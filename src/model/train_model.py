# src/model/train_model.py
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
import time
from datetime import datetime

# Detectar raíz del proyecto
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR))  # Sube de src/model a Anime_recommender/
DATA_DIR = os.path.join(ROOT_DIR, "data")
FINAL_DATASET_PATH = os.path.join(DATA_DIR, "final_dataset.csv")
USER_RATINGS_PATH = os.path.join(DATA_DIR, "user_ratings.csv") 
BLACKLIST_PATH = os.path.join(DATA_DIR, "blacklist.json")
PREPARE_SCRIPT_PATH = os.path.join(ROOT_DIR, 'src', 'data', 'prepare_data.py')

print(f"📁 Script dir: {SCRIPT_DIR}")
print(f"📁 Root dir: {ROOT_DIR}")
print(f"📁 Data dir: {DATA_DIR}")

# === FUNCIONES DE RUTA Y UTILIDAD ===
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

# === LÓGICA DE CARGA DE DATOS PARA EL MODELO ===
def load_data():
    if not os.path.exists(FINAL_DATASET_PATH) or os.path.getsize(FINAL_DATASET_PATH) <= 100:
        print("⚠️ Archivo 'final_dataset.csv' no encontrado o es vacío. Generando...")
        try:
            subprocess.run([sys.executable, PREPARE_SCRIPT_PATH], check=True)
        except subprocess.CalledProcessError as e:
            print(f"❌ Error al ejecutar prepare_data.py: {e}")
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
    print(f"✅ TF-IDF completado: {tfidf_matrix.shape}")
    n_components = min(tfidf_matrix.shape) - 1
    if n_components <= 0: return None
    n_svd = min(200, n_components) 
    svd = TruncatedSVD(n_components=n_svd, random_state=42)
    latent_matrix = svd.fit_transform(tfidf_matrix)
    print(f"✅ SVD aplicado: {latent_matrix.shape}")
    cosine_sim = linear_kernel(latent_matrix, latent_matrix)
    print(f"✅ Similitud coseno calculada: {cosine_sim.shape}")
    return cosine_sim

def get_recommendations(df, cosine_sim, threshold=8, top_n=10):
    score_vector = df['user_score'].values / 10 
    total_scores = np.dot(cosine_sim, score_vector)
    recs = df.copy()
    recs['hybrid_score'] = total_scores
    vistos_ids = recs[recs['my_status'] != 'NO_INTERACTUADO']['AniListID'].tolist()
    blacklist_ids = set(load_blacklist())
    ids_a_excluir = set(vistos_ids).union(blacklist_ids)
    recs = recs[~recs['AniListID'].isin(ids_a_excluir)].copy()
    
    print(f"✅ Filtrado completado. Se excluyeron {len(ids_a_excluir)} animes.")
    
    if recs.empty:
        print("⚠️ No hay recomendaciones disponibles.")
        return pd.DataFrame() 
        
    recs = recs[recs['score'] >= 80]
    recs = recs.sort_values(by='hybrid_score', ascending=False)
    return recs.head(top_n)

# === FUNCIONES PARA ESTADÍSTICAS ===
def load_user_ratings_only():
    """Carga solo los ratings del usuario para estadísticas"""
    if not os.path.exists(USER_RATINGS_PATH) or os.path.getsize(USER_RATINGS_PATH) <= 100:
        return pd.DataFrame()

    try:
        df_user = pd.read_csv(USER_RATINGS_PATH)
        df_user['my_score'] = df_user['my_score'].fillna(0)
        df_user = df_user.rename(columns={'anime_id': 'AniListID', 'my_score': 'user_score'})
        return df_user
    except Exception as e:
        print(f"❌ Error al cargar user_ratings.csv: {e}")
        return pd.DataFrame()

def get_user_favorites(df_user_list, threshold=8):
    """Obtiene los géneros y tags de los animes favoritos"""
    df_favorites = df_user_list[(df_user_list['user_score'] >= threshold) & (df_user_list['user_score'] > 0)].copy()
    
    all_genres = Counter()
    all_tags = Counter()

    for genres_str in df_favorites['genres']:
        if isinstance(genres_str, str) and genres_str:
            all_genres.update(genres_str.split())

    for tags_str in df_favorites['tags']:
        if isinstance(tags_str, str) and tags_str:
            all_tags.update(tags_str.split())

    return all_genres, all_tags

def generate_statistics():
    """Genera estadísticas del usuario para incluir en el JSON"""
    try:
        # Cargar datos necesarios para estadísticas
        df = load_data()
        df_ratings = load_user_ratings_only()
        
        if df_ratings.empty:
            return {
                'total_animes_catalog': len(df),
                'total_user_animes': 0,
                'error': 'No se pudieron cargar los ratings del usuario'
            }
        
        # Fusionar para análisis
        df_user_list = df_ratings.merge(
            df[['AniListID', 'genres', 'tags']].drop_duplicates(subset=['AniListID']),
            on='AniListID', 
            how='left' 
        )
        
        # Calcular estadísticas
        total_rated = len(df_user_list[df_user_list['user_score'] > 0])
        favoritos_count = len(df_user_list[df_user_list['user_score'] >= 8])
        
        # Top géneros y tags
        top_genres, top_tags = get_user_favorites(df_user_list, threshold=8)
        
        # Conteo de estados
        status_counts = df_ratings['my_status'].value_counts(dropna=False).to_dict()
        
        # Construir objeto de estadísticas
        stats = {
            'total_animes_catalog': len(df),
            'total_user_animes': len(df_ratings),
            'total_rated': total_rated,
            'favorites_count': favoritos_count,
            'top_genres': [{'name': g[0], 'count': g[1]} for g in top_genres.most_common(5)],
            'top_tags': [{'name': t[0], 'count': t[1]} for t in top_tags.most_common(5)],
            'status_distribution': status_counts,
            'completion_rate': f"{(total_rated / len(df_ratings) * 100):.1f}%" if len(df_ratings) > 0 else "0%"
        }
        
        print("📊 Estadísticas generadas exitosamente")
        return stats
        
    except Exception as e:
        print(f"❌ Error generando estadísticas: {e}")
        return {
            'total_animes_catalog': 0,
            'total_user_animes': 0,
            'error': str(e)
        }

# === FUNCIÓN PARA GUARDAR JSON CON ESTADÍSTICAS ===
def save_recommendations_to_json(recommendations_df, filename="recommendations.json"):
    """Guarda las recomendaciones Y estadísticas en formato JSON para Flutter"""
    recommendations_json = []
    for _, row in recommendations_df.iterrows():
        recommendations_json.append({
            'id': int(row['AniListID']),
            'title': row['title'],
            'score': float(row['score']),
            'type': row.get('Tipo', 'N/A'),
            'genres': row['genres'].split() if isinstance(row['genres'], str) else [],
            'tags': row['tags'].split() if isinstance(row['tags'], str) else [],
            'description': row.get('description', ''),
            'hybrid_score': float(row.get('hybrid_score', 0))
        })
    
    # Generar estadísticas
    stats = generate_statistics()
    
    # Guardar TODO en el JSON
    output_path = os.path.join(DATA_DIR, filename)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'count': len(recommendations_json),
            'statistics': stats,  # ✅ INCLUIR ESTADÍSTICAS
            'recommendations': recommendations_json
        }, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Recomendaciones Y estadísticas guardadas en: {output_path}")
    return output_path

# === FUNCIÓN PRINCIPAL MODIFICADA ===
def main_with_json():
    """Versión que guarda resultados en JSON para Flutter"""
    try:
        print("🚀 Iniciando generación de recomendaciones...")
        
        df = load_data() 
        print(f"✅ Dataset cargado: {len(df)} filas.")
        
        print("\n🔧 Entrenando modelo...")
        sim = preprocess_data(df)
        
        if sim is None:
            print("❌ No se pudo entrenar el modelo")
            return None

        recs = get_recommendations(df, sim)
        
        if recs.empty:
            print("❌ No se generaron recomendaciones")
            return None
            
        output_file = save_recommendations_to_json(recs)
        
        print(f"🎯 {len(recs)} recomendaciones generadas exitosamente")
        return output_file
        
    except Exception as e:
        print(f"❌ Error en main_with_json: {e}")
        return None

# === FUNCIÓN DE ESTADÍSTICAS ===
def get_anime_statistics(df):
    """
    Calcula estadísticas simples a partir del DataFrame fusionado.
    """
    stats = {}
    
    # Asegurarse de que el DataFrame no esté vacío
    if df.empty:
        return stats
        
    # 1. Género más popular/visto (entre los animes con rating)
    rated_anime = df[df['user_score'].notna()]
    if not rated_anime.empty and 'genres' in rated_anime.columns:
        genre_counter = Counter()
        # Iterar sobre las listas de géneros (ya convertidas a listas por prepare_data.py)
        rated_anime['genres'].apply(lambda x: genre_counter.update(x))
        most_watched_genre = genre_counter.most_common(1)
        stats['most_watched_genre'] = most_watched_genre[0][0] if most_watched_genre else 'N/A'

    # 2. Puntuación promedio del usuario (solo animes calificados)
    if 'user_score' in df.columns:
        avg_score = rated_anime['user_score'].mean()
        stats['average_user_score'] = round(avg_score, 2) if pd.notna(avg_score) else 0.0

    # 3. Total de animes en la lista del usuario (vistos/plan to watch)
    if 'my_status' in df.columns:
        total_in_list = df['my_status'].count()
        stats['total_anime_in_list'] = int(total_in_list)

    return stats

if __name__ == "__main__":
    main_with_json()