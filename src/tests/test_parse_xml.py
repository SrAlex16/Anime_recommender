# src/tests/test_parse_xml.py

import os
import sys
import importlib.util
import pandas as pd # Añadido para verificar CSV

# CRÍTICO: Detectar la raíz del proyecto (2 niveles hacia arriba desde src/tests)
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(ROOT_DIR, "data")

# Añadir la ruta completa para el archivo de salida
CSV_OUTPUT_FILE = os.path.join(DATA_DIR, "user_ratings.csv")
SCRIPT_PATH = os.path.join(ROOT_DIR, "src", "data", "parse_xml.py")


# RENOMBRAR: run_parse_xml_test -> test_parse_xml
def test_parse_xml():
    print("🔍 Test: parse_xml.py")

    os.makedirs(DATA_DIR, exist_ok=True) 
    
    # Cargar dinámicamente el módulo
    spec = importlib.util.spec_from_file_location("parse_xml", SCRIPT_PATH)
    parse_xml = importlib.util.module_from_spec(spec)
    sys.modules[parse_xml.__name__] = parse_xml # Para permitir que los módulos internos lo vean
    spec.loader.exec_module(parse_xml)

    # Simular archivo XML de prueba (el código de producción lo busca por defecto)
    xml_test = os.path.join(DATA_DIR, "animelist.xml") # El script busca "animelist.xml"
    
    # 💥 CRÍTICO: LIMPIAR EL CSV DE RESULTADOS REALES ANTES DE LA PRUEBA
    if os.path.exists(CSV_OUTPUT_FILE):
        os.remove(CSV_OUTPUT_FILE)
    
    # Creación del XML de prueba
    with open(xml_test, "w", encoding="utf-8") as f:
        f.write("""
<myanimelist>
  <myinfo><user_total_anime>2</user_total_anime></myinfo>
  <anime>
    <series_animedb_id>1</series_animedb_id>
    <series_title>Naruto</series_title>
    <my_score>8</my_score>
    <my_status>Completed</my_status>
  </anime>
  <anime>
    <series_animedb_id>2</series_animedb_id>
    <series_title>Bleach</series_title>
    <my_score>7</my_score>
    <my_status>Watching</my_status>
  </anime>
</myanimelist>
""")

    # Ejecutar parser (usando la función principal)
    parse_xml.parse_and_save_ratings() 

    # 1. Verificar si el CSV se generó
    assert os.path.exists(CSV_OUTPUT_FILE), "❌ user_ratings.csv no se generó."

    # 2. Verificar contenido y columnas
    df_ratings = pd.read_csv(CSV_OUTPUT_FILE)
    assert len(df_ratings) == 2, f"❌ El número de filas no coincide. Esperado: 2, Obtenido: {len(df_ratings)}"
    assert {"anime_id", "my_score", "my_status"}.issubset(df_ratings.columns), "❌ Faltan columnas esenciales en el CSV."
    
    # 3. Limpiar los archivos simulados
    os.remove(xml_test) 
    
    print("✅ user_ratings.csv generado y validado correctamente.")