# src/data/parse_xml.py
import os
import csv
import json 
import sys

# CRÍTICO: Sube TRES niveles
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(ROOT_DIR, "data")
# Archivos de entrada y salida
JSON_INPUT_FILE = os.path.join(DATA_DIR, "user_mal_list.json") 
CSV_OUTPUT_FILE = os.path.join(DATA_DIR, "user_ratings.csv")

def parse_and_save_ratings():
    """Lee el JSON descargado y lo convierte al CSV de ratings."""
    
    if not os.path.exists(JSON_INPUT_FILE) or os.path.getsize(JSON_INPUT_FILE) <= 100:
        print(f"❌ Error: Archivo de lista de usuario '{os.path.basename(JSON_INPUT_FILE)}' no encontrado o vacío.", file=sys.stderr)
        print("💡 Consejo: Asegúrate de ejecutar 'download_mal_list.py' antes.", file=sys.stderr)
        # En lugar de sys.exit(1), lanzamos una excepción para que el orquestador la capture
        raise FileNotFoundError("user_mal_list.json no encontrado o inválido.")

    try:
        with open(JSON_INPUT_FILE, 'r', encoding='utf-8') as f:
            user_data = json.load(f)
            if not isinstance(user_data, list):
                 raise TypeError("El contenido de user_mal_list.json no es una lista válida.")
    except Exception as e:
        print(f"❌ Error al cargar/parsear el JSON de usuario: {e}", file=sys.stderr)
        raise e
    
    ratings = []

    for item in user_data:
        try:
            # El ID del anime en el JSON de MAL es 'anime_id'
            anime_id = item.get('anime_id') 
            title = item.get('anime_title') 
            
            # La puntuación viene como un string/número
            score_text = str(item.get('score')) 
            score = int(score_text) if score_text.isdigit() else 0
            
            # Mapeo de status (viene como ID numérico en el JSON)
            status_id = item.get('status')
            status_map = {
                1: 'Watching', 2: 'Completed', 3: 'On-Hold', 4: 'Dropped', 6: 'Plan to Watch'
            }
            my_status = status_map.get(status_id, 'NO_INTERACTUADO') 


            if anime_id is None:
                continue

            ratings.append({
                'user_id': 1,
                'anime_id': anime_id, # Este es el MAL ID
                'title': title,
                'my_score': score,
                'my_status': my_status
            })
        except Exception:
            continue # Saltar si un item está corrupto

    if ratings:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(CSV_OUTPUT_FILE, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['user_id', 'anime_id', 'title', 'my_score', 'my_status'])
            writer.writeheader()
            writer.writerows(ratings)

        print(f"✅ Proceso completado. Se extrajeron {len(ratings)} items.", file=sys.stderr)
        print(f"El archivo '{os.path.basename(CSV_OUTPUT_FILE)}' se guardó en {os.path.abspath(DATA_DIR)}.", file=sys.stderr)
    else:
        print("⚠️ No se extrajeron ratings válidos.", file=sys.stderr)
        # Crear un archivo CSV vacío si no hay ratings para evitar fallos
        with open(CSV_OUTPUT_FILE, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['user_id', 'anime_id', 'title', 'my_score', 'my_status'])
            writer.writeheader()

if __name__ == '__main__':
    try:
        parse_and_save_ratings()
    except Exception as e:
        sys.exit(1)