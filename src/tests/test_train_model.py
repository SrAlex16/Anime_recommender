# src/tests/test_train_model.py

import os
import importlib.util
import pandas as pd
import numpy as np
import json 
import sys 
import time # Añadir para depuración opcional

# --- Rutas ---
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MODEL_PATH = os.path.join(ROOT_DIR, "src", "model", "train_model.py")
DATA_DIR = os.path.join(ROOT_DIR, "data")

# Nombres de archivos de producción
FINAL_PATH = os.path.join(DATA_DIR, "final_dataset.csv")
USER_RATINGS_PATH = os.path.join(DATA_DIR, "user_ratings.csv") 
MERGED_PATH = os.path.join(DATA_DIR, "merged_anime.csv") 
BLACKLIST_PATH = os.path.join(DATA_DIR, "blacklist.json")

# Rutas temporales para aislar los archivos de producción
TEMP_SUFFIX = "_TEST_BACKUP"
TEMP_PATHS = {
    FINAL_PATH: FINAL_PATH + TEMP_SUFFIX,
    USER_RATINGS_PATH: USER_RATINGS_PATH + TEMP_SUFFIX,
    MERGED_PATH: MERGED_PATH + TEMP_SUFFIX,
}

def test_train_model():
    print("🔍 Test: train_model.py - INICIANDO AISLAMIENTO")

    files_to_restore = []
    # Archivos mock creados que DEBEN ELIMINARSE siempre
    mock_files_created = [FINAL_PATH, USER_RATINGS_PATH, MERGED_PATH]

    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        
        # 1. AISLAMIENTO: Renombrar archivos de producción existentes (si los hay)
        for original, temp in TEMP_PATHS.items():
            if os.path.exists(original):
                os.rename(original, temp)
                files_to_restore.append((temp, original)) 
                print(f"  -> Aislado: {os.path.basename(original)}")
        
        # 2. SETUP: Cargar Módulo y Crear Mocks (Archivos pequeños)
        spec = importlib.util.spec_from_file_location("train_model", MODEL_PATH)
        train_model = importlib.util.module_from_spec(spec)
        sys.modules[train_model.__name__] = train_model 
        
        # Mocks para garantizar que el modelo cargue *algo*
        common_genres = "['Action', 'Adventure']"
        
        df_final_mock = pd.DataFrame({
            "id": [1, 2, 3], "MAL_ID": [1, 2, 3], "title": ["A", "B", "C"], 
            "genres": [common_genres, common_genres, common_genres], "tags": ["['T1']", "['T2']", "['T3']"], 
            "description": ["D1", "D2", "D3"],
            "user_score": [9.0, np.nan, np.nan], "my_status": ["Completed", "", ""], 
            "score": [80, 85, 100], "type": ["ANIME", "ANIME", "ANIME"], 
        })
        
        df_ratings_mock = pd.DataFrame({
            "anime_id": [1], "my_score": [9], "my_status": ["Completed"]
        })
        
        # Guardar mocks con nombres de producción (Sobreescriben los originales si no se aislaron)
        df_final_mock.to_csv(FINAL_PATH, index=False) 
        df_ratings_mock.to_csv(USER_RATINGS_PATH, index=False) 
        pd.DataFrame().to_csv(MERGED_PATH, index=False) # Crear archivo vacío para merged
        
        # MOCK DE BLACKLIST: asegurar que exista
        if not os.path.exists(BLACKLIST_PATH):
            with open(BLACKLIST_PATH, 'w', encoding='utf-8') as f:
                json.dump([], f) 

        # Ejecutar el módulo de entrenamiento
        spec.loader.exec_module(train_model) 

        # --- 3. EJECUCIÓN DEL TEST ---
        df_loaded = train_model.load_data() 
        
        # Verificación crítica: el test debe cargar 3 filas
        assert len(df_loaded) == 3, f"❌ Carga de mock fallida. Esperado: 3 filas, Obtenido: {len(df_loaded)}"
        
        # El resto de aserciones...
        cosine_sim = train_model.preprocess_data(df_loaded)
        recs = train_model.get_recommendations(df_loaded, cosine_sim, threshold=0.6, top_n=3)
        
        assert 1 not in recs['AniListID'].tolist(), "❌ El anime visto/puntuado (ID 1) no fue excluido."
        print("✅ Test de entrenamiento y recomendación completado correctamente.")

    finally:
        # 4. LIMPIEZA Y RESTAURACIÓN (TEARDOWN) - ESTO SE EJECUTA SIEMPRE
        print("\n🧹 Iniciando limpieza de archivos temporales y restauración de producción.")
        
        # A. Eliminar Mocks creados
        for file_path in mock_files_created:
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    print(f"  -> Limpiado Mock: {os.path.basename(file_path)}")
                except OSError as e:
                    print(f"❌ Error al limpiar {os.path.basename(file_path)}: {e}") 
        
        # B. Restaurar originales (si fueron renombrados)
        for temp_path, original_path in files_to_restore:
            if os.path.exists(temp_path):
                try:
                    os.rename(temp_path, original_path)
                    print(f"  -> Restaurado: {os.path.basename(original_path)}")
                except OSError as e:
                    print(f"❌ Error al restaurar {os.path.basename(original_path)}: {e}")

        print("✅ Aislamiento garantizado. Archivos de producción intactos/restaurados.")