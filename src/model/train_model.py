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

def get_recommendations(df, cosine_sim, top_n=10):
    """Función CORREGIDA - sin duplicados"""
    try:
        debug_log("Calculando recomendaciones...")
        
        # Calcular scores híbridos
        score_vector = df['user_score'].values / 10 
        total_scores = np.dot(cosine_sim, score_vector)
        recs = df.copy()
        recs['hybrid_score'] = total_scores
        
        # Filtrar animes ya vistos
        vistos_ids = recs[recs['my_status'] != 'NO_INTERACTUADO']['AniListID'].tolist()
        blacklist_ids = set(load_blacklist())
        ids_a_excluir = set(vistos_ids).union(blacklist_ids)
        recs = recs[~recs['AniListID'].isin(ids_a_excluir)].copy()
        
        debug_log(f"✅ Filtrado completado. Se excluyeron {len(ids_a_excluir)} animes")
        
        if recs.empty:
            debug_log("⚠️ No hay recomendaciones disponibles.")
            return pd.DataFrame() 
            
        # Filtrar por score mínimo de MAL
        recs = recs[recs['score'] >= 70]
        
        if recs.empty:
            debug_log("⚠️ No hay animes con score >= 70")
            return pd.DataFrame()
        
        # Ordenar y tomar top N
        recs = recs.sort_values(by='hybrid_score', ascending=False)
        
        # Seleccionar columnas de salida
        output_columns = ['id', 'MAL_ID', 'title', 'score', 'genres', 'description', 'type', 'episodes', 'siteUrl', 'studios']
        available_columns = [col for col in output_columns if col in recs.columns]
        
        result = recs[available_columns].head(top_n)
        debug_log(f"✅ {len(result)} recomendaciones generadas")
        return result
        
    except Exception as e:
        debug_log(f"❌ Error en get_recommendations: {e}")
        return pd.DataFrame()

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

if __name__ == "__main__":
    # Para testing local
    df = load_data()
    sim = preprocess_data(df)
    if sim is not None:
        recs = get_recommendations(df, sim)
        print(f"Recomendaciones generadas: {len(recs)}")