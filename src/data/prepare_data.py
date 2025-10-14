# src/data/prepare_data.py (Versión con ruta corregida)
import os
import sys
import pandas as pd
import subprocess
import ast

# CRÍTICO: Sube TRES niveles (lo que funcionó para la ruta del proyecto)
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# CRÍTICO: Eliminar "./data" redundante
DATA_DIR = os.path.join(ROOT_DIR, "data") 

MERGED_ANIME_PATH = os.path.join(DATA_DIR, "merged_anime.csv")
USER_RATINGS_PATH = os.path.join(DATA_DIR, "user_ratings.csv")
FINAL_DATA_PATH = os.path.join(DATA_DIR, "final_dataset.csv")

FETCH_SCRIPT_PATH = "fetch_datasets.py"
PARSE_SCRIPT_PATH = "parse_xml.py"

# === FUNCIONES ===
def get_script_full_path(script_name):
    """Devuelve la ruta completa al script que está en src/data/."""
    # Esto sigue apuntando a src/data/script.py, que es correcto
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), script_name)

# Define un tamaño mínimo razonable (10 KB es un margen seguro)
MIN_FILE_SIZE = 10 * 1024 # 10 KB

def run_script_if_missing(file_path, script_name):
    # ⚠️ CAMBIO CRÍTICO: Usar el nuevo tamaño mínimo
    is_missing = not os.path.exists(file_path) or os.path.getsize(file_path) < MIN_FILE_SIZE

    if is_missing:
        print(f"\n=======================================================")
        print(f"⚠️ Archivo '{os.path.basename(file_path)}' no encontrado/vacío. Generando...")
        print(f"⏳ Ejecutando '{script_name}'...")
        print(f"=======================================================")
        try:
            subprocess.run(
                [sys.executable, get_script_full_path(script_name)],
                check=True,
                stdout=sys.stdout,
                stderr=sys.stderr,
            )
            
            print(f"✅ Ejecución de '{script_name}' finalizada.")
        except subprocess.CalledProcessError:
            print(f"❌ Error: '{script_name}' falló durante la ejecución.")
            sys.exit(1)
        
         # ⚠️ CAMBIO CRÍTICO: La verificación final
        if not os.path.exists(file_path) or os.path.getsize(file_path) < MIN_FILE_SIZE:
            print(f"❌ Error Crítico: '{script_name}' finalizó pero el archivo '{os.path.basename(file_path)}' sigue vacío o muy pequeño (< {MIN_FILE_SIZE // 1024} KB).")
            sys.exit(1)
    else:
        print(f"✔ Archivo '{os.path.basename(file_path)}' encontrado.")


def main():
    # 1. Asegurar que los archivos de origen se generen en la carpeta 'data' de la raíz
    run_script_if_missing(MERGED_ANIME_PATH, FETCH_SCRIPT_PATH)
    run_script_if_missing(USER_RATINGS_PATH, PARSE_SCRIPT_PATH)

    # 2. Cargar datos
    try:
        # Los archivos ahora se cargan desde la ruta correcta
        df_anime = pd.read_csv(MERGED_ANIME_PATH, low_memory=False)
        df_ratings = pd.read_csv(USER_RATINGS_PATH)
    except Exception as e:
        print(f"❌ Error: No se pudieron cargar los archivos requeridos para la fusión. {e}")
        sys.exit(1)

    print("\n⏳ Fusionando datasets...")

    # 3. Preparación de DataFrames
    df_ratings = df_ratings.rename(columns={
        'anime_id': 'mal_id_merge',
        'my_score': 'user_score'
    })
    df_ratings['mal_id_merge'] = pd.to_numeric(df_ratings['mal_id_merge'], errors='coerce')
    
    # Asegurar que MalID es numérico para la fusión
    if 'MalID' in df_anime.columns:
        df_anime['MalID'] = pd.to_numeric(df_anime['MalID'], errors='coerce')
    else:
        print("❌ Error: Columna 'MalID' no encontrada en merged_anime.csv.")
        sys.exit(1)
        
    if 'AniListID' not in df_anime.columns:
        print("❌ Error: Columna 'AniListID' no encontrada en merged_anime.csv.")
        sys.exit(1)


    # 4. Fusión
    df_final = pd.merge(
        df_anime,
        df_ratings[['mal_id_merge', 'user_score', 'my_status']],
        left_on='MalID',
        right_on='mal_id_merge',
        how='left'
    ).rename(columns={'siteUrl': 'url_anilist'})

    # 5. Limpieza y Filtrado
    df_final.drop(columns=['mal_id_merge'], errors='ignore', inplace=True)
    
    # Renombrar columnas a la convención final del dataset
    df_final = df_final.rename(columns={'AniListID': 'id', 'MalID': 'MAL_ID'})
    
    # Asegurar que solo tengamos filas con títulos válidos
    df_final = df_final[df_final['title'].astype(bool)].copy()
    
    # Eliminar duplicados basados en el ID principal (AniList ID, ahora llamado 'id')
    if 'id' in df_final.columns:
         df_final.drop_duplicates(subset=['id'], keep='first', inplace=True)
         
    # Convertir las columnas de lista (que se guardan como string en CSV)
    cols_to_convert = ['genres', 'tags', 'studios']
    for col in cols_to_convert:
        if col in df_final.columns:
            # Usar literal_eval para convertir la string de lista a lista real
            df_final[col] = df_final[col].apply(lambda x: ast.literal_eval(x) if pd.notna(x) and isinstance(x, str) and x.startswith('[') else [])


    # 6. CHEQUEO CRÍTICO DE FILAS MÍNIMAS
    if len(df_final) < 500: 
        print(f"❌ Error Crítico: El dataset final es demasiado pequeño ({len(df_final)} filas). La fusión falló. Revisar archivos de origen.")
        sys.exit(1) 
        
    # 7. Guardar
    columnas = ['id', 'MAL_ID', 'user_score', 'my_status', 'status', 'title', 'genres',
                'tags', 'score', 'description', 'type', 'episodes', 'url_anilist', 'studios']
    df_final = df_final[[c for c in columnas if c in df_final.columns]].copy()
    
    # Rellenar los NaN en my_status con cadena vacía para el filtro posterior en train_model.py
    if 'my_status' in df_final.columns:
        df_final['my_status'] = df_final['my_status'].fillna('')

    os.makedirs(DATA_DIR, exist_ok=True)
    df_final.to_csv(FINAL_DATA_PATH, index=False, encoding='utf-8')
    print(f"✅ Dataset final guardado: {os.path.abspath(FINAL_DATA_PATH)} ({len(df_final)} filas).")

if __name__ == "__main__":
    main()