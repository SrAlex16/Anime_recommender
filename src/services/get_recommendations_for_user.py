# src/services/get_recommendations_for_user.py
import sys
import json
import subprocess
from datetime import datetime
import os
import traceback

# Configuración de paths
SRC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
ROOT_DIR = os.path.dirname(SRC_DIR)
sys.path.insert(0, SRC_DIR)
sys.path.insert(0, ROOT_DIR)

def debug_log(message):
    """Función de logging para debug - FORZAR FLUSH"""
    print(f"🔍 [DEBUG] {message}", file=sys.stderr, flush=True)

def get_recommendations_service(username):
    """
    Orquesta el proceso completo con mejor manejo de errores
    """
    try:
        debug_log(f"Iniciando servicio para usuario: {username}")

        # 🔥 VERIFICAR DATOS PRECARGADOS
        check_preloaded_data()
        
        # 1. Importaciones dentro de la función para evitar problemas
        try:
            from data.download_mal_list import download_user_list
            from data.prepare_data import run_full_preparation_flow
            from model.train_model import load_data, preprocess_data, get_recommendations, get_anime_statistics
            debug_log("✅ Módulos importados correctamente")
        except ImportError as e:
            debug_log(f"❌ Error importando módulos: {e}")
            return json.dumps({
                'status': 'error',
                'message': f"Error de importación: {str(e)}",
                'timestamp': datetime.now().isoformat()
            })

        # 2. DESCARGA LA LISTA DEL USUARIO
        debug_log("Descargando lista del usuario...")
        if not download_user_list(username):
            return json.dumps({
                'status': 'error',
                'message': f"No se pudo descargar la lista de '{username}'. Verifica que el usuario existe y la lista es pública.",
                'timestamp': datetime.now().isoformat()
            })

        # 3. PREPARA EL DATASET
        debug_log("Preparando dataset...")
        try:
            run_full_preparation_flow(username)
            debug_log("✅ Dataset preparado")
        except Exception as e:
            debug_log(f"❌ Error preparando datos: {e}")
            return json.dumps({
                'status': 'error',
                'message': f"Error preparando datos: {str(e)}",
                'timestamp': datetime.now().isoformat()
            })

        # 4. ENTRENAR MODELO Y GENERAR RECOMENDACIONES
        debug_log("Generando recomendaciones...")
        try:
            df = load_data()
            debug_log(f"✅ Dataset cargado: {len(df)} filas")
            
            sim = preprocess_data(df)
            if sim is None:
                raise Exception("No se pudo entrenar el modelo.")

            recs = get_recommendations(df, sim)
            debug_log(f"✅ Recomendaciones generadas: {len(recs)} animes")
            
            if recs.empty:
                raise Exception("No se generaron recomendaciones.")

            stats = get_anime_statistics(df)
            recommendations_json = json.loads(recs.to_json(orient='records'))

            output_data = {
                'status': 'success',
                'timestamp': datetime.now().isoformat(),
                'count': len(recommendations_json),
                'statistics': stats,
                'recommendations': recommendations_json
            }
            
            debug_log("✅ Proceso completado exitosamente")
            return json.dumps(output_data, ensure_ascii=False)
            
        except Exception as e:
            debug_log(f"❌ Error en motor de recomendación: {e}")
            return json.dumps({
                'status': 'error',
                'message': f"Error en el motor de recomendación: {str(e)}",
                'timestamp': datetime.now().isoformat()
            })

    except Exception as e:
        debug_log(f"❌ Error general: {e}")
        debug_log(traceback.format_exc())
        return json.dumps({
            'status': 'error',
            'message': f"Error general: {str(e)}",
            'timestamp': datetime.now().isoformat()
        })
    
def check_preloaded_data():
    """Verifica si los datos están precargados, si no los descarga"""
    ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    MERGED_ANIME_PATH = os.path.join(ROOT_DIR, "data", "merged_anime.csv")
    
    # Verificar si el archivo existe y tiene tamaño suficiente
    if not os.path.exists(MERGED_ANIME_PATH) or os.path.getsize(MERGED_ANIME_PATH) < 10000:
        debug_log("📥 Dataset base no encontrado. Descargando...")
        try:
            from data.fetch_datasets import main as fetch_main
            fetch_main()
            debug_log("✅ Dataset base descargado exitosamente")
        except Exception as e:
            debug_log(f"❌ Error descargando dataset: {e}")
            raise e
    else:
        debug_log("✅ Dataset base ya está precargado")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        username = sys.argv[1]
        debug_log(f"Ejecutando para usuario: {username}")
        
        # 🔥 CRÍTICO: Forzar encoding y flushing en Render
        try:
            # Forzar stdout a UTF-8 y sin buffering
            if sys.stdout.encoding != 'UTF-8':
                import codecs
                sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer)
            
            result = get_recommendations_service(username)
            if result:
                # 🔥 IMPRIMIR DIRECTAMENTE SIN BUFFERING
                print(result, flush=True)
            else:
                error_output = json.dumps({
                    'status': 'error',
                    'message': 'El servicio no devolvió resultado',
                    'timestamp': datetime.now().isoformat()
                })
                print(error_output, flush=True)
                
        except Exception as e:
            error_output = json.dumps({
                'status': 'error', 
                'message': f'Error ejecutando servicio: {str(e)}',
                'timestamp': datetime.now().isoformat()
            })
            print(error_output, flush=True)
    else:
        # Sin argumentos = modo servidor, salir silenciosamente
        sys.exit(0)