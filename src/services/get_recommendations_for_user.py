# src/services/get_recommendations_for_user.py
import sys
import json
import subprocess
from datetime import datetime
import os
import traceback

# === CONFIGURACIÓN DE PATHS ===
# 🔧 Forzar que Python reconozca 'src' como paquete raíz, incluso en Render
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Importar funciones de los scripts de datos y modelo
from src.data.download_mal_list import download_user_list
from src.data.prepare_data import run_full_preparation_flow
from src.model.train_model import main_with_json as run_model_pipeline


def debug_log(message):
    """Función de logging para debug - FORZAR FLUSH"""
    print(f"🔍 [DEBUG] {message}", file=sys.stderr, flush=True)

def verify_no_list_conflicts(df, recs):
    """Verifica que no se recomienden animes de la lista del usuario"""
    debug_log("🔍 VERIFICANDO QUE NO SE RECOMIENDEN ANIMES DE LA LISTA...")

    # Se consideran "interactuados" aquellos que no tienen el estado por defecto
    user_anime_ids = df[df['my_status'] != 'NO_INTERACTUADO']['id'].tolist()
    recommended_ids = recs['id'].tolist()

    conflicts = set(user_anime_ids).intersection(set(recommended_ids))
    if conflicts:
        debug_log(f"❌ ALERTA: {len(conflicts)} animes de la lista fueron recomendados")
        # Remover los conflictos de la lista de recomendaciones
        recs = recs[~recs['id'].isin(conflicts)]
        debug_log(f"✅ Se eliminaron {len(conflicts)} conflictos. Total recs: {len(recs)}")
        return recs
    else:
        debug_log("✅ No se encontraron conflictos con la lista del usuario.")
        return recs

def main_pipeline(username):
    """
    Función principal que orquesta todo el flujo.
    Retorna un string JSON o lanza una excepción.
    """
    try:
        debug_log("--- INICIO DEL PIPELINE DE RECOMENDACIÓN ---")
        
        # 1. Verificar/Descargar datos estáticos (Anime base) - Ejecutado en el deploy
        check_preloaded_data()
        
        # 2. Descargar la lista del usuario
        if not download_user_list(username):
            raise Exception("No se pudo descargar la lista de anime del usuario de MAL.")
        
        # 3. Preparar/Limpiar los datos (parsear lista y fusionar)
        # Esto incluye: parse_xml y merge_and_clean_data
        run_full_preparation_flow(username)
        
        # 4. Ejecutar el modelo de recomendación
        # run_model_pipeline devuelve un string JSON con el resultado o lanza una excepción
        result_json_str = run_model_pipeline(username=username) 
        
        debug_log("--- FIN DEL PIPELINE DE RECOMENDACIÓN EXITOSO ---")
        return result_json_str

    except Exception as e:
        debug_log(f"❌ Error en el motor de recomendación: {e}")
        debug_log(traceback.format_exc()) # Imprimir el stack trace para debug
        
        return json.dumps({
            'status': 'error',
            'message': f"Error en el motor de recomendación: {str(e)}",
            'timestamp': datetime.now().isoformat()
        })

def check_preloaded_data():
    """Verifica si los datos base están descargados, si no los obtiene"""
    ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    MERGED_ANIME_PATH = os.path.join(ROOT_DIR, "data", "merged_anime.csv")

    # Si el archivo no existe o es demasiado pequeño (por ejemplo, < 10KB), lo descargamos.
    if not os.path.exists(MERGED_ANIME_PATH) or os.path.getsize(MERGED_ANIME_PATH) < 10000:
        debug_log("📥 Dataset base no encontrado o incompleto. Descargando...")
        try:
            # Importación local para evitar problemas de dependencia circular
            from src.data.fetch_datasets import main as fetch_main
            fetch_main()
            debug_log("✅ Dataset base descargado exitosamente")
        except Exception as e:
            debug_log(f"❌ Error descargando dataset base: {e}")
            raise Exception("Error al obtener el dataset base de AniList.")
    else:
        debug_log("✅ Dataset base ya está precargado")

if __name__ == "__main__":
    try:
        # El nombre de usuario se pasa como argumento de línea de comandos desde app.py
        if len(sys.argv) < 2:
            raise ValueError("Falta el argumento: Nombre de usuario de MyAnimeList.")
        
        USERNAME = sys.argv[1]
        
        # La salida de la función principal (el JSON string) se imprime al stdout
        # para que la API de Flask lo capture.
        result_json_str = main_pipeline(USERNAME)
        print(result_json_str)

    except Exception as e:
        # En caso de error, siempre imprimir un JSON de error al stdout final.
        error_output = json.dumps({
            'status': 'error',
            'message': f"Error en el flujo principal: {str(e)}",
            'timestamp': datetime.now().isoformat(),
            'traceback': traceback.format_exc()
        })
        print(error_output) # Esto es capturado por Flask
        sys.exit(1) # Forzar un código de salida de error