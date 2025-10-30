# src/data/prepare_data.py - CORREGIDO (Fusión por MAL ID y renombramiento de score)
import os
import sys
import pandas as pd
import subprocess
import ast
# Importación necesaria para el orquestador si parse_xml.py está en el mismo nivel
try:
    from src.data.parse_xml import parse_and_save_ratings 
except ImportError:
    # Manejo si se ejecuta directamente y no está configurado el path
    pass 

# --- FUNCIÓN DE LOGGING ---
def log_info(message):
    print(message, file=sys.stderr, flush=True)
def log_error(message):
    print(f"❌ {message}", file=sys.stderr, flush=True)
# --------------------------

# CRÍTICO: Sube TRES niveles (de src/data/ a la raíz del proyecto)
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(ROOT_DIR, "data") 

# Rutas de los archivos intermedios y finales
MERGED_ANIME_PATH = os.path.join(DATA_DIR, "merged_anime.csv") 
USER_RATINGS_PATH = os.path.join(DATA_DIR, "user_ratings.csv") 
FINAL_DATA_PATH = os.path.join(DATA_DIR, "final_dataset.csv") 

# === FUNCIONES DE LÓGICA PRINCIPAL ===
def merge_and_clean_data():
    """
    Carga el dataset principal y los ratings del usuario, los fusiona
    usando el ID de MAL (MalID) y guarda el dataset final.
    """
    log_info("🔄 Fusionando datos de anime y ratings de usuario por MAL ID...")
    
    if not os.path.exists(MERGED_ANIME_PATH):
        raise FileNotFoundError(f"❌ Error: El dataset base de anime no existe: {MERGED_ANIME_PATH}")
    if not os.path.exists(USER_RATINGS_PATH):
        raise FileNotFoundError(f"❌ Error: El archivo de ratings de usuario no existe: {USER_RATINGS_PATH}")

    try:
        # Cargar los datasets
        df_anime = pd.read_csv(MERGED_ANIME_PATH)
        df_ratings = pd.read_csv(USER_RATINGS_PATH)
    except Exception as e:
        log_error(f"Error al cargar los datasets: {e}")
        raise e

    # Renombrar columnas para la fusión y la lógica
    # CRÍTICO: Renombrar MalID en df_anime para que coincida con anime_id en df_ratings
    df_anime = df_anime.rename(columns={'idMal': 'anime_id', 'id': 'AniListID', 'averageScore': 'score'})
    df_ratings = df_ratings.rename(columns={'anime_id': 'anime_id', 'my_score': 'user_score'})

    # 💡 Se ha detectado que el df_anime tiene 'id' (AniListID) y 'anime_id' (MalID) después de renombrar
    # Usaremos 'anime_id' (MalID) para la fusión.
    # df_anime['anime_id'] es el MalID (el ID de la lista del usuario)
    # df_anime['AniListID'] es el ID principal del dataset base

    # Fusionar por el ID de MyAnimeList (que es 'anime_id' en ambos después del renombramiento)
    df_merged = pd.merge(
        df_anime,
        df_ratings[['anime_id', 'user_score', 'my_status']],
        on='anime_id',
        how='left'
    )
    
    # Rellenar los valores nulos para animes que el usuario NO ha interactuado
    df_merged['user_score'] = df_merged['user_score'].fillna(0).astype(int)
    df_merged['my_status'] = df_merged['my_status'].fillna('NO_INTERACTUADO')

    # Renombrar las columnas finales para la consistencia
    df_final = df_merged.rename(columns={'anime_id': 'MAL_ID', 'AniListID': 'id'})
    
    # 💡 Convertir las columnas de listas de string a listas de Python (necesario si se lee de CSV)
    # df_final['genres'] = df_final['genres'].apply(
    #     lambda x: ast.literal_eval(x) if isinstance(x, str) and x.startswith('[') else []
    # )
            
    # Asegurar el orden de columnas
    columnas = ['id', 'MAL_ID', 'user_score', 'my_status', 'status', 'title', 'genres',
                'tags', 'score', 'description', 'type', 'episodes', 'siteUrl', 'studios']
    
    # Usar las columnas que realmente existen después del merge
    df_final = df_final[[c for c in columnas if c in df_final.columns]].copy()
    
    # Asegurarse de que el directorio exista
    os.makedirs(DATA_DIR, exist_ok=True)
    df_final.to_csv(FINAL_DATA_PATH, index=False)
    
    log_info(f"🎉 Dataset final de {len(df_final)} filas guardado en: {FINAL_DATA_PATH}")


# === FUNCIÓN DE ORQUESTACIÓN ===
def run_full_preparation_flow(username):
    """
    Ejecuta el parsing de datos de usuario y la fusión con el dataset base.
    El script de descarga (download_mal_list.py) debe ser llamado ANTES.
    """
    log_info("🛠️ Iniciando el flujo simplificado de preparación de datos...")
    
    # 1. Asegurarse de que los ratings del usuario estén parseados
    try:
        # Esta función lee el JSON descargado por download_mal_list.py y genera user_ratings.csv
        parse_and_save_ratings()
        log_info("✅ Ratings de usuario parseados.")
    except Exception as e:
        log_error(f"Error durante el parseo de datos de usuario: {e}")
        raise e
    
    # 2. Fusionar y limpiar los datos finales
    merge_and_clean_data()
    
    log_info("✅ Flujo de preparación de datos completado exitosamente.")
    return True


if __name__ == '__main__':
    # Este bloque se mantiene para pruebas locales.
    log_info("Ejecutando prepare_data.py directamente (solo para pruebas locales).")
    
    if len(sys.argv) > 1:
        USERNAME = sys.argv[1]
    else:
        USERNAME = "SrAlex16" 
    
    log_info(f"Usando usuario simulado para prueba local: {USERNAME}")
    
    try:
        # Se asume que download_mal_list.py ya se ejecutó con el username para crear el JSON.
        run_full_preparation_flow(USERNAME)
    except Exception as e:
        log_error(f"Fallo en el flujo de preparación: {e}")
        sys.exit(1)