# src/tests/test_prepare_data.py

import os
import sys
import pandas as pd
import importlib.util
import ast 

# --- CONFIGURACIÓN DE RUTAS ---
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(ROOT_DIR, "data")
SCRIPT_PATH = os.path.join(ROOT_DIR, "src", "data", "prepare_data.py")

# Nombres de archivos de producción
merged_path = os.path.join(DATA_DIR, "merged_anime.csv")
user_path = os.path.join(DATA_DIR, "user_ratings.csv")
final_path = os.path.join(DATA_DIR, "final_dataset.csv")

# Sufijo temporal para el aislamiento
TEMP_SUFFIX = "_TEST_BACKUP"

# RENOMBRAR: run_prepare_data_test -> test_prepare_data
def test_prepare_data():
    
    # Archivos que deben ser respaldados si existen
    FILES_TO_ISOLATE = [merged_path, user_path]
    files_to_restore = [] # Lista de (temp_path, original_path)
    
    # 1. INICIAR AISLAMIENTO (SETUP)
    print("🔍 Test: prepare_data.py - INICIANDO AISLAMIENTO")
    os.makedirs(DATA_DIR, exist_ok=True) 

    # Renombrar archivos de producción para aislar el test
    for original_path in FILES_TO_ISOLATE:
        temp_path = original_path + TEMP_SUFFIX
        if os.path.exists(original_path):
            # Mover original a backup
            os.rename(original_path, temp_path)
            files_to_restore.append((temp_path, original_path))
            print(f"  -> Aislado: {os.path.basename(original_path)}")


    # 2. EJECUCIÓN DEL TEST (dentro de try/finally para garantizar la restauración)
    try:
        # Cargar dinámicamente el módulo
        spec = importlib.util.spec_from_file_location("prepare_data", SCRIPT_PATH)
        prepare_data = importlib.util.module_from_spec(spec)
        sys.modules[prepare_data.__name__] = prepare_data 
        spec.loader.exec_module(prepare_data)

        # 💥 CRÍTICO: Simular merged_anime.csv (Catálogo de la API)
        NUM_ROWS = 510
        anime_list_ids = list(range(1, NUM_ROWS + 1)) 
        mal_ids = [1000 + i for i in range(NUM_ROWS - 1)] + [9999] 
        
        pd.DataFrame({
            'AniListID': anime_list_ids,
            'MalID': mal_ids,
            'title': [f'Anime Title {i}' for i in range(1, NUM_ROWS + 1)],
            'status': ['FINISHED'] * NUM_ROWS,
            'score': [70] * NUM_ROWS,
            'description': ['Desc'] * NUM_ROWS,
            'type': ['TV'] * NUM_ROWS,
            'episodes': [12] * NUM_ROWS,
            'siteUrl': ['url_test'] * NUM_ROWS, 
            'genres': ["['Action', 'Fantasy']"] * NUM_ROWS, 
            'tags': ["['Shounen', 'Magic']"] * NUM_ROWS, 
            'studios': ["['Studio A']"] * NUM_ROWS,
        }).to_csv(merged_path, index=False) # Se crea el mock en la ruta original

        # 💥 CRÍTICO: Simular user_ratings.csv (Lista del usuario)
        pd.DataFrame([
            {"user_id": 1, "anime_id": 9999, "title": "Coincidence", "my_score": 10, "my_status": "Completed"}, 
            {"user_id": 1, "anime_id": 5000, "title": "Other", "my_score": 5, "my_status": "Watching"},
        ]).to_csv(user_path, index=False) # Se crea el mock en la ruta original

        # CRÍTICO: MOCK para evitar que prepare_data.py intente regenerar dependencias
        def mock_run_script_if_missing(file_path, script_name):
            print(f"✅ MOCK: Se saltó la ejecución de la dependencia '{script_name}' en el test.")

        prepare_data.run_script_if_missing = mock_run_script_if_missing

        # Ejecutar la función principal de prepare_data.py
        print("\n⏳ Fusionando datasets...")
        prepare_data.main()
        assert os.path.exists(final_path), "❌ final_dataset.csv no se generó."

        df_final = pd.read_csv(final_path)

        # CRÍTICO: Conversión de string de lista a lista real (necesario para las aserciones)
        cols_to_convert = ['genres', 'tags', 'studios']
        for col in cols_to_convert:
            if col in df_final.columns:
                df_final[col] = df_final[col].apply(
                    lambda x: ast.literal_eval(x) 
                    if pd.notna(x) and isinstance(x, str) and x.startswith('[') 
                    else []
                )

        # 1. Verificación de integridad
        assert len(df_final) == NUM_ROWS, f"❌ El dataset final tiene {len(df_final)} filas, se esperaban {NUM_ROWS}."

        # 2. Verificar columnas finales y 3. Verificar merge
        assert "user_score" in df_final.columns, "❌ Columna user_score no encontrada."
        coincidencia = df_final[df_final['MAL_ID'] == 9999].iloc[0]
        assert coincidencia['user_score'] == 10.0, "❌ La fusión de 'user_score' falló."

        # 4. Verificar la conversión de tipo (la aserción que falló originalmente)
        genres_value = df_final['genres'].iloc[0]
        assert isinstance(genres_value, list), f"❌ La columna 'genres' (tipo: {type(genres_value)}) no se convirtió a lista."

        print(f"✅ Dataset final guardado: {final_path} ({len(df_final)} filas).")
        print("✅ Test completado sin errores de aserción.")

    finally:
        # 3. LIMPIEZA Y RESTAURACIÓN (TEARDOWN)
        print("\n🧹 Iniciando limpieza y restauración de archivos de producción.")
        mock_files_to_delete = [merged_path, user_path, final_path]
        
        # A. Eliminar los archivos mock creados por el test
        for file_path in mock_files_to_delete:
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