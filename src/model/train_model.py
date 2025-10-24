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
    """Carga la lista de IDs de anime a excluir."""
    if not os.path.exists(BLACKLIST_PATH):
        return []
    try:
        with open(BLACKLIST_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # CRÍTICO: Asegurar que la blacklist es una lista de enteros
            return [int(x) for x in data if str(x).isdigit()] 
    except Exception as e:
        debug_log(f"❌ Error al cargar blacklist: {e}")
        return []

# ✅ NUEVA FUNCIÓN: Agregar IDs a la blacklist y guardar
def add_to_blacklist(new_anime_ids):
    """
    Carga la blacklist, añade los nuevos IDs, y guarda el archivo.
    Retorna la nueva lista de IDs.
    """
    debug_log(f"🔧 Solicitud para añadir a blacklist: {new_anime_ids}")
    try:
        current_blacklist = set(load_blacklist())
        
        # Filtrar solo IDs que son números enteros y no están ya presentes
        new_ids = set()
        for item in new_anime_ids:
            try:
                # Intenta convertir a entero y añadir
                new_ids.add(int(item))
            except (ValueError, TypeError):
                # Ignorar si no es convertible a entero
                debug_log(f"⚠️ ID ignorado (no válido): {item}")
                continue

        # No hay nuevos IDs para añadir
        if not new_ids:
            debug_log("✅ No hay IDs válidos para añadir a la blacklist.")
            return sorted(list(current_blacklist))

        # Añadir los nuevos IDs
        current_blacklist.update(new_ids)
        final_list = sorted(list(current_blacklist))
        
        # Guardar la lista actualizada
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(BLACKLIST_PATH, 'w', encoding='utf-8') as f:
            json.dump(final_list, f, indent=4)

        debug_log(f"✅ Blacklist actualizada. Total: {len(final_list)} IDs.")
        return final_list

    except Exception as e:
        debug_log(f"❌ Error al actualizar la blacklist: {e}")
        raise

def load_data():
    """Carga y limpia el dataset final de anime para el modelo."""
    # ... (Resto de la implementación de load_data)
    if not os.path.exists(FINAL_DATASET_PATH) or os.path.getsize(FINAL_DATASET_PATH) < 1024:
        debug_log(f"❌ Dataset final no encontrado o vacío: {FINAL_DATASET_PATH}")
        # Intentar ejecutar el pipeline de preparación si falla
        try:
            debug_log("Intentando ejecutar pipeline de preparación de datos...")
            subprocess.run([sys.executable, PREPARE_SCRIPT_PATH, "temp_user"], check=True, cwd=ROOT_DIR)
        except subprocess.CalledProcessError as e:
            debug_log(f"❌ Falló la ejecución del pipeline de preparación. Código: {e.returncode}. Output: {e.stderr}")
            return pd.DataFrame() # Retorna DataFrame vacío
        except Exception as e:
            debug_log(f"❌ Falló la ejecución del pipeline de preparación con error: {e}")
            return pd.DataFrame() # Retorna DataFrame vacío

    try:
        df = pd.read_csv(FINAL_DATASET_PATH)
        # Limpieza de datos
        df['tags'] = df['tags'].apply(lambda x: ast.literal_eval(x) if pd.notna(x) else [])
        df['studios'] = df['studios'].apply(lambda x: ast.literal_eval(x) if pd.notna(x) else [])
        df['genres'] = df['genres'].apply(lambda x: ast.literal_eval(x) if pd.notna(x) else [])
        
        # Crear la columna 'content' para TFIDF
        df['content'] = df.apply(
            lambda row: ' '.join(row['genres'] + row['tags'] + row['studios']), axis=1
        )
        
        return df
    except Exception as e:
        debug_log(f"❌ Error al cargar o procesar el dataset final: {e}")
        debug_log(f"❌ Traceback: {traceback.format_exc()}")
        return pd.DataFrame()

def preprocess_data(df):
    """Crea la matriz de similitud de contenido (TF-IDF y SVD)."""
    # ... (Resto de la implementación de preprocess_data)
    if df.empty:
        return None
        
    try:
        # TF-IDF
        tfidf = TfidfVectorizer(stop_words='english')
        tfidf_matrix = tfidf.fit_transform(df['content'])
        
        # SVD para reducir dimensionalidad y hacer más eficiente
        n_components = min(300, tfidf_matrix.shape[1] - 1)
        if n_components <= 0:
            debug_log("⚠️ Matriz de contenido es demasiado pequeña para SVD.")
            return None
            
        svd = TruncatedSVD(n_components=n_components)
        svd_matrix = svd.fit_transform(tfidf_matrix)
        
        # Similitud del Coseno (kernel lineal)
        cosine_sim = linear_kernel(svd_matrix, svd_matrix)
        return cosine_sim
        
    except Exception as e:
        debug_log(f"❌ Error en preprocess_data: {e}")
        debug_log(f"❌ Traceback: {traceback.format_exc()}")
        return None


def get_recommendations(df, sim_matrix, k=10):
    """Genera las recomendaciones basadas en la lista del usuario."""
    # ... (Resto de la implementación de get_recommendations)
    
    # 1. Cargar ratings del usuario y blacklist
    try:
        ratings_df = pd.read_csv(USER_RATINGS_PATH)
    except Exception:
        debug_log("⚠️ No se pudo cargar el archivo user_ratings.csv. Retornando vacío.")
        return pd.DataFrame()

    # 2. Preprocesamiento de Ratings: Solo animes vistos y puntuados > 0
    # Usar 'status' para identificar animes ya vistos/interactuados
    watched_anime = ratings_df[
        (ratings_df['my_status'] != 'NO_INTERACTUADO')
    ].copy()
    
    if watched_anime.empty:
        debug_log("⚠️ Usuario no tiene animes interactuados para generar recomendaciones.")
        return pd.DataFrame()

    # 3. Mapear IDs de MAL a IDs de AniList para la matriz
    df_map = df[['MalID', 'AniListID']].dropna().astype(int)
    watched_anime['MalID'] = watched_anime['anime_id'].astype(int)
    
    # Fusionar para obtener los AniListID y el índice en el DF principal
    watched_anime = pd.merge(watched_anime, df_map, on='MalID', how='inner')
    
    # Fusionar con el índice del dataframe principal (el que creó la matriz de similitud)
    df_indices = pd.Series(df.index, index=df['AniListID']).drop_duplicates()
    watched_anime['index'] = watched_anime['AniListID'].map(df_indices)
    
    watched_anime.dropna(subset=['index'], inplace=True)
    watched_anime['index'] = watched_anime['index'].astype(int)
    
    if watched_anime.empty:
        debug_log("⚠️ Ningún anime visto por el usuario se encuentra en el catálogo.")
        return pd.DataFrame()

    # 4. Cálculo de Similitudes Ponderadas
    all_sims = {}
    
    # Ponderar por puntuación: 
    # Usar una escala simple (score/10) para ponderar la influencia del anime
    watched_anime['weight'] = watched_anime['my_score'] / 10.0 
    
    for index, row in watched_anime.iterrows():
        anime_index = row['index']
        weight = row['weight']

        # Obtener similitudes para este anime
        sim_scores = list(enumerate(sim_matrix[anime_index]))
        
        # Ponderar la similitud por la puntuación/peso del usuario
        for i, score in sim_scores:
            if i != anime_index: # Excluir el propio anime
                weighted_score = score * weight
                all_sims[i] = all_sims.get(i, 0) + weighted_score

    # 5. Filtrar y ordenar
    # Convertir a lista de tuplas (index, score)
    total_sim_scores = sorted(all_sims.items(), key=lambda item: item[1], reverse=True)

    # IDs de anime ya vistos y IDs en la blacklist
    already_seen_ids = set(watched_anime['AniListID'].tolist())
    
    # Aplicar Blacklist
    blacklist_ids = set(load_blacklist())
    
    # Lista para almacenar las recomendaciones finales
    final_recommendations = []
    
    for index, score in total_sim_scores:
        recommended_anime = df.iloc[index].to_dict()
        anime_id = recommended_anime['AniListID']

        if anime_id not in already_seen_ids and anime_id not in blacklist_ids:
            # Añadir la puntuación de similitud
            recommended_anime['similarity_score'] = round(score, 4)
            final_recommendations.append(recommended_anime)
            
        if len(final_recommendations) >= k:
            break
            
    # 6. Devolver como DataFrame
    return pd.DataFrame(final_recommendations)


def save_recommendations_to_json(recs):
    """Guarda las recomendaciones en un archivo JSON en la carpeta data."""
    # ... (Resto de la implementación de save_recommendations_to_json)
    
    # Convertir el DataFrame a una lista de diccionarios
    recs_list = recs.replace({np.nan: None}).to_dict('records')

    # Crear el diccionario de salida
    output_data = {
        'timestamp': datetime.now().isoformat(),
        'count': len(recs_list),
        'recommendations': recs_list,
        'statistics': generate_system_statistics(recs_list), # Añadir estadísticas de las recomendaciones
        'status': 'success',
        'message': f'{len(recs_list)} recomendaciones generadas'
    }

    # Guardar en el archivo temporal
    os.makedirs(DATA_DIR, exist_ok=True)
    output_file_path = os.path.join(DATA_DIR, "recommendations_output.json")
    
    try:
        with open(output_file_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=4)
        return output_file_path
    except Exception as e:
        debug_log(f"❌ Error al guardar JSON: {e}")
        debug_log(f"❌ Traceback: {traceback.format_exc()}")
        # Imprimir el JSON al stderr para que el pipeline lo capture
        return json.dumps({'status': 'error', 'message': f'Error al guardar JSON: {str(e)}', 'timestamp': datetime.now().isoformat()})

def generate_system_statistics(recs_list):
    """Genera estadísticas del sistema y de las recomendaciones."""
    # ... (Resto de la implementación de generate_system_statistics)
    
    stats = {}
    
    # 1. Estadísticas del Catálogo Base
    try:
        df = load_data()
        stats['total_animes_catalog'] = len(df)
        
        # Contar cuántos animes del catálogo tienen una puntuación
        scored_animes = df[df['averageScore'].notna()]
        stats['scored_animes_count'] = len(scored_animes)
        stats['average_catalog_score'] = round(scored_animes['averageScore'].mean(), 2) if len(scored_animes) > 0 else 0
        stats['catalog_loaded'] = True
        
    except Exception as e:
        debug_log(f"❌ Error al cargar stats del catálogo: {e}")
        stats['catalog_loaded'] = False
        stats['catalog_error'] = str(e)
        
    # 2. Estadísticas de las Recomendaciones
    if recs_list:
        scores = [r.get('averageScore') for r in recs_list if r.get('averageScore') is not None]
        stats['avg_recommendation_score'] = round(sum(scores) / len(scores), 2) if scores else 0
        
        genres = [g for r in recs_list for g in r.get('genres', [])]
        genre_counts = Counter(genres).most_common(5)
        stats['top_genres_in_recs'] = [{'genre': g, 'count': c} for g, c in genre_counts]
        
        studios = [s for r in recs_list for s in r.get('studios', [])]
        studio_counts = Counter(studios).most_common(3)
        stats['top_studios_in_recs'] = [{'studio': s, 'count': c} for s, c in studio_counts]
        
    debug_log("📊 Estadísticas del sistema generadas")
    return stats
        
def main_with_json():
    """Función principal que guarda resultados en JSON"""
    # ... (Resto de la implementación de main_with_json)
    
    try:
        debug_log("🚀 Iniciando generación de recomendaciones...")
        
        df = load_data() 
        debug_log(f"✅ Dataset cargado: {len(df)} filas.")
        
        debug_log("🔧 Entrenando modelo...")
        sim = preprocess_data(df)
        
        if sim is None:
            debug_log("❌ No se pudo entrenar el modelo")
            # Devolver JSON de error para que el proceso lo capture
            return json.dumps({
                'status': 'error',
                'message': 'No se pudo entrenar el modelo de similitud',
                'timestamp': datetime.now().isoformat()
            })

        recs = get_recommendations(df, sim)
        
        if recs.empty:
            debug_log("❌ No se generaron recomendaciones")
            return json.dumps({
                'status': 'error',
                'message': 'No se generaron recomendaciones para este usuario',
                'timestamp': datetime.now().isoformat()
            })
            
        output_data = save_recommendations_to_json(recs)
        
        # Si se guardó correctamente, output_data será el path. 
        # Si hubo error al guardar, será un string JSON de error.
        if isinstance(output_data, str) and 'status' in output_data:
            return output_data # Es el JSON de error
        
        # En caso de éxito, leer el JSON guardado y devolver su contenido
        with open(output_data, 'r', encoding='utf-8') as f:
            result_json = json.load(f)
            # Retorna el diccionario completo, el script lo imprime como string JSON
            return json.dumps(result_json, ensure_ascii=False)
        
    except Exception as e:
        debug_log(f"❌ Error en main_with_json: {e}")
        debug_log(f"❌ Traceback: {traceback.format_exc()}")
        return json.dumps({
            'status': 'error',
            'message': f'Error fatal del pipeline: {str(e)}',
            'timestamp': datetime.now().isoformat()
        })


if __name__ == "__main__":
    # Para testing local
    result_json_str = main_with_json()
    if result_json_str:
        # Imprime la salida final para que el proceso padre (si lo hay) la capture
        print(result_json_str, flush=True)
