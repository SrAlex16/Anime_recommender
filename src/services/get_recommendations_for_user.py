import sys
import json
import subprocess
from datetime import datetime
import os

import os
import sys
import json
import subprocess
from datetime import datetime

# --- CORRECCIÓN CRÍTICA DE RUTAS ---
# 1. Asegurar que la carpeta 'src' esté en el path
SRC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

# 2. Asegurar que las carpetas de módulos estén en el path
# Esto es necesario porque el subproceso se ejecuta desde la raíz del proyecto (ROOT_DIR)
# y debe encontrar los scripts dentro de 'src/data' y 'src/model'

DATA_DIR_FOR_IMPORT = os.path.join(SRC_DIR, 'data')
MODEL_DIR_FOR_IMPORT = os.path.join(SRC_DIR, 'model')

if DATA_DIR_FOR_IMPORT not in sys.path:
    sys.path.insert(0, DATA_DIR_FOR_IMPORT)
if MODEL_DIR_FOR_IMPORT not in sys.path:
    sys.path.insert(0, MODEL_DIR_FOR_IMPORT)

# --- IMPORTACIONES CORREGIDAS ---
# Ahora, las importaciones directas funcionarán porque el directorio del módulo está en sys.path
from data.prepare_data import run_full_preparation_flow
from model.train_model import load_data, preprocess_data, get_recommendations, get_anime_statistics
from data.download_mal_list import download_user_list

def get_recommendations_service(username):

    check_and_preload_dataset()
    
    """
    Orquesta el proceso completo: 
    1. Descarga la lista del usuario.
    2. Prepara el dataset (corre fetch, parse, merge).
    3. Entrena el modelo y genera recomendaciones.
    4. Imprime el JSON a stdout para que el subprocess lo capture.
    """
    # ROOT_DIR y DATA_DIR no son estrictamente necesarios para la lógica interna, 
    # pero los mantendremos si los usas para alguna función de ruta.
    ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    DATA_DIR = os.path.join(ROOT_DIR, "data")
    
    # 1. DESCARGA LA LISTA DEL USUARIO
    if not download_user_list(username):
        return json.dumps({
            'status': 'error',
            'message': f"No se pudo descargar la lista de anime del usuario '{username}'. Asegúrate de que el usuario existe y su lista es pública.",
            'timestamp': datetime.now().isoformat()
        })
    
    # 2. PREPARA EL DATASET COMPLETO
    try:
        run_full_preparation_flow(username) 
    except subprocess.CalledProcessError as e:
        return json.dumps({
            'status': 'error',
            'message': f"Error en la preparación de datos (fetch/parse): {e.stderr.decode()}",
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return json.dumps({
            'status': 'error',
            'message': f"Error desconocido durante la preparación de datos: {str(e)}",
            'timestamp': datetime.now().isoformat()
        })
        
    # 3. ENTRENAR MODELO Y GENERAR RECOMENDACIONES
    try:
        df = load_data() 
        sim = preprocess_data(df)
        if sim is None:
            raise Exception("No se pudo entrenar el modelo.")

        recs = get_recommendations(df, sim)
        
        if recs.empty:
            raise Exception("No se generaron recomendaciones.")

        stats = get_anime_statistics(df)
        
        recommendations_json = json.loads(recs.to_json(orient='records'))

        # Crear el JSON final
        output_data = {
            'status': 'success',
            'timestamp': datetime.now().isoformat(),
            'count': len(recommendations_json),
            'statistics': stats,
            'recommendations': recommendations_json
        }
        
        return json.dumps(output_data, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            'status': 'error',
            'message': f"Error en el motor de recomendación: {str(e)}",
            'timestamp': datetime.now().isoformat()
        })

def check_and_preload_dataset():
    """Verifica si el dataset base existe, si no lo descarga"""
    ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    MERGED_ANIME_PATH = os.path.join(ROOT_DIR, "data", "merged_anime.csv")
    
    if not os.path.exists(MERGED_ANIME_PATH) or os.path.getsize(MERGED_ANIME_PATH) < 10000:
        print("📥 Dataset base no encontrado. Descargando...")
        from data.fetch_datasets import main as fetch_main
        fetch_main()
    else:
        print("✅ Dataset base ya existe, saltando descarga")

if __name__ == "__main__":
    # Lee el nombre de usuario del argumento de la línea de comandos
    if len(sys.argv) > 1:
        username = sys.argv[1]
        
        # Llama al servicio SOLO si se proporciona un nombre de usuario como argumento
        json_output = get_recommendations_service(username)
        
        # Imprime el JSON que el subprocess capturará en app.py
        print(json_output)
        
    else:
        # ⚠️ Solución al error de inicio de Gunicorn: salir sin ejecutar código pesado
        # Ya que no hay argumentos (nombre de usuario), no se ejecuta la lógica.
        sys.exit(0)