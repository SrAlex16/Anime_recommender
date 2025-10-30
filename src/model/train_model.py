# src/model/train_model.py - VERSIÓN FINAL Y ROBUSTA
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel
from sklearn.decomposition import TruncatedSVD
import os
import sys
import json
import numpy as np
from collections import Counter
import ast
from datetime import datetime
import traceback
import csv

# Función de log para asegurar que no se corrompa el JSON de salida
def debug_log(message):
    print(f"🔍 [MODEL_DEBUG] {message}", file=sys.stderr, flush=True)

# Configuración de paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR))
DATA_DIR = os.path.join(ROOT_DIR, "data")
FINAL_DATASET_PATH = os.path.join(DATA_DIR, "final_dataset.csv")
USER_RATINGS_PATH = os.path.join(DATA_DIR, "user_ratings.csv") 
BLACKLIST_FILE = os.path.join(DATA_DIR, "runtime_blacklist.json")


# === 1. FUNCIONES AUXILIARES ===

def load_data():
    """Carga el dataset final y aplica limpieza básica."""
    if not os.path.exists(FINAL_DATASET_PATH) or os.path.getsize(FINAL_DATASET_PATH) < 1000:
        raise FileNotFoundError(f"El dataset final no existe o está vacío: {FINAL_DATASET_PATH}")
    
    df = pd.read_csv(FINAL_DATASET_PATH)

    # Convertir las listas guardadas como strings a listas de Python
    for col in ['genres', 'tags', 'studios']:
        if col in df.columns:
            df[col] = df[col].apply(lambda x: ast.literal_eval(x) if pd.notna(x) and isinstance(x, str) and x.startswith('[') else [])

    # Crear el campo de features combinadas
    def combine_features(row):
        features = []
        if 'genres' in row and row['genres']:
            features.extend(row['genres'])
        if 'tags' in row and row['tags']:
            features.extend(row['tags'])
        if 'studios' in row and row['studios']:
            features.extend(row['studios'])
        # Agregar el tipo de anime
        if 'type' in row and pd.notna(row['type']):
             features.append(row['type'])
        
        return ' '.join(features)

    df['combined_features'] = df.apply(combine_features, axis=1)
    
    return df


def get_anime_statistics(df):
    """
    Retorna estadísticas generales del dataset de animes.
    df: DataFrame con la información de animes.
    """
    
    # 1. Animes vistos por el usuario (score > 0)
    watched_count = len(df[df['user_score'] > 0])
    
    # 2. Puntuación promedio del usuario (solo si ha puntuado algo)
    user_avg_score = df[df['user_score'] > 0]['user_score'].mean()
    user_avg_score = round(user_avg_score, 2) if pd.notna(user_avg_score) else None

    # 3. Género más visto
    all_genres = [g for sublist in df[df['user_score'] > 0]['genres'] for g in sublist]
    genre_counts = Counter(all_genres)
    most_common_genre = genre_counts.most_common(1)[0][0] if genre_counts else None
    
    # 4. Studio más visto
    all_studios = [s for sublist in df[df['user_score'] > 0]['studios'] for s in sublist]
    studio_counts = Counter(all_studios)
    most_common_studio = studio_counts.most_common(1)[0][0] if studio_counts else None
    
    # Cargar Blacklist
    blocked_ids = set()
    if os.path.exists(BLACKLIST_FILE):
        try:
            with open(BLACKLIST_FILE, 'r', encoding='utf-8') as f:
                blocked_ids = set(json.load(f))
        except Exception:
            debug_log("Error cargando blacklist para estadísticas.")
            
    blacklist_count = len(blocked_ids)

    stats = {
        "user_watched_count": watched_count,
        "user_avg_score": user_avg_score,
        "most_common_genre": most_common_genre,
        "most_common_studio": most_common_studio,
        "blacklist_count": blacklist_count,
        "total_animes_in_db": len(df),
    }
    return stats

def load_blacklist():
    """Carga la blacklist desde el archivo JSON si existe."""
    blocked_ids = set()
    if os.path.exists(BLACKLIST_FILE):
        try:
            with open(BLACKLIST_FILE, 'r', encoding='utf-8') as f:
                # Asegurarse de que los IDs sean enteros
                blocked_ids = set(map(int, json.load(f)))
        except Exception:
            debug_log("Error cargando blacklist.")
    return blocked_ids


# === 2. LÓGICA DEL MODELO ===

def run_recommendation_engine(df, num_recommendations=20):
    """
    Entrena el modelo de filtrado colaborativo basado en contenido
    y devuelve las mejores recomendaciones para el usuario.
    """
    debug_log("Entrenando TF-IDF y calculando similitud coseno...")

    # Crear la matriz TF-IDF
    tfidf = TfidfVectorizer(stop_words='english')
    # Ajustar a los features combinados
    tfidf_matrix = tfidf.fit_transform(df['combined_features'].fillna(''))

    # Aplicar TruncatedSVD para reducir la dimensionalidad (optimización)
    n_components = min(50, tfidf_matrix.shape[1])
    if n_components > 1:
        svd = TruncatedSVD(n_components=n_components, random_state=42)
        tfidf_matrix_reduced = svd.fit_transform(tfidf_matrix)
        cosine_sim = linear_kernel(tfidf_matrix_reduced, tfidf_matrix_reduced)
    else:
        # Si la matriz es muy pequeña, usar el kernel lineal directamente
        cosine_sim = linear_kernel(tfidf_matrix, tfidf_matrix)

    debug_log(f"Matriz de similitud calculada. Shape: {cosine_sim.shape}")
    
    # Mapeo de títulos a índices del DataFrame
    indices = pd.Series(df.index, index=df['title']).drop_duplicates()

    # 1. Obtener los animes que el usuario ha puntuado (mejor puntuación)
    user_rated_animes = df[df['user_score'] >= 7].sort_values(by='user_score', ascending=False)
    
    # Si el usuario no tiene animes puntuados alto, usar los vistos
    if user_rated_animes.empty:
        debug_log("⚠️ No hay animes con puntuación >= 7. Usando todos los animes vistos/en lista.")
        user_rated_animes = df[df['my_status'] != 'NO_INTERACTUADO'].sort_values(by='user_score', ascending=False)

    if user_rated_animes.empty:
        debug_log("❌ No se encontraron animes para usar como base. Devolviendo los más populares.")
        # Si no hay interacciones, usar un fallback (los 20 más populares con mejor score)
        return df[df['my_status'] == 'NO_INTERACTUADO'].sort_values(by='averageScore', ascending=False).head(num_recommendations)

    # 2. Generar recomendaciones
    sim_scores = {}
    
    # Usar los 5 animes mejor puntuados por el usuario como "semilla"
    seed_animes = user_rated_animes.head(5)

    for idx_seed in seed_animes.index:
        title = df.loc[idx_seed]['title']
        if title not in indices:
            continue
            
        # Obtener el índice de la matriz de similitud
        idx = indices[title]
        # Obtener las puntuaciones de similitud de ese anime con todos los demás
        sim_scores_list = list(enumerate(cosine_sim[idx]))
        # Sumar las puntuaciones de similitud para combinarlas
        for i, score in sim_scores_list:
            sim_scores[i] = sim_scores.get(i, 0) + score

    # Eliminar las entradas de animes ya utilizados como semilla
    for idx_seed in seed_animes.index:
        sim_scores.pop(idx_seed, None)


    # Ordenar los animes por la puntuación de similitud combinada
    sorted_sim_scores = sorted(sim_scores.items(), key=lambda item: item[1], reverse=True)

    # 3. Filtrar y construir la lista final
    recommended_indices = []
    
    # Animes a excluir: ya interactuados por el usuario o en la blacklist
    # Usar 'id' (AniList ID) para la exclusión
    user_interacted_ids = df[df['my_status'] != 'NO_INTERACTUADO']['id'].tolist()
    blocked_ids = load_blacklist()
    
    animes_to_exclude = set(user_interacted_ids) | blocked_ids
    
    debug_log(f"Excluyendo {len(user_interacted_ids)} animes vistos y {len(blocked_ids)} en blacklist.")

    for i, score in sorted_sim_scores:
        anime_id = df.iloc[i]['id']
        if anime_id not in animes_to_exclude:
            recommended_indices.append(i)
        
        if len(recommended_indices) >= num_recommendations:
            break

    # Obtener el DataFrame de las recomendaciones
    recs_df = df.iloc[recommended_indices].copy()

    # Si no se alcanzan las recomendaciones, añadir por popularidad
    if len(recs_df) < num_recommendations:
        debug_log(f"⚠️ Solo se encontraron {len(recs_df)} recomendaciones. Rellenando con los más populares no vistos.")
        
        # Obtener animes no interactuados y no recomendados aún
        not_seen_and_not_recommended = df[
            (~df['id'].isin(animes_to_exclude)) & 
            (~df.index.isin(recs_df.index))
        ]
        
        # Rellenar con los más populares (mejor averageScore)
        filler_recs = not_seen_and_not_recommended.sort_values(by='averageScore', ascending=False).head(num_recommendations - len(recs_df))
        recs_df = pd.concat([recs_df, filler_recs])

    # 4. Post-procesamiento
    recs_df = post_process_recommendations(recs_df)

    return recs_df.head(num_recommendations)

def post_process_recommendations(recs_df):
    """Limpia y selecciona las columnas finales para la API."""
    cols_to_keep = [
        'id', 'title', 'genres', 'tags', 'averageScore', 
        'type', 'episodes', 'siteUrl', 'studios', 'description'
    ]
    # Asegurar que solo se mantienen las columnas existentes
    recs_df = recs_df[[c for c in cols_to_keep if c in recs_df.columns]].rename(columns={'id': 'AniListID'}).copy()
    
    # Limpiar columnas de lista para el JSON (convertir listas vacías a None)
    for col in ['genres', 'tags', 'studios']:
         recs_df[col] = recs_df[col].apply(lambda x: x if x else None)


    return recs_df

def save_recommendations_to_json(recs_df, stats):
    """Guarda el DataFrame de recomendaciones y estadísticas en un archivo JSON temporal y devuelve el JSON."""
    try:
        if recs_df.empty:
             raise Exception("DataFrame de recomendaciones está vacío.")
        
        # Renombrar 'AniListID' a 'id' para la respuesta final del frontend
        recs_df = recs_df.rename(columns={'AniListID': 'id'}) 
        
        recs_json = {
            'status': 'success',
            'timestamp': datetime.now().isoformat(),
            'count': len(recs_df),
            'statistics': stats,
            'recommendations': json.loads(recs_df.to_json(orient='records')), 
        }
        
        # Devolver el objeto directamente, no necesitamos guardar a disco en este flujo
        return json.dumps(recs_json, indent=4, ensure_ascii=False)
        
    except Exception as e:
        debug_log(f"❌ Error al serializar las recomendaciones a JSON: {e}")
        return json.dumps({
            'status': 'error',
            'message': f'Error al serializar recomendaciones: {str(e)}',
            'timestamp': datetime.now().isoformat()
        })


def main_with_json(username):
    """
    Función principal para el pipeline de la API. Carga, entrena y devuelve JSON.
    """
    try:
        debug_log(f"Iniciando entrenamiento para el usuario: {username}")
        
        df = load_data()
        stats = get_anime_statistics(df)
        recs_df = run_recommendation_engine(df)
        
        if recs_df.empty:
            debug_log("❌ No se generaron recomendaciones")
            return json.dumps({
                'status': 'error',
                'message': 'No se generaron recomendaciones para este usuario',
                'timestamp': datetime.now().isoformat()
            })
            
        output_json_str = save_recommendations_to_json(recs_df, stats)
        
        return output_json_str
        
    except Exception as e:
        debug_log(f"❌ Error en main_with_json: {e}")
        debug_log(f"❌ Traceback: {traceback.format_exc()}")
        return json.dumps({
            'status': 'error',
            'message': f'Error fatal del pipeline: {str(e)}',
            'timestamp': datetime.now().isoformat()
        })


if __name__ == "__main__":
    # Bloque de ejecución para pruebas locales
    try:
        if len(sys.argv) > 1:
            TEST_USERNAME = sys.argv[1]
        else:
            TEST_USERNAME = "SrAlex16" # Usuario de prueba por defecto
            
        print(f"Ejecutando train_model.py en modo local para {TEST_USERNAME}")
        
        # Para pruebas locales, primero necesitamos asegurar que los archivos de datos existan
        # Esto requiere haber ejecutado antes:
        # 1. python src/data/download_mal_list.py SrAlex16
        # 2. python src/data/fetch_datasets.py
        # 3. python src/data/prepare_data.py
        
        result_json_str = main_with_json(TEST_USERNAME)
        if result_json_str:
            print("--- RESULTADO DEL MODELO (JSON) ---")
            print(result_json_str)
            print("-----------------------------------")
            
    except Exception as e:
        print(f"Error en la ejecución local: {e}")
        sys.exit(1)