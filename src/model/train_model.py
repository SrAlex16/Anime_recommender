# src/model/train_model.py - VERSIÓN COMPLETA CON TODAS LAS FUNCIONES
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
import traceback
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
    """Función de logging para debug - FORZAR FLUSH"""
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

def get_user_anime_ids_from_source():
    """Obtiene los IDs de anime directamente del JSON original del usuario"""
    try:
        user_json_path = os.path.join(DATA_DIR, "user_mal_list.json")
        
        if not os.path.exists(user_json_path):
            debug_log("❌ user_mal_list.json no encontrado")
            return set()
        
        with open(user_json_path, 'r', encoding='utf-8') as f:
            user_data = json.load(f)
        
        # Extraer todos los anime_id del JSON
        user_anime_ids = set()
        for item in user_data:
            anime_id = item.get('anime_id')
            if anime_id is not None:
                user_anime_ids.add(int(anime_id))
        
        debug_log(f"📊 user_mal_list.json contiene {len(user_anime_ids)} animes únicos")
        
        # 🔥 DEBUG: Mostrar algunos ejemplos del JSON
        debug_log("🔍 Ejemplos del JSON original:")
        for i, item in enumerate(user_data[:3]):
            debug_log(f"   📝 Anime {i+1}: ID={item.get('anime_id')}, Title='{item.get('anime_title')}', Status={item.get('status')}")
        
        return user_anime_ids
        
    except Exception as e:
        debug_log(f"❌ Error leyendo user_mal_list.json: {e}")
        return set()

def debug_user_animes(df):
    """Debug: Ver qué animes tiene el usuario desde la fuente directa"""
    user_anime_ids = get_user_anime_ids_from_source()
    
    debug_log(f"📊 USER ANIME LIST DEBUG (desde JSON):")
    debug_log(f"Total animes en lista: {len(user_anime_ids)}")
    
    # Mostrar algunos ejemplos con títulos
    debug_log("🔍 Ejemplos de animes en lista del usuario:")
    sample_ids = list(user_anime_ids)[:8]
    for anime_id in sample_ids:
        anime_info = df[df['id'] == anime_id]
        if not anime_info.empty:
            title = anime_info.iloc[0]['title']
            status = anime_info.iloc[0]['my_status'] if 'my_status' in anime_info.columns else 'Unknown'
            debug_log(f"   📺 {title} (ID: {anime_id}) - Estado: {status}")
        else:
            debug_log(f"   ❓ Anime ID {anime_id} no encontrado en dataset")
    
    return user_anime_ids

def load_data():
    if not os.path.exists(FINAL_DATASET_PATH) or os.path.getsize(FINAL_DATASET_PATH) <= 100:
        debug_log("⚠️ Archivo 'final_dataset.csv' no encontrado. Generando...")
        try:
            subprocess.run([sys.executable, PREPARE_SCRIPT_PATH], check=True)
        except subprocess.CalledProcessError as e:
            debug_log(f"❌ Error al ejecutar prepare_data.py: {e}")
            sys.exit(1)

    df = pd.read_csv(FINAL_DATASET_PATH)
    
    # Limpieza y preparación de datos
    df['user_score'] = df['user_score'].fillna(0.0)
    df['my_status'] = df['my_status'].fillna('NO_INTERACTUADO')
    df['my_status'] = df['my_status'].replace('', 'NO_INTERACTUADO') 

    # Procesar listas de géneros y tags
    for col in ['genres', 'tags']:
        df[col] = df[col].apply(lambda x: ast.literal_eval(x) if pd.notna(x) and isinstance(x, str) and '[' in x else [])
        df[col] = df[col].apply(lambda x: ' '.join([str(i).replace(" ", "") for i in x]))

    # Combinar características para TF-IDF
    df['combined_features'] = df.apply(
        lambda row: f"{row['title']} {row['genres']} {row['tags']} {row['description']}", 
        axis=1
    )
    
    df = df.rename(columns={'type': 'Tipo'})
    df['AniListID'] = df['id']

    debug_log(f"✅ Dataset cargado: {len(df)} filas, columnas: {list(df.columns)}")
    return df

def preprocess_data(df):
    """Preprocesa los datos y calcula la matriz de similitud"""
    try:
        debug_log("Iniciando preprocesamiento TF-IDF y SVD...")
        
        tfidf = TfidfVectorizer(stop_words='english', max_features=10000)
        df['combined_features'] = df['combined_features'].fillna('')
        tfidf_matrix = tfidf.fit_transform(df['combined_features'])
        
        debug_log(f"✅ TF-IDF completado: {tfidf_matrix.shape}")
        
        # Aplicar SVD para reducción de dimensionalidad
        n_components = min(tfidf_matrix.shape) - 1
        if n_components <= 0:
            debug_log("❌ No hay suficientes componentes para SVD")
            return None
            
        n_svd = min(100, n_components)  # Reducir para mayor estabilidad
        svd = TruncatedSVD(n_components=n_svd, random_state=42)
        latent_matrix = svd.fit_transform(tfidf_matrix)
        
        debug_log(f"✅ SVD aplicado: {latent_matrix.shape}")
        
        # Calcular similitud coseno
        cosine_sim = linear_kernel(latent_matrix, latent_matrix)
        debug_log(f"✅ Similitud coseno calculada: {cosine_sim.shape}")
        
        return cosine_sim
        
    except Exception as e:
        debug_log(f"❌ Error en preprocess_data: {e}")
        debug_log(f"❌ Traceback: {traceback.format_exc()}")
        return None

def get_recommendations(df, cosine_sim, top_n=10):
    """Función CORREGIDA: recomienda animes excluyendo los que el usuario ya vio (por MAL_ID)"""
    try:
        debug_log("🎯 Calculando recomendaciones...")

        # 🔥 Obtener IDs del usuario directamente del JSON
        user_anime_ids_from_json = get_user_anime_ids_from_source()
        if not user_anime_ids_from_json:
            debug_log("❌ No se pudieron obtener IDs del usuario desde el JSON")
            return pd.DataFrame()

        debug_log(f"🛑 Excluyendo {len(user_anime_ids_from_json)} animes del usuario (por MAL_ID)")

        # 🔥 Asegurar que la columna MAL_ID sea int
        df['MAL_ID'] = df['MAL_ID'].fillna(0).astype(int)

        # Calcular scores híbridos
        score_vector = df['user_score'].values.astype(float) / 10.0

        # Ajustar dimensiones si es necesario
        if score_vector.shape[0] != cosine_sim.shape[1]:
            debug_log(f"⚠️ Ajustando dimensiones: score_vector {score_vector.shape} vs cosine_sim {cosine_sim.shape}")
            min_dim = min(score_vector.shape[0], cosine_sim.shape[1])
            score_vector = score_vector[:min_dim]
            cosine_sim = cosine_sim[:min_dim, :min_dim]

        # Calcular puntuaciones híbridas
        total_scores = np.dot(cosine_sim, score_vector)
        recs = df.copy()
        recs['hybrid_score'] = total_scores

        # 🔥 FILTRADO: excluir animes ya vistos (MAL_ID)
        recs = recs[~recs['MAL_ID'].isin(user_anime_ids_from_json)].copy()
        debug_log(f"✅ Filtrado completado. Animes disponibles: {len(recs)}")

        if recs.empty:
            debug_log("⚠️ No hay recomendaciones disponibles después del filtrado.")
            return pd.DataFrame()

        # Filtrar por score mínimo de MAL
        recs = recs[recs['score'] >= 70]
        if recs.empty:
            debug_log("⚠️ No hay animes con score >= 70")
            return pd.DataFrame()

        # Ordenar por score híbrido y tomar top N
        recs = recs.sort_values(by='hybrid_score', ascending=False).head(top_n)

        # 🔥 VERIFICACIÓN FINAL: asegurar que no se recomienden animes del usuario
        conflicts = recs[recs['MAL_ID'].isin(user_anime_ids_from_json)]
        if not conflicts.empty:
            debug_log(f"❌ ERROR CRÍTICO: {len(conflicts)} animes del usuario fueron recomendados")
            for _, row in conflicts.iterrows():
                debug_log(f"   🚫 CONFLICTO: {row['title']} (MAL_ID: {row['MAL_ID']})")
            return pd.DataFrame()

        debug_log(f"✅ {len(recs)} recomendaciones generadas exitosamente")
        debug_log("🎯 RECOMENDACIONES FINALES:")
        for _, anime in recs.iterrows():
            debug_log(f"   ✅ {anime['title']} (MAL_ID: {anime['MAL_ID']}) - Score: {anime['score']}")

        return recs

    except Exception as e:
        debug_log(f"❌ Error en get_recommendations: {e}")
        debug_log(f"❌ Traceback: {traceback.format_exc()}")
        return pd.DataFrame()

def get_anime_statistics(df):
    """Calcula estadísticas del usuario"""
    stats = {}
    
    if df.empty:
        return stats
        
    try:
        # Asegurar tipos de datos
        df['user_score'] = pd.to_numeric(df['user_score'], errors='coerce').fillna(0)
        
        # Género más popular entre animes calificados
        rated_anime = df[df['user_score'].notna() & (df['user_score'] > 0)]
        if not rated_anime.empty and 'genres' in rated_anime.columns:
            genre_counter = Counter()
            # Procesar géneros
            for genres in rated_anime['genres']:
                if isinstance(genres, str):
                    genre_list = genres.split()
                    genre_counter.update(genre_list)
            
            most_watched_genre = genre_counter.most_common(1)
            stats['most_watched_genre'] = most_watched_genre[0][0] if most_watched_genre else 'N/A'

        # Puntuación promedio del usuario
        if 'user_score' in df.columns:
            avg_score = rated_anime['user_score'].mean()
            stats['average_user_score'] = round(avg_score, 2) if pd.notna(avg_score) else 0.0

        # Total de animes en la lista del usuario
        user_anime_ids = get_user_anime_ids_from_source()
        stats['total_anime_in_list'] = len(user_anime_ids)
            
        debug_log(f"📊 Estadísticas generadas: {stats}")
        
    except Exception as e:
        debug_log(f"❌ Error calculando estadísticas: {e}")
        stats['error'] = str(e)
    
    return stats

def save_recommendations_to_json(recommendations_df, filename="recommendations.json"):
    """Guarda las recomendaciones en formato JSON, usando MAL_ID de forma consistente"""
    try:
        if recommendations_df.empty:
            debug_log("⚠️ No hay recomendaciones para guardar")
            return None

        # 🔥 Validar que MAL_ID exista y sea int
        recommendations_df['MAL_ID'] = recommendations_df['MAL_ID'].fillna(0).astype(int)

        recommendations_json = []

        for _, row in recommendations_df.iterrows():
            clean_rec = {
                'id': int(row['id']) if 'id' in row and pd.notna(row['id']) else 0,
                'MAL_ID': int(row['MAL_ID']) if 'MAL_ID' in row and pd.notna(row['MAL_ID']) else 0,
                'title': str(row['title']) if 'title' in row and pd.notna(row['title']) else 'Unknown',
                'score': float(row['score']) if 'score' in row and pd.notna(row['score']) else 0.0,
                'genres': str(row['genres']) if 'genres' in row and pd.notna(row['genres']) else '',
                'description': str(row['description']) if 'description' in row and pd.notna(row['description']) else '',
                'type': str(row['type']) if 'type' in row and pd.notna(row['type']) else 'Unknown',
                'episodes': int(row['episodes']) if 'episodes' in row and pd.notna(row['episodes']) else 0,
                'siteUrl': str(row['siteUrl']) if 'siteUrl' in row and pd.notna(row['siteUrl']) else '',
                'studios': str(row['studios']) if 'studios' in row and pd.notna(row['studios']) else ''
            }
            recommendations_json.append(clean_rec)

        # Generar estadísticas
        stats = generate_statistics()

        # Guardar JSON final
        output_path = os.path.join(DATA_DIR, filename)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'count': len(recommendations_json),
                'statistics': stats,
                'recommendations': recommendations_json
            }, f, indent=2, ensure_ascii=False)

        debug_log(f"✅ {len(recommendations_json)} recomendaciones guardadas en: {output_path}")

        # 🔥 Verificación final: asegurar que no se guarden animes ya vistos
        user_anime_ids = get_user_anime_ids_from_source()
        conflicts = [rec for rec in recommendations_json if rec['MAL_ID'] in user_anime_ids]
        if conflicts:
            debug_log(f"❌ ALERTA: Se están guardando {len(conflicts)} animes ya vistos: {[c['title'] for c in conflicts]}")
            return None

        return output_path

    except Exception as e:
        debug_log(f"❌ Error guardando recomendaciones: {e}")
        debug_log(f"❌ Traceback: {traceback.format_exc()}")
        return None


def generate_statistics():
    """Genera estadísticas del sistema (función de respaldo)"""
    try:
        df = load_data()
        stats = get_anime_statistics(df)
        
        # Agregar información adicional
        stats['total_animes_catalog'] = len(df)
        stats['catalog_loaded'] = True
        
        debug_log("📊 Estadísticas del sistema generadas")
        return stats
        
    except Exception as e:
        debug_log(f"❌ Error generando estadísticas: {e}")
        return {
            'total_animes_catalog': 0,
            'error': str(e)
        }

def main_with_json():
    """Función principal que guarda resultados en JSON"""
    try:
        debug_log("🚀 Iniciando generación de recomendaciones...")
        
        df = load_data() 
        debug_log(f"✅ Dataset cargado: {len(df)} filas.")
        
        debug_log("🔧 Entrenando modelo...")
        sim = preprocess_data(df)
        
        if sim is None:
            debug_log("❌ No se pudo entrenar el modelo")
            return None

        recs = get_recommendations(df, sim)
        
        if recs.empty:
            debug_log("❌ No se generaron recomendaciones")
            return None
            
        output_file = save_recommendations_to_json(recs)
        
        debug_log(f"🎯 {len(recs)} recomendaciones generadas exitosamente")
        return output_file
        
    except Exception as e:
        debug_log(f"❌ Error en main_with_json: {e}")
        debug_log(f"❌ Traceback: {traceback.format_exc()}")
        return None

if __name__ == "__main__":
    # Para testing local
    result_file = main_with_json()
    if result_file:
        debug_log(f"✅ Proceso completado: {result_file}")
    else:
        debug_log("❌ Proceso falló")
        sys.exit(1)