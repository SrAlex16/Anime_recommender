# src/data/prepare_data.py (Versión con flujo automatizado y orquestación)
import os
import sys
import pandas as pd
import subprocess
import ast

# CRÍTICO: Sube TRES niveles (de src/data/ a la raíz del proyecto)
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(ROOT_DIR, "data") 

# Rutas de los archivos intermedios y finales
MERGED_ANIME_PATH = os.path.join(DATA_DIR, "merged_anime.csv") # Output de fetch_datasets.py
USER_RATINGS_PATH = os.path.join(DATA_DIR, "user_ratings.csv") # Output de parse_xml.py
FINAL_DATA_PATH = os.path.join(DATA_DIR, "final_dataset.csv") # Output de este script

# Rutas de los scripts que se ejecutarán como subprocesos
FETCH_SCRIPT_PATH = "fetch_datasets.py"
PARSE_SCRIPT_PATH = "parse_xml.py"

# === FUNCIONES DE UTILIDAD ===
def get_script_full_path(script_name):
    """Devuelve la ruta completa al script que está en src/data/."""
    # Los scripts están en el mismo directorio (src/data/)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), script_name)

MIN_FILE_SIZE = 10 * 1024 # 10 KB

def run_script_if_missing(file_path, script_name):
    """
    Ejecuta un script como subproceso si el archivo de salida
    está ausente, es demasiado pequeño o ha fallado previamente.
    """
    is_missing = not os.path.exists(file_path) or os.path.getsize(file_path) < MIN_FILE_SIZE
    
    if is_missing:
        full_script_path = get_script_full_path(script_name)
        
        print(f"⚙️ Ejecutando script: {script_name} para generar {os.path.basename(file_path)}")
        
        try:
            # Ejecutar el script usando el intérprete actual (sys.executable)
            result = subprocess.run(
                [sys.executable, full_script_path], 
                capture_output=True, 
                text=True, 
                check=True, # Lanza CalledProcessError si el código de salida no es 0
                cwd=DATA_DIR # Asegurarse de que el directorio de trabajo sea 'data' si los scripts lo necesitan
            )
            # Imprimir salida del script para logs de Render
            print(result.stdout)
            print(result.stderr)
            
            if result.returncode != 0:
                raise subprocess.CalledProcessError(result.returncode, result.args, output=result.stdout, stderr=result.stderr)
                
            print(f"✅ Ejecución de {script_name} completada.")
        
        except subprocess.CalledProcessError as e:
            print(f"❌ Error al ejecutar {script_name}. Salida: {e.stderr.strip()}")
            # Re-lanzar el error para que sea capturado por el servicio principal
            raise e
        except Exception as e:
            print(f"❌ Error desconocido al ejecutar {script_name}: {str(e)}")
            raise e


# === FUNCIÓN DE LÓGICA PRINCIPAL ===
def merge_and_clean_data():
    """
    Carga el dataset principal y los ratings del usuario, los fusiona
    y guarda el dataset final en final_dataset.csv.
    """
    print("🔄 Fusionando datos de anime y ratings de usuario...")
    
    if not os.path.exists(MERGED_ANIME_PATH):
        raise FileNotFoundError(f"Archivo base de anime no encontrado: {MERGED_ANIME_PATH}")
    if not os.path.exists(USER_RATINGS_PATH):
        raise FileNotFoundError(f"Archivo de ratings de usuario no encontrado: {USER_RATINGS_PATH}")

    try:
        df_anime = pd.read_csv(MERGED_ANIME_PATH)
        df_ratings = pd.read_csv(USER_RATINGS_PATH)
    except Exception as e:
        print(f"❌ Error al leer archivos CSV: {e}")
        raise e

    # 1. Preparar df_anime: convertir la columna de ID a entero para el merge
    # Se asume que el ID de AniList es el ID principal para el merge
    df_anime['id_merge'] = df_anime['AniListID'].astype(str).str.split('.').str[0].astype(int)

    # 2. Preparar df_ratings: renombrar y limpiar
    # Asumimos que la columna 'anime_id' en df_ratings es el AniList ID
    df_ratings = df_ratings.rename(columns={'anime_id': 'id_merge', 'my_score': 'user_score'})
    df_ratings = df_ratings[df_ratings['user_score'] > 0] # Solo animes calificados

    # 3. Merge: Unir ratings del usuario con el dataset principal
    df_final = pd.merge(
        df_anime, 
        df_ratings[['id_merge', 'user_score', 'my_status']], 
        on='id_merge', 
        how='left'
    ).rename(columns={'id_merge': 'AniListID'})
    
    # 4. Limpieza y Guardado (Lógica sin cambios)
    df_final.drop(columns=['mal_id_merge', 'MAL_ID'], errors='ignore', inplace=True)
    df_final = df_final.rename(columns={'AniListID': 'id', 'MalID': 'MAL_ID'})
    df_final = df_final[df_final['title'].astype(bool)].copy()
    
    if 'id' in df_final.columns:
         df_final.drop_duplicates(subset=['id'], keep='first', inplace=True)
         
    # Intentar convertir listas de strings de vuelta a listas (para TF-IDF)
    cols_to_convert = ['genres', 'tags', 'studios']
    for col in cols_to_convert:
        if col in df_final.columns:
            df_final[col] = df_final[col].apply(
                lambda x: ast.literal_eval(x) if pd.notna(x) and isinstance(x, str) and x.startswith('[') else []
            )

    if len(df_final) < 500: 
        print(f"❌ Error: El dataset final es demasiado pequeño ({len(df_final)} filas).")
        # En Render, esto puede ser un error fatal, pero lo dejamos pasar si es solo advertencia
        # sys.exit(1) # No usar sys.exit() aquí, solo lanzar excepción si es fatal.
        
    columnas = ['id', 'MAL_ID', 'user_score', 'my_status', 'status', 'title', 'genres',
                'tags', 'score', 'description', 'type', 'episodes', 'siteUrl', 'studios']
    
    df_final = df_final[[c for c in columnas if c in df_final.columns]].copy()
    
    # Asegurarse de que el directorio exista
    os.makedirs(DATA_DIR, exist_ok=True)
    df_final.to_csv(FINAL_DATA_PATH, index=False)
    
    print(f"🎉 Dataset final de {len(df_final)} filas guardado en: {FINAL_DATA_PATH}")


# === FUNCIÓN DE ORQUESTACIÓN (LA QUE FALTABA) ===
def run_full_preparation_flow(username):
    """
    Ejecuta todos los pasos de preparación y limpieza de datos en orden.
    """
    print("🛠️ Iniciando el flujo completo de preparación de datos...")
    
    # 1. Asegurarse de que el dataset de anime base exista (fetch_datasets.py)
    run_script_if_missing(MERGED_ANIME_PATH, FETCH_SCRIPT_PATH)
    
    # 2. Asegurarse de que los ratings del usuario estén parseados (parse_xml.py)
    run_script_if_missing(USER_RATINGS_PATH, PARSE_SCRIPT_PATH)
    
    # 3. Fusionar y limpiar los datos finales
    merge_and_clean_data()
    
    print("✅ Flujo de preparación de datos completado exitosamente.")
    return True


if __name__ == '__main__':
    # Bloque de ejecución local para pruebas
    print("Ejecutando prepare_data.py directamente (solo para pruebas locales).")
    try:
        # Nota: La lista de usuario debe estar en DATA_DIR/user_mal_list.json antes de ejecutar esto
        run_full_preparation_flow("test_user") 
    except Exception as e:
        print(f"Fallo en la ejecución principal: {e}")
        sys.exit(1)