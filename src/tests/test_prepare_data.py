# src/tests/test_prepare_data.py

import os
import sys
import pandas as pd
import importlib.util

# CRÍTICO: Detectar la raíz del proyecto (2 niveles hacia arriba desde src/tests)
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(ROOT_DIR, "data")
SCRIPT_PATH = os.path.join(ROOT_DIR, "src", "data", "prepare_data.py")

# RENOMBRAR: run_prepare_data_test -> test_prepare_data
def test_prepare_data():
    print("🔍 Test: prepare_data.py")

    spec = importlib.util.spec_from_file_location("prepare_data", SCRIPT_PATH)
    prepare_data = importlib.util.module_from_spec(spec)
    sys.modules[prepare_data.__name__] = prepare_data 
    spec.loader.exec_module(prepare_data)

    # Rutas de archivos simulados (usando las rutas reales para el test)
    merged_path = os.path.join(DATA_DIR, "merged_anime.csv")
    user_path = os.path.join(DATA_DIR, "user_ratings.csv")
    final_path = os.path.join(DATA_DIR, "final_dataset.csv")

    os.makedirs(DATA_DIR, exist_ok=True) # Asegurar que la carpeta exista

    # 💥 CRÍTICO: Simular merged_anime.csv (Catálogo de la API)
    # CORRECCIÓN: Aumentar el número de filas simuladas a más de 500 para evitar el SystemExit en prepare_data.main()
    mock_anime_data = []
    # Generar 502 filas (más de 500 para el chequeo de prepare_data.py)
    for i in range(1, 503): 
        mock_anime_data.append({
            "AniListID": i, 
            "MalID": i, 
            "title": f"Anime Title {i}", 
            "description": "Mock description", 
            "genres": "['Action']", 
            "tags": "['Shounen']", 
            "score": 80, 
            "type": "TV"
        })
    pd.DataFrame(mock_anime_data).to_csv(merged_path, index=False)


    # 💥 CRÍTICO: Simular user_ratings.csv (Lista del usuario)
    pd.DataFrame([
        {"user_id": 1, "anime_id": 1, "title": "Anime Title 1", "my_score": 9, "my_status": "Completed"}, # 'anime_id' es el ID de MAL/AniList
        {"user_id": 1, "anime_id": 2, "title": "Anime Title 2", "my_score": 7, "my_status": "Completed"},
    ]).to_csv(user_path, index=False)

    # CRÍTICO: MOCK para evitar que prepare_data.py intente regenerar dependencias
    def mock_run_script_if_missing(file_path, script_name):
        """Mock que asume que el archivo ya existe y salta la ejecución del subprocess."""
        print(f"✅ MOCK: Se saltó la ejecución de '{script_name}' en el test.")

    # Reemplazar la función real con el mock ANTES de llamar a main
    prepare_data.run_script_if_missing = mock_run_script_if_missing

    # Ejecutar la función principal de prepare_data.py
    prepare_data.main()
    assert os.path.exists(final_path), "❌ final_dataset.csv no se generó."

    df_final = pd.read_csv(final_path)
    
    # Verificar columnas finales (después de renombrado y limpieza)
    assert len(df_final) >= 500, "❌ El dataset final tiene menos de 500 filas."
    assert "user_score" in df_final.columns, "❌ Columna user_score no encontrada en el dataset final."
    assert "id" in df_final.columns, "❌ Columna 'id' (el ID unificado) no encontrada."
    assert "MAL_ID" in df_final.columns, "❌ Columna 'MAL_ID' no encontrada."
    assert "my_status" in df_final.columns, "❌ Columna 'my_status' no encontrada."
    
    # Verificar que el merge funcionó para el ID 1 (puntuación 9.0)
    assert df_final[df_final['id'] == 1]['user_score'].iloc[0] == 9.0, "❌ Error en el merge: user_score no se cargó correctamente (debería ser 9.0)."
    
    print(f"✅ final_dataset.csv generado correctamente con {len(df_final)} filas.")