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

# Detectar raíz del proyecto
# Aseguramos la ruta del directorio de datos
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(ROOT_DIR, "data")
FINAL_DATASET_PATH = os.path.join(DATA_DIR, "final_dataset.csv")
USER_RATINGS_PATH = os.path.join(DATA_DIR, "user_ratings.csv") 
BLACKLIST_PATH = os.path.join(DATA_DIR, "blacklist.json")
PREPARE_SCRIPT_PATH = os.path.join(ROOT_DIR, 'src', 'data', 'prepare_data.py')

# === FUNCIONES DE RUTA Y UTILIDAD ===
def get_project_root():
    """Devuelve la ruta raíz del proyecto."""
    return ROOT_DIR

def load_blacklist():
    """Carga la lista de IDs de anime a excluir."""
    if not os.path.exists(BLACKLIST_PATH):
        return []
    try:
        with open(BLACKLIST_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Asegura que los IDs sean enteros para el filtro isin
            return [int(id) for id in data if str(id).isdigit()]
    except Exception:
        # Si el archivo está corrupto o vacío, devuelve una lista vacía
        return []

def save_blacklist(new_ids):
    """Añade IDs a la lista de exclusión y guarda el archivo."""
    existing_ids = load_blacklist()
    
    # Asegurarse de que los nuevos IDs sean números únicos
    current_set = set(existing_ids)
    new_ids = [int(i) for i in new_ids if int(i) not in current_set]
    
    if not new_ids:
        print("⚠️ Los IDs proporcionados ya estaban en la Blacklist o son inválidos.")
        return False
        
    updated_ids = existing_ids + new_ids
    
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(BLACKLIST_PATH, 'w', encoding='utf-8') as f:
            json.dump(updated_ids, f, indent=4)
        print(f"✅ Blacklist actualizada. Añadidos: {new_ids}. Total: {len(updated_ids)} IDs.")
        return True
    except Exception as e:
        print(f"❌ Error al guardar la Blacklist: {e}")
        return False

# === LÓGICA DE CARGA DE DATOS PARA EL MODELO ===
def load_data():
    """
    Carga el dataset final para el modelo, asegurando que exista, 
    y aplica limpieza crítica de NaN.
    """
    if not os.path.exists(FINAL_DATASET_PATH) or os.path.getsize(FINAL_DATASET_PATH) <= 100:
        print("⚠️ Archivo 'final_dataset.csv' no encontrado o es vacío. Generando...")
        try:
            subprocess.run([sys.executable, PREPARE_SCRIPT_PATH], check=True)
        except subprocess.CalledProcessError as e:
            print(f"❌ Error al ejecutar prepare_data.py: {e}")
            sys.exit(1)

    # 1. Cargar datos
    df = pd.read_csv(FINAL_DATASET_PATH)
    
    # CRÍTICO: Rellena los NaN dejados por el LEFT JOIN en prepare_data
    df['user_score'] = df['user_score'].fillna(0.0)
    df['my_status'] = df['my_status'].fillna('NO_INTERACTUADO')
    df['my_status'] = df['my_status'].replace('', 'NO_INTERACTUADO') 

    # 2. Conversión de listas (genres y tags)
    for col in ['genres', 'tags']:
        df[col] = df[col].apply(lambda x: ast.literal_eval(x) if pd.notna(x) and isinstance(x, str) and '[' in x else [])
        df[col] = df[col].apply(lambda x: ' '.join([str(i).replace(" ", "") for i in x]))

    # 3. Columna de Features combinados para TF-IDF
    df['combined_features'] = df.apply(
        lambda row: f"{row['title']} {row['genres']} {row['tags']} {row['description']}", 
        axis=1
    )
    
    # 4. Limpieza final y renombre 
    df = df.rename(columns={'type': 'Tipo'})
    df['AniListID'] = df['id'] # Mantener ambos por seguridad

    return df

# === FUNCIÓN PARA CARGA DE DATOS SÓLO PARA ESTADÍSTICAS ===
def load_user_ratings_only():
    """Carga solo los ratings del usuario para estadísticas, sin el merge completo."""
    if not os.path.exists(USER_RATINGS_PATH) or os.path.getsize(USER_RATINGS_PATH) <= 100:
        # Si falta el archivo de ratings, forzamos su generación
        print("⚠️ Archivo 'user_ratings.csv' no encontrado o es vacío. Ejecutando parse_xml.py...")
        try:
            PARSE_SCRIPT_PATH = os.path.join(ROOT_DIR, 'src', 'data', 'parse_xml.py')
            subprocess.run([sys.executable, PARSE_SCRIPT_PATH], check=True)
        except subprocess.CalledProcessError as e:
            print(f"❌ Error al ejecutar parse_xml.py para estadísticas: {e}")
            return pd.DataFrame()

    try:
        # Cargar los datos puros del usuario
        df_user = pd.read_csv(USER_RATINGS_PATH)
        df_user['my_score'] = df_user['my_score'].fillna(0) # Limpieza simple
        df_user = df_user.rename(columns={'anime_id': 'AniListID', 'my_score': 'user_score'})
        return df_user
    except Exception as e:
        print(f"❌ Error al cargar user_ratings.csv para estadísticas: {e}")
        return pd.DataFrame()

# === FUNCIONES DE ANÁLISIS (ESTADÍSTICAS) ===
def get_user_favorites(df_user_list, threshold=8):
    """Obtiene los géneros y tags de los animes favoritos."""
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

def analyze_data(df_model):
    """Muestra estadísticas clave usando los ratings puros del usuario fusionados con el catálogo."""
    print("\n--- 🧠 MOTOR DE RECOMENDACIÓN INICIADO ---")
    
    # 1. Cargar la lista PURA del usuario
    df_ratings = load_user_ratings_only()

    if df_ratings.empty:
        print("❌ No se pudieron cargar los ratings del usuario para las estadísticas.")
        return

    # 2. Total de animes en la base de datos completa (Catálogo)
    total_db_animes = len(df_model)
    
    # 3. Fusionar los ratings puros con el catálogo completo (df_model)
    df_user_list = df_ratings.merge(
        df_model[['AniListID', 'genres', 'tags', 'my_status']].drop_duplicates(subset=['AniListID']),
        on='AniListID', 
        how='left' 
    )
    
    print("\n--- 📊 ANÁLISIS DE SU LISTA PERSONAL ---")
    print(f"| Total de animes en el catálogo: {total_db_animes}")
    
    # Usar el total del archivo de ratings para la cuenta de la lista de usuario
    total_list_animes = len(df_ratings) 
    print(f"| Total de animes en su lista: {total_list_animes}") 
    
    # Animes puntuados (score > 0)
    total_rated = len(df_user_list[df_user_list['user_score'] > 0])
    
    # Animes favoritos (Score >= 8)
    favoritos_count = len(df_user_list[df_user_list['user_score'] >= 8])
    print(f"| Animes Favoritos (Score >= 8): {favoritos_count} de {total_rated} calificados.")
    
    # Top Géneros y Temas
    top_genres, top_tags = get_user_favorites(df_user_list, threshold=8)
    
    genres_str = ', '.join([f'{g[0]} ({g[1]})' for g in top_genres.most_common(5)]) if top_genres else 'N/A'
    tags_str = ', '.join([f'{t[0]} ({t[1]})' for t in top_tags.most_common(5)]) if top_tags else 'N/A'

    print(f"| Top 5 Géneros Favoritos: {genres_str}")
    print(f"| Top 5 Temas Favoritos: {tags_str}")
    
    print("\n| ESTADO DE VISUALIZACIÓN:")
    # Conteo de Status (usando el status de la lista de usuario)
    status_counts = df_ratings['my_status'].value_counts(dropna=False)
    
    # Mostrar los conteos (solo Completed está en el output, los demás están a 0)
    estados = ['Completed', 'Dropped', 'Plan to Watch', 'On-Hold', 'Watching']
    for status in estados:
        count = status_counts.get(status, 0)
        print(f"| - {status}: {count}")

    print("---------------------------------------")

# === EL RESTO DE FUNCIONES (ENTRENAMIENTO, RECOMENDACIÓN Y DISPLAY) ===

def preprocess_data(df):
    """Aplica TF-IDF y Truncated SVD para crear la matriz de similitud coseno."""
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
    """Genera recomendaciones de anime basadas en similitud de contenido."""
    score_vector = df['user_score'].values / 10 
    total_scores = np.dot(cosine_sim, score_vector)
    recs = df.copy()
    recs['hybrid_score'] = total_scores
    vistos_ids = recs[recs['my_status'] != 'NO_INTERACTUADO']['AniListID'].tolist()
    blacklist_ids = set(load_blacklist())
    ids_a_excluir = set(vistos_ids).union(blacklist_ids)
    recs = recs[~recs['AniListID'].isin(ids_a_excluir)].copy()
    
    print(f"✅ Filtrado completado. Se excluyeron {len(ids_a_excluir)} animes (Vistos/Puntuados/Blacklist).")
    
    if recs.empty:
        print("⚠️ No hay recomendaciones disponibles después de aplicar el filtro. Intente añadir más animes a su lista.")
        return pd.DataFrame() 
        
    recs = recs[recs['score'] >= 80]
    recs = recs.sort_values(by='hybrid_score', ascending=False)
    return recs.head(top_n)

def format_score(score):
    """Formatea la puntuación de 1-100 a un solo decimal."""
    if pd.isna(score): return 'N/A'
    return f"{score / 10:.1f}"

def display_recommendations(df_recs):
    """Muestra las recomendaciones en un formato legible."""
    if df_recs.empty: return
    
    # Las columnas seleccionadas garantizan que no haya KeyErrors.
    top_10 = df_recs[['AniListID', 'title', 'genres', 'tags', 'score', 'Tipo', 'hybrid_score']].copy()
    
    top_10.rename(columns={'AniListID': 'ID', 'score': 'Puntuación AniList', 'hybrid_score': 'Puntuación Híbrida', 'Tipo': 'Tipo',}, inplace=True)
    
    # Limitar géneros y tags mostrados para que no rompa el formato de tabla
    top_10['genres'] = top_10['genres'].apply(lambda x: ', '.join(x.split()[:3]) if isinstance(x, str) else x)
    top_10['tags'] = top_10['tags'].apply(lambda x: ', '.join(x.split()[:3]) if isinstance(x, str) else x)
    
    top_10['Puntuación Híbrida'] = top_10['Puntuación Híbrida'].round(4)
    top_10['Puntuación AniList'] = top_10['Puntuación AniList'].apply(format_score)
    if 'Tipo' in top_10.columns:
        top_10['Tipo'] = top_10['Tipo'].apply(lambda x: 'ANIME' if pd.notna(x) and x else 'N/A')
        
    # Seleccionar y reordenar columnas para la tabla
    final_cols = ['ID', 'title', 'Puntuación AniList', 'Tipo', 'genres', 'tags']
    top_10_display = top_10[final_cols]
    
    print("\n--- ✅ RECOMENDACIONES DE ANIME (Content-Based) ---")
    print(top_10_display.to_markdown(index=False))
    print("----------------------------------------------------")

# === FUNCIÓN PRINCIPAL ===
def main():
    
    # Cargar el dataset grande para el modelo
    df = load_data() 
    print(f"✅ Dataset final cargado: {len(df)} filas.")
    
    # Analizar datos usando los ratings puros
    analyze_data(df) 
    
    # Entrenar modelo
    print("\n| Iniciando cálculo de modelo. Esto puede tardar varios segundos...")
    sim = preprocess_data(df)
    
    if sim is None:
        print("❌ No se pudo entrenar el modelo (posiblemente datos insuficientes).")
        return

    # Obtener recomendaciones
    recs = get_recommendations(df, sim)
    
    # Mostrar resultados
    display_recommendations(recs)

    # === INTERACCIÓN DE BLACKLIST ===
    while True:
        user_input = input("\n¿Desea añadir ID(s) a la Blacklist? (AniList IDs separados por coma, ej: 123,456. O 'no' para salir): ").strip()
        if user_input.lower() == 'no':
            break
        
        try:
            new_ids = [int(i.strip()) for i in user_input.split(',') if i.strip().isdigit()]
            
            if new_ids:
                if save_blacklist(new_ids):
                    # Recargar, reanalizar y reentrenar después de la Blacklist
                    df = load_data()
                    print(f"✅ Dataset final recargado: {len(df)} filas.")
                    analyze_data(df)
                    print("\n| Recalculando modelo tras Blacklist...")
                    sim = preprocess_data(df)
                    recs = get_recommendations(df, sim)
                    display_recommendations(recs)
        except Exception as e:
            print(f"❌ Entrada inválida: {e}")

if __name__ == "__main__":
    main()