# src/model/get_recommendations_for_user.py

import os
import sys
import json
import subprocess
from datetime import datetime

# Añadir la ruta de src/data para los imports internos
# Esto asegura que los scripts puedan importar cosas si las necesitas
# SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# sys.path.append(os.path.join(SCRIPT_DIR, '..', 'data'))

# Importar las funciones principales desde tus scripts
from prepare_data import run_full_preparation_flow
from train_model import load_data, preprocess_data, get_recommendations, get_anime_statistics, save_recommendations_to_json
from download_mal_list import download_user_list # Necesario para iniciar

def get_recommendations_service(username):
    """
    Orquesta el proceso completo: 
    1. Descarga la lista del usuario.
    2. Prepara el dataset (corre fetch, parse, merge).
    3. Entrena el modelo y genera recomendaciones.
    4. Imprime el JSON a stdout para que Flutter lo capture.
    """
    ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    DATA_DIR = os.path.join(ROOT_DIR, "data")
    
    # 1. DESCARGA LA LISTA DEL USUARIO
    # NOTA: download_user_list necesita el nombre de usuario.
    # Asumimos que lo guardará en data/user_mal_list.json
    if not download_user_list(username):
        return json.dumps({
            'status': 'error',
            'message': f"No se pudo descargar la lista de anime del usuario '{username}'. Asegúrate de que el usuario existe y su lista es pública.",
            'timestamp': datetime.now().isoformat()
        })
    
    # 2. PREPARA EL DATASET COMPLETO (Esto incluye la descarga de AniList si es necesario)
    try:
        # Asumimos que run_full_preparation_flow maneja la ejecución de fetch_datasets y parse_xml
        # ⚠️ Necesitas adaptar tu prepare_data.py para exponer esta función
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

        # Crear el JSON final que se devolverá a Flutter
        output_data = {
            'status': 'success',
            'timestamp': datetime.now().isoformat(),
            'count': len(recommendations_json),
            'statistics': stats,
            'recommendations': recommendations_json
        }
        
        # ⚠️ IMPORTANTE: Devolver el JSON directamente al stdout
        return json.dumps(output_data, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            'status': 'error',
            'message': f"Error en el motor de recomendación: {str(e)}",
            'timestamp': datetime.now().isoformat()
        })

if __name__ == "__main__":
    # Lee el nombre de usuario del argumento de la línea de comandos
    if len(sys.argv) > 1:
        username = sys.argv[1]
    else:
        # Esto solo es para pruebas locales, Chaquopy siempre envía el argumento
        username = "alex_mal_user" # Usuario por defecto
        
    json_output = get_recommendations_service(username)
    # Imprime el JSON que Chaquopy/Native capturará
    print(json_output)