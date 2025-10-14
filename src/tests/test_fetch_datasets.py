# src/tests/test_fetch_datasets.py

import os
import sys
import importlib.util
import pandas as pd

# CRÍTICO: Detectar la raíz del proyecto (2 niveles hacia arriba desde src/tests)
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(ROOT_DIR, "data")
SCRIPT_PATH = os.path.join(ROOT_DIR, "src", "data", "fetch_datasets.py")

# RENOMBRAR: run_fetch_datasets_test -> test_fetch_datasets
def test_fetch_datasets():
    print("🔍 Test: fetch_datasets.py")

    spec = importlib.util.spec_from_file_location("fetch_datasets", SCRIPT_PATH)
    fetch_datasets = importlib.util.module_from_spec(spec)
    # Ejecutar primero para permitir la sobreescritura (ya no es necesario, pero es buena práctica)
    sys.modules[fetch_datasets.__name__] = fetch_datasets 
    spec.loader.exec_module(fetch_datasets)

    merged_path = os.path.join(DATA_DIR, "merged_anime.csv")
    
    # 💥 CRÍTICO: Limpiar el archivo real antes del test
    if os.path.exists(merged_path):
        os.remove(merged_path)

    # Solo una página para velocidad
    df = fetch_datasets.fetch_all(max_pages=1) 
    assert not df.empty, "❌ No se obtuvieron datos de la API AniList."
    # CORRECCIÓN: Los nombres de columnas deben ser los reales devueltos por la API/fetch_all
    assert {"AniListID", "title"}.issubset(df.columns), "❌ Faltan columnas esperadas (AniListID, title)."

    # Ejecutamos el main para que se genere el archivo como en el flujo normal:
    fetch_datasets.main()
    
    assert os.path.exists(merged_path), "❌ No se generó merged_anime.csv."
    
    # Comprobar que el archivo generado tiene datos (más de 10 filas)
    df_merged = pd.read_csv(merged_path)
    assert len(df_merged) > 10, "❌ merged_anime.csv no se generó con suficientes datos."


    print(f"✅ merged_anime.csv generado/verificado correctamente (test).")