# src/data/parse_xml.py (Versión con ruta corregida)
import os
import csv
import xml.etree.ElementTree as ET
import sys

# CRÍTICO: Sube TRES niveles (consistente con prepare_data.py)
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# CRÍTICO: Eliminar "./data" redundante
DATA_DIR = os.path.join(ROOT_DIR, "data")
CSV_OUTPUT_FILE = os.path.join(DATA_DIR, "user_ratings.csv")

def find_mal_xml_file(data_path):
    """Busca el archivo XML en el directorio de datos."""
    try:
        # Crea la carpeta si no existe, antes de buscar
        os.makedirs(data_path, exist_ok=True) 
        
        xml_files = [f for f in os.listdir(data_path) if f.endswith('.xml')]
        
        if not xml_files:
            print(f"❌ Error: No se encontró ningún archivo XML en el directorio '{os.path.abspath(data_path)}'.")
            print(f"💡 Consejo: coloca tu archivo exportado de MyAnimeList (.xml) en esa carpeta.")
            return None
            
        return os.path.join(data_path, xml_files[0])
    except FileNotFoundError:
        # Este caso es poco probable si se usa os.makedirs, pero se mantiene por si acaso
        print(f"❌ Error: El directorio '{data_path}' no existe.")
        return None

def parse_and_save_ratings():
# DATA_DIR ahora apunta a la carpeta /data correcta
    xml_file_path = find_mal_xml_file(DATA_DIR)
    if not xml_file_path:
        sys.exit(1)

    try:
        tree = ET.parse(xml_file_path)
        root = tree.getroot()
    except Exception as e:
        print(f"❌ Error al parsear el XML: '{xml_file_path}'. Verifica la integridad del archivo. Error: {e}")
        sys.exit(1)

    ratings = []
    total_anime_xml = 0

    # Intenta obtener el total de animes del usuario
    total_anime_node = root.find('myinfo/user_total_anime')
    if total_anime_node is not None:
        try:
            total_anime_xml = int(total_anime_node.text)
        except (ValueError, TypeError):
            pass # No pasa nada si no se encuentra o es inválido

    for anime_node in root.findall('anime'):
        try:
            id_node = anime_node.find('series_animedb_id')
            title_node = anime_node.find('series_title')
            score_node = anime_node.find('my_score')
            status_node = anime_node.find('my_status')

            # Requisitos mínimos
            if id_node is None:
                continue

            anime_id = int(id_node.text)
            title = title_node.text.strip() if title_node is not None and title_node.text else ''
            
            # Asegurar que el score se maneje correctamente (convertir '0' a 0)
            score_text = score_node.text if score_node is not None and score_node.text is not None else '0'
            score = int(score_text) if score_text.isdigit() else 0
            
            # Rellenar my_status con 'NaN' o '' si no existe (el '' es mejor para nuestro filtro)
            my_status = status_node.text.strip() if status_node is not None and status_node.text else ''

            # Solo guardar si hay un ID válido
            ratings.append({
                'user_id': 1,
                'anime_id': anime_id,
                'title': title,
                'my_score': score,
                'my_status': my_status
            })
        except Exception:
            # Captura errores de conversión o atributos faltantes en un nodo <anime>
            continue

    if ratings:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(CSV_OUTPUT_FILE, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['user_id', 'anime_id', 'title', 'my_score', 'my_status'])
            writer.writeheader()
            writer.writerows(ratings)

        print(f"✅ Proceso completado. Se extrajeron {len(ratings)} items.")
        if total_anime_xml > 0 and len(ratings) == total_anime_xml:
            print(f"🎉 Éxito: El conteo coincide con el total de su lista ({total_anime_xml}).")
        elif total_anime_xml > 0:
            print(f"⚠️ Aviso: Total en XML ({total_anime_xml}) no coincide con extraídos ({len(ratings)}).")
        # 🚨 Arreglar el mensaje de impresión incorrecto del archivo
        print(f"El archivo '{os.path.basename(CSV_OUTPUT_FILE)}' se guardó en {os.path.abspath(DATA_DIR)}.")

def main():
    parse_and_save_ratings()

if __name__ == "__main__":
    main()