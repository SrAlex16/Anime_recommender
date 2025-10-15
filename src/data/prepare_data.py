# src/data/prepare_data.py (Versión con flujo automatizado y nombres originales)
import os
import sys
import pandas as pd
import subprocess
import ast

# CRÍTICO: Sube TRES niveles (lo que funcionó para la ruta del proyecto)
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(ROOT_DIR, "data") 

MERGED_ANIME_PATH = os.path.join(DATA_DIR, "merged_anime.csv")
USER_RATINGS_PATH = os.path.join(DATA_DIR, "user_ratings.csv")
FINAL_DATA_PATH = os.path.join(DATA_DIR, "final_dataset.csv")

FETCH_SCRIPT_PATH = "fetch_datasets.py"
PARSE_SCRIPT_PATH = "parse_xml.py" # ⚠️ Mantenemos el nombre original, ahora lee JSON
DOWNLOAD_SCRIPT_PATH = "download_mal_list.py" # 💡 Nuevo script

# === FUNCIONES ===
def get_script_full_path(script_name):
    """Devuelve la ruta completa al script que está en src/data/."""
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), script_name)

MIN_FILE_SIZE = 10 * 1024 # 10 KB

def run_script_if_missing(file_path, script_name):
    is_missing = not os.path.exists(file_path) or os.path.getsize(file_path) < MIN_FILE_SIZE

    # ⚠️ CAMBIO CRÍTICO: Si falta el archivo de ratings o es el script de descarga, forzamos la ejecución.
    if script_name == DOWNLOAD_SCRIPT_PATH:
        # Ejecutamos el script de descarga de usuario que pide el nombre
        print(f"\n=======================================================")
        print(f"⚠️ Iniciando descarga de lista de usuario...")
        print(f"⏳ Ejecutando '{DOWNLOAD_SCRIPT_PATH}' (pide nombre de usuario)...")
        print(f"=======================================================")
        try:
            # 1. Ejecución del script que pide el nombre de usuario y descarga el JSON
            subprocess.run(
                [sys.executable, get_script_full_path(DOWNLOAD_SCRIPT_PATH)],
                check=True, # Detiene si el script de descarga falla (ej: usuario no encontrado)
                stdout=sys.stdout,
                stderr=sys.stderr,
            )
            print(f"✅ Ejecución de '{DOWNLOAD_SCRIPT_PATH}' finalizada.")
            
            # 2. Después de descargar el JSON, ejecutamos el parser (parse_xml.py modificado)
            print(f"\n=======================================================")
            print(f"⏳ Ejecutando '{PARSE_SCRIPT_PATH}' para convertir JSON a CSV...")
            print(f"=======================================================")
            subprocess.run(
                [sys.executable, get_script_full_path(PARSE_SCRIPT_PATH)],
                check=True, # Detiene si el parser falla
                stdout=sys.stdout,
                stderr=sys.stderr,
            )
            print(f"✅ Ejecución de '{PARSE_SCRIPT_PATH}' finalizada.")
            
            # 3. Verificación final
            if not os.path.exists(USER_RATINGS_PATH) or os.path.getsize(USER_RATINGS_PATH) < 100: 
                print(f"❌ Error Crítico: La lista de usuario no pudo ser generada. Abortando.")
                sys.exit(1)
            
            return 
            
        except subprocess.CalledProcessError:
            print(f"❌ Error: El proceso de descarga/parseo falló. Abortando.")
            sys.exit(1)


    if is_missing:
        # Esto solo se ejecuta para la descarga del catálogo (fetch_datasets.py)
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
        
            if not os.path.exists(file_path) or os.path.getsize(file_path) < MIN_FILE_SIZE:
                print(f"❌ Error Crítico: '{script_name}' falló al generar el archivo.")
                sys.exit(1)
        except subprocess.CalledProcessError:
            print(f"❌ Error: '{script_name}' falló durante la ejecución.")
            sys.exit(1)
    else:
        print(f"✔ Archivo '{os.path.basename(file_path)}' encontrado.")


def main():
    # 1. Asegurar que el catálogo de ANIME se genere (si falta)
    run_script_if_missing(MERGED_ANIME_PATH, FETCH_SCRIPT_PATH)
    
    # 2. Asegurar que los ratings del usuario se generen (SIEMPRE SE EJECUTA LA DESCARGA/PARSEO)
    # Ejecutamos el proceso completo de descarga (pide nombre) y parseo (genera CSV)
    # Pasamos el nombre del script de descarga, que es la entrada al proceso de ratings
    run_script_if_missing(USER_RATINGS_PATH, DOWNLOAD_SCRIPT_PATH)


    # 3. Cargar datos
    try:
        df_anime = pd.read_csv(MERGED_ANIME_PATH, low_memory=False)
        df_ratings = pd.read_csv(USER_RATINGS_PATH)
    except Exception as e:
        print(f"❌ Error: No se pudieron cargar los archivos requeridos para la fusión. {e}")
        sys.exit(1)

    print("\n⏳ Fusionando datasets...")

    # 4. Fusión (Lógica sin cambios)
    df_ratings = df_ratings.rename(columns={
        'anime_id': 'mal_id_merge',
        'my_score': 'user_score'
    })
    df_ratings['mal_id_merge'] = pd.to_numeric(df_ratings['mal_id_merge'], errors='coerce')
    
    if 'MalID' in df_anime.columns:
        df_anime['MalID'] = pd.to_numeric(df_anime['MalID'], errors='coerce')
    else:
        print("❌ Error: Columna 'MalID' no encontrada en merged_anime.csv.")
        sys.exit(1)
        
    if 'AniListID' not in df_anime.columns:
        print("❌ Error: Columna 'AniListID' no encontrada en merged_anime.csv.")
        sys.exit(1)

    df_final = pd.merge(
        df_anime,
        df_ratings[['mal_id_merge', 'user_score', 'my_status']],
        left_on='MalID',
        right_on='mal_id_merge',
        how='left'
    ).rename(columns={'siteUrl': 'url_anilist'})

    # 5. Limpieza y Guardado (Lógica sin cambios)
    df_final.drop(columns=['mal_id_merge'], errors='ignore', inplace=True)
    df_final = df_final.rename(columns={'AniListID': 'id', 'MalID': 'MAL_ID'})
    df_final = df_final[df_final['title'].astype(bool)].copy()
    
    if 'id' in df_final.columns:
         df_final.drop_duplicates(subset=['id'], keep='first', inplace=True)
         
    cols_to_convert = ['genres', 'tags', 'studios']
    for col in cols_to_convert:
        if col in df_final.columns:
            df_final[col] = df_final[col].apply(lambda x: ast.literal_eval(x) if pd.notna(x) and isinstance(x, str) and x.startswith('[') else [])

    if len(df_final) < 500: 
        print(f"❌ Error Crítico: El dataset final es demasiado pequeño ({len(df_final)} filas).")
        sys.exit(1) 
        
    columnas = ['id', 'MAL_ID', 'user_score', 'my_status', 'status', 'title', 'genres',
                'tags', 'score', 'description', 'type', 'episodes', 'url_anilist', 'studios']
    df_final = df_final[[c for c in columnas if c in df_final.columns]].copy()
    
    if 'my_status' in df_final.columns:
        df_final['my_status'] = df_final['my_status'].fillna('')

    os.makedirs(DATA_DIR, exist_ok=True)
    df_final.to_csv(FINAL_DATA_PATH, index=False, encoding='utf-8')
    print(f"✅ Dataset final guardado: {os.path.abspath(FINAL_DATA_PATH)} ({len(df_final)} filas).")

if __name__ == "__main__":
    main()