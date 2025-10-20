# src/model/train_model.py - VERSIÓN CORREGIDA
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel
from sklearn.decomposition import TruncatedSVD
import os
import sys
import json
import subprocess
import numpy as np
from collections import Counter
import ast
from datetime import datetime

# Configuración de paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR))
DATA_DIR = os.path.join(ROOT_DIR, "data")
FINAL_DATASET_PATH = os.path.join(DATA_DIR, "final_dataset.csv")
USER_RATINGS_PATH = os.path.join(DATA_DIR, "user_ratings.csv") 
BLACKLIST_PATH = os.path.join(DATA_DIR, "blacklist.json")
PREPARE_SCRIPT_PATH = os.path.join(ROOT_DIR, 'src', 'data', 'prepare_data.py')

def debug_log(message):
    print(f"🔍 [DEBUG] {message}", file=sys.stderr, flush=True)

def get_project_root():
    return ROOT_DIR

def load_blacklist():
    if not os.path.exists(BLACKLIST_PATH):
        return []
    try:
        with open(BLACKLIST_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return [int(id) for id in data if str(id).isdigit()]
    except Exception:
        return []

def load_data():
    if not os.path.exists(FINAL_DATASET_PATH) or os.path.getsize(FINAL_DATASET_PATH) <= 100:
        debug_log("⚠️ Archivo 'final_dataset.csv' no encontrado. Generando...")
        try:
            subprocess.run([sys.executable, PREPARE_SCRIPT_PATH], check=True)
        except subprocess.CalledProcessError as e:
            debug_log(f"❌ Error al ejecutar prepare_data.py: {e}")
            sys.exit(1)

    df = pd.read_csv(FINAL_DATASET_PATH)
    
    df['user_score'] = df['user_score'].fillna(0.0)
    df['my_status'] = df['my_status'].fillna('NO_INTERACTUADO')
    df['my_status'] = df['my_status'].replace('', 'NO_INTERACTUADO') 

    for col in ['genres', 'tags']:
        df[col] = df[col].apply(lambda x: ast.literal_eval(x) if pd.notna(x) and isinstance(x, str) and '[' in x else [])
        df[col] = df[col].apply(lambda x: ' '.join([str(i).replace(" ", "") for i in x]))

    df['combined_features'] = df.apply(
        lambda row: f"{row['title']} {row['genres']} {row['tags']} {row['description']}", 
        axis=1
    )
    
    df = df.rename(columns={'type': 'Tipo'})
    df['AniListID'] = df['id']

    return df

def preprocess_data(df):
    tfidf = TfidfVectorizer(stop_words='english')
    df['combined_features'] = df['combined_features'].fillna('')
    tfidf_matrix = tfidf.fit_transform(df['combined_features'])
    debug_log(f"✅ TF-IDF completado: {tfidf_matrix.shape}")
    
    n_components = min(tfidf_matrix.shape) - 1
    if n_components <= 0: 
        return None
        
    n_svd = min(200, n_components) 
    svd = TruncatedSVD(n_components=n_svd, random_state=42)
    latent_matrix = svd.fit_transform(tfidf_matrix)
    debug_log(f"✅ SVD aplicado: {latent_matrix.shape}")
    
    cosine_sim = linear_kernel(latent_matrix, latent_matrix)
    debug_log(f"✅ Similitud coseno calculada: {cosine_sim.shape}")
    return cosine_sim

# src/model/train_model.py

import pandas as pd
import numpy as np
# ... (otras importaciones)

# ... (Mantener las funciones preprocess_data y load_data)

def get_recommendations(df, df_processed, top_n=30):
    """
    Obtiene las recomendaciones basadas en el score simple precalculado.
    Excluye CUALQUIER anime que esté presente en el DataFrame del usuario (df),
    utilizando tanto el ID de AniList ('id') como el ID de MAL ('MAL_ID').
    """
    
    # 1. Obtener la lista de IDs de anime que están en la lista del usuario.
    # ⚠️ CORRECCIÓN CLAVE: Usar AMBOS IDs para robustez
    
    # IDs de AniList que están en la lista del usuario
    anilist_ids_en_lista = df['id'].dropna().unique().astype(int).tolist()
    
    # IDs de MAL que están en la lista del usuario
    # Convertir a int para una comparación limpia, ignorando NaNs
    mal_ids_en_lista = df['MAL_ID'].dropna().unique().astype(int).tolist()
    
    
    print(f"Excluyendo {len(anilist_ids_en_lista)} IDs de AniList y {len(mal_ids_en_lista)} IDs de MAL de la lista del usuario.")

    # 2. Filtrar el dataset procesado (df_processed)
    
    # Excluir por ID de AniList
    df_recommendations = df_processed[~df_processed['id'].isin(anilist_ids_en_lista)].copy()
    
    # Excluir también por ID de MAL (por si el merge falló con el ID de AniList)
    df_recommendations = df_recommendations[~df_recommendations['MAL_ID'].isin(mal_ids_en_lista)].copy()
    
    # 3. Calcular la puntuación de recomendación final
    df_recommendations['final_score'] = df_recommendations['normalized_score'] * df_recommendations['score']
    
    # 4. Filtrar por score mínimo de AniList (score >= 70)
    df_recommendations = df_recommendations[df_recommendations['score'] >= 70].copy() 
    
    print(f"✅ Filtrado completado. Animes elegibles restantes: {len(df_recommendations)}.")
    
    if df_recommendations.empty:
        print("⚠️ No hay recomendaciones disponibles después del filtrado.")
        return pd.DataFrame() 

    # 5. Ordenar y tomar top N
    df_recommendations = df_recommendations.sort_values(by='final_score', ascending=False)
    
    # Seleccionar solo las columnas necesarias para el output
    output_columns = ['id', 'MAL_ID', 'title', 'score', 'genres', 'description', 'type', 'episodes', 'siteUrl', 'studios']
    
    # Tomar los Top N y devolver solo las columnas de salida
    return df_recommendations[output_columns].head(top_n)

def get_anime_statistics(df):
    """Calcula estadísticas simples"""
    stats = {}
    
    if df.empty:
        return stats
        
    # Género más popular entre animes calificados
    rated_anime = df[df['user_score'].notna() & (df['user_score'] > 0)]
    if not rated_anime.empty and 'genres' in rated_anime.columns:
        genre_counter = Counter()
        rated_anime['genres'].apply(lambda x: genre_counter.update(x if isinstance(x, list) else x.split()))
        most_watched_genre = genre_counter.most_common(1)
        stats['most_watched_genre'] = most_watched_genre[0][0] if most_watched_genre else 'N/A'

    # Puntuación promedio del usuario
    if 'user_score' in df.columns:
        avg_score = rated_anime['user_score'].mean()
        stats['average_user_score'] = round(avg_score, 2) if pd.notna(avg_score) else 0.0

    # Total de animes en la lista del usuario
    if 'my_status' in df.columns:
        total_in_list = df['my_status'].count()
        stats['total_anime_in_list'] = int(total_in_list)

    return stats

def debug_user_animes(df):
    """Debug: Ver qué animes tiene el usuario en su lista"""
    user_animes = df[df['my_status'] != 'NO_INTERACTUADO'][['id', 'title', 'my_status', 'user_score']]
    
    debug_log(f"📊 USER ANIME LIST DEBUG:")
    debug_log(f"Total animes en lista: {len(user_animes)}")
    
    # Contar por estado
    status_counts = user_animes['my_status'].value_counts()
    for status, count in status_counts.items():
        debug_log(f"  {status}: {count} animes")
    
    # Mostrar algunos ejemplos
    sample_animes = user_animes.head(5)
    for _, anime in sample_animes.iterrows():
        debug_log(f"  📺 {anime['title']} - {anime['my_status']} (Score: {anime['user_score']})")
    
    return user_animes

if __name__ == "__main__":
    # Para testing local
    df = load_data()
    sim = preprocess_data(df)
    if sim is not None:
        recs = get_recommendations(df, sim)
        print(f"Recomendaciones generadas: {len(recs)}")