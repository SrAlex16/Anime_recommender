# src/tests/test_parse_xml.py (CORREGIDO)

import os
import sys
import importlib.util
import pandas as pd
import json 

# CRÍTICO: Detectar la raíz del proyecto (2 niveles hacia arriba desde src/tests)
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(ROOT_DIR, "data")

# Añadir la ruta completa para los archivos de prueba
CSV_OUTPUT_FILE = os.path.join(DATA_DIR, "user_ratings.csv")
JSON_INPUT_FILE = os.path.join(DATA_DIR, "user_mal_list.json")
SCRIPT_PATH = os.path.join(ROOT_DIR, "src", "data", "parse_xml.py")


def test_parse_xml():
    print("🔍 Test: parse_xml.py (ahora parsea JSON)")

    os.makedirs(DATA_DIR, exist_ok=True) 
    
    # Cargar dinámicamente el módulo
    spec = importlib.util.spec_from_file_location("parse_xml", SCRIPT_PATH)
    parse_xml = importlib.util.module_from_spec(spec)
    sys.modules[parse_xml.__name__] = parse_xml 
    spec.loader.exec_module(parse_xml)

    # 💥 CRÍTICO: LIMPIAR ARCHIVOS ANTES DE LA PRUEBA
    if os.path.exists(CSV_OUTPUT_FILE):
        os.remove(CSV_OUTPUT_FILE)
    if os.path.exists(JSON_INPUT_FILE):
        os.remove(JSON_INPUT_FILE)
    
    # Creación del JSON de prueba (simulando la respuesta del endpoint)
    # Nota: Status IDs: 1=Watching, 2=Completed, 4=Dropped, 6=Plan to Watch
    mock_json_data = [
        {
            "anime_id": 1,
            "anime_title": "Naruto",
            "score": 8,
            "status": 2, # Completed
            "other_field": "ignore"
        },
        {
            "anime_id": 2,
            "anime_title": "Bleach",
            "score": 7,
            "status": 1, # Watching
            "other_field": "ignore"
        },
        {
            "anime_id": 3,
            "anime_title": "One Piece",
            "score": 0,
            "status": 6, # Plan to Watch (Score 0)
            "other_field": "ignore"
        },
        {
            "anime_id": 4,
            "anime_title": "Corrupt Item",
            "score": None, # Item con score faltante o no válido. Se convierte a 0.
            "status": 4 # Dropped
        }
    ]
    
    # Escribir el JSON de prueba
    with open(JSON_INPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(mock_json_data, f, indent=4)


    # Ejecutar parser
    parse_xml.main() 

    # 1. Verificar si el CSV se generó
    assert os.path.exists(CSV_OUTPUT_FILE), "❌ user_ratings.csv no se generó."

    # 2. Cargar y verificar el contenido del CSV
    df = pd.read_csv(CSV_OUTPUT_FILE)

    # 💡 CORRECCIÓN: Esperamos 4 filas, ya que el ítem con score=None se convierte a score=0 y se mantiene.
    assert len(df) == 4, f"❌ Se esperaban 4 filas en el CSV, pero se encontraron {len(df)}."

    # Verificar valores mapeados
    naruto = df[df['anime_id'] == 1].iloc[0]
    corrupt_item = df[df['anime_id'] == 4].iloc[0]

    # Verificar Score del item corrupto
    assert corrupt_item['my_score'] == 0, "❌ El score del ítem corrupto debe ser 0."
    assert corrupt_item['my_status'] == 'Dropped', "❌ El status del ítem corrupto debe ser 'Dropped' (ID 4)."
    
    # Verificar otros ítems
    assert naruto['my_score'] == 8, "❌ El score de Naruto no es 8."
    assert naruto['my_status'] == 'Completed', "❌ El status de Naruto no es 'Completed'."


    print("✅ Test de parse_xml.py completado. El parseo de JSON a CSV es correcto.")
    
    # 3. Limpieza de archivos de prueba
    os.remove(JSON_INPUT_FILE)
    os.remove(CSV_OUTPUT_FILE)
    
    # Limpieza de archivos del XML si existieran (mantenido por precaución)
    xml_test = os.path.join(DATA_DIR, "animelist.xml")
    if os.path.exists(xml_test):
        os.remove(xml_test)