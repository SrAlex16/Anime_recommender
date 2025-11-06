# src/model/train_model.py - VERSIÓN FINAL Y ROBUSTA (con Blacklist Filter)
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
import re # Necesario para limpiar la descripción en save_recommendations_to_json

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

# ✅ NUEVA FUNCIÓN: Cargar la lista negra (blacklist)
def load_blacklist():
    """Carga la blacklist desde el archivo JSON."""
    if not os.path.exists(BLACKLIST_FILE):
        return set()
    try:
        with open(BLACKLIST_FILE, 'r', encoding='utf-8') as f:
            # El archivo debe contener una lista de IDs (integers)
            data = json.load(f)
            if not isinstance(data, list):
                return set()
            # Convertir a set de enteros para una búsqueda rápida
            return set(data)
    except (FileNotFoundError, json.JSONDecodeError, TypeError):
        debug_log(f"⚠️ Error al leer/decodificar el archivo de blacklist. Retornando set vacío.")
        return set()

def load_data():
    """Carga el dataset final y aplica limpieza básica."""
    if not os.path.exists(FINAL_DATASET_PATH) or os.path.getsize(FINAL_DATASET_PATH) < 1000:
        raise FileNotFoundError(f"El dataset final no existe o está vacío: {FINAL_DATASET_PATH}")
    
    # Cargar el CSV y manejar las columnas de lista (tags, genres)
    df = pd.read_csv(FINAL_DATASET_PATH, 
                     dtype={'id': 'Int64', 'idMal': 'Int64'}, 
                     na_values=['nan'])
    
    # Rellenar nulos en score y limpieza
    df['averageScore'] = df['averageScore'].fillna(df['averageScore'].mean()).astype(int)
    df['description'] = df['description'].fillna('')
    df['romaji'] = df['title_romaji'].fillna(df['title_english']).fillna(df['title_native']).fillna('N/A')
    
    # Convertir cadenas de lista a listas reales
    def safe_literal_eval(val):
        try:
            # Intenta evaluar como lista o diccionario, si falla, devuelve el valor original
            return ast.literal_eval(val)
        except (ValueError, SyntaxError, TypeError):
            # Si no es una cadena JSON/lista válida, devuelve una lista vacía para manejarlo
            return [] if isinstance(val, str) else []

    # Aplicar la conversión segura a las columnas de lista
    for col in ['genres', 'tags']:
        # Solo aplicar si la columna existe y no es ya una lista/iterable
        if col in df.columns:
            # Para la fusión final de texto: combinar tags y géneros
            df[col] = df[col].apply(lambda x: [item['name'] for item in safe_literal_eval(x)] if isinstance(x, str) else [])
    
    # Unir todos los elementos de contenido en una sola cadena para TF-IDF
    df['content_features'] = df.apply(lambda row: ' '.join(row['genres']) + ' ' + ' '.join(row['tags']) + ' ' + (row['description'] if isinstance(row['description'], str) else ''), axis=1)
    
    # Eliminar cualquier fila que haya quedado con características de contenido vacías
    df = df[df['content_features'].str.strip() != '']

    debug_log(f"✅ Datos cargados y listos. Filas: {len(df)}")
    return df

def get_recommendations_and_stats(df, user_ratings_df):
    """
    Genera recomendaciones basadas en los ratings del usuario.
    Retorna (DataFrame de recomendaciones, Dict de estadísticas).
    """
    debug_log("⚙️ Iniciando generación de recomendaciones...")
    
    # 1. Preparar la matriz TF-IDF
    tfidf = TfidfVectorizer(stop_words='english', min_df=5)
    tfidf_matrix = tfidf.fit_transform(df['content_features'])
    
    # Reducción de dimensionalidad (opcional, pero ayuda a manejar ruido y rendimiento)
    n_components = min(500, tfidf_matrix.shape[1] - 1)
    if n_components > 0:
        svd = TruncatedSVD(n_components=n_components, random_state=42)
        tfidf_matrix_reduced = svd.fit_transform(tfidf_matrix)
        cosine_sim = linear_kernel(tfidf_matrix_reduced, tfidf_matrix_reduced)
    else:
        # Fallback si no hay suficientes componentes
        cosine_sim = linear_kernel(tfidf_matrix, tfidf_matrix)

    debug_log(f"✅ Matriz de similitud coseno calculada. Forma: {cosine_sim.shape}")

    # Mapeo de índices a IDs (CRÍTICO)
    indices = pd.Series(df.index, index=df['id']).to_dict()
    
    # Crear un DataFrame para las recomendaciones, inicializándolo con todos los animes
    recs_df = df.copy()
    # Inicializar la columna de puntuación final de recomendación
    recs_df['recs_score'] = 0.0
    
    # Obtener los IDs de los animes que el usuario ha visto/puntuado (no 'NO_INTERACTUADO')
    interacted_animes = user_ratings_df[user_ratings_df['my_status'] != 'NO_INTERACTUADO']
    
    if interacted_animes.empty:
        debug_log("⚠️ Usuario sin interacciones válidas. Retornando los animes mejor puntuados globalmente.")
        # Retorna el top 10 basado en score global (ejemplo)
        top_global = df.sort_values(by='averageScore', ascending=False).head(10)
        return top_global, {'status': 'info', 'message': 'No hay suficientes interacciones para el modelo de contenido.'}

    # 2. Generar puntuación de recomendación
    # Se utiliza el promedio ponderado de la similitud del contenido con los animes puntuados
    
    total_weight = 0
    final_score = np.zeros(len(df))

    # Usar solo los animes que tienen una puntuación > 0 o que están en la lista (evitar 'Dropped', 'Hold' si no tienen score)
    # Filtramos por score > 0 Y que el anime ID exista en el índice del modelo
    user_animes = interacted_animes[
        (interacted_animes['my_score'] > 0) & 
        (interacted_animes['anime_id'].isin(indices.keys()))
    ].copy()
    
    # Mapear el 'anime_id' (MAL ID) a 'id' (AniList ID)
    mal_to_anilist = df.set_index('idMal')['id'].to_dict()
    user_animes['anilist_id'] = user_animes['anime_id'].map(mal_to_anilist)
    
    # Filtrar los que no tienen ID de AniList
    user_animes = user_animes.dropna(subset=['anilist_id'])
    
    if user_animes.empty:
        debug_log("⚠️ Usuario con interacciones pero sin coincidencias en el dataset. Retornando global.")
        top_global = df.sort_values(by='averageScore', ascending=False).head(10)
        return top_global, {'status': 'info', 'message': 'Interacciones del usuario no coinciden con animes del dataset.'}

    
    # 3. Suma de similitudes
    for mal_id, score in zip(user_animes['anime_id'], user_animes['my_score']):
        # Mapear MAL ID a índice del DataFrame
        anilist_id = mal_to_anilist.get(mal_id)
        if anilist_id not in indices:
            continue
            
        idx = indices[anilist_id]
        
        # Ponderación: usar la puntuación del usuario (1-10) como peso
        weight = score / 10.0 
        
        # Añadir la similitud de este anime, ponderada por la puntuación del usuario
        final_score += cosine_sim[idx] * weight
        total_weight += weight

    if total_weight > 0:
        final_score /= total_weight
        recs_df['recs_score'] = final_score
    else:
        # Fallback si por alguna razón total_weight es cero (e.g., todos los scores fueron 0)
        recs_df['recs_score'] = df['averageScore'] / 100.0 # Usar el score global

    # 4. Excluir animes que el usuario ya ha interactuado
    # IDs de animes interactuados (incluyendo 'Completed', 'Dropped', 'Plan to Watch')
    interacted_anilist_ids = user_animes['anilist_id'].tolist()
    recs_df = recs_df[~recs_df['id'].isin(interacted_anilist_ids)]
    
    # 5. Ordenar por puntuación de recomendación
    # Se pide el doble de recomendaciones por si la blacklist necesita rellenar mucho
    recs_count = 10 
    raw_recs = recs_df.sort_values(by=['recs_score', 'averageScore'], ascending=False).head(recs_count * 2) 

    # 6. Preparar estadísticas
    stats = {
        'total_animes_scored': len(user_animes),
        'total_animes_in_dataset': len(df),
        'model_type': 'Content-Based Filtering (TFIDF + SVD)',
        'top_genres_scored': Counter(g for row in user_animes['genres'].tolist() for g in row).most_common(5)
    }

    return raw_recs, stats


def save_recommendations_to_json(recs_df, stats):
    """
    Convierte el DataFrame de recomendaciones y estadísticas a una cadena JSON.
    """
    # Función de limpieza (adaptada de tus snippets anteriores)
    def clean_description(desc):
        # Limpia las etiquetas HTML y los saltos de línea
        desc = re.sub(r'<[^>]+>', '', desc)
        desc = desc.replace('\n', ' ').strip()
        # Asegura que no sea más larga de 300 caracteres
        return desc[:300] + '...' if len(desc) > 300 else desc

    recommendations_list = []
    for _, row in recs_df.iterrows():
        # Formato de salida requerido por el frontend
        recommendations_list.append({
            'id': row['id'], # AniList ID
            'idMal': row['idMal'], # MAL ID
            'title': row['title_romaji'] or row['title_english'] or row['title_native'] or 'N/A',
            'description': clean_description(row['description']),
            'score': int(row['averageScore']),
            'episodes': int(row['episodes']) if pd.notna(row['episodes']) else 'N/A',
            'genres': row['genres'],
            'tags': row['tags'],
            'siteUrl': row['siteUrl'],
            'type': row['type'],
            'recs_score': round(row['recs_score'], 4) # Puntuación del modelo
        })

    # Construir el objeto JSON final
    output_data = {
        'status': 'success',
        'count': len(recommendations_list),
        'recommendations': recommendations_list,
        'statistics': stats,
        'timestamp': datetime.now().isoformat()
    }
    
    return json.dumps(output_data, ensure_ascii=False)


# === FUNCIÓN PRINCIPAL ORQUESTADORA ===
def main_with_json(username):
    """
    Función principal que ejecuta todo el pipeline y devuelve un JSON string.
    """
    try:
        debug_log(f"🎬 Iniciando pipeline para el usuario: {username}")
        
        # 1. Cargar datos del modelo (dataset base y ratings del usuario)
        df = load_data() # Dataset base (merged_anime.csv)
        user_ratings_df = pd.read_csv(USER_RATINGS_PATH) # Ratings del usuario (user_ratings.csv)
        
        # 2. Generar lista inicial de recomendaciones (el doble de lo necesario)
        raw_recs_df, stats = get_recommendations_and_stats(df, user_ratings_df)
        
        # =======================================================
        # 3. CRÍTICO: FILTRAR Y REEMPLAZAR ANTES DE GUARDAR
        # =======================================================
        
        # 3a. Cargar la blacklist
        blocked_ids = load_blacklist()
        debug_log(f"⚫ Animes en Blacklist: {len(blocked_ids)}")
        
        if blocked_ids:
            
            # 3b. Filtrar animes bloqueados de la lista de recomendaciones
            recs_df_filtered = raw_recs_df[~raw_recs_df['id'].isin(blocked_ids)].copy()
            
            # El número de recomendaciones finales que queremos es 10
            final_recs_count = 10 
            
            # 3c. Determinar cuántos animes faltan (máximo 10)
            missing_count = final_recs_count - len(recs_df_filtered)
            
            if missing_count > 0:
                debug_log(f"🔄 Faltan {missing_count} recomendaciones. Rellenando...")
                
                # Excluir los IDs que ya fueron recomendados o están en la blacklist
                already_used_ids = set(recs_df_filtered['id'].tolist()) | blocked_ids
                
                # Identificar el índice de la última recomendación válida obtenida
                # Esto asume que raw_recs_df ya está ordenado por recs_score
                
                # Coger las siguientes mejores recomendaciones del DataFrame completo (df) 
                # que no estén en la lista de usados/bloqueados
                
                # Generar una lista de todos los animes rankeados por el modelo que no están en la lista del usuario ni bloqueados
                
                # Para simplificar y dado que ya tenemos raw_recs_df con el doble de elementos:
                # Tomamos los siguientes mejores de raw_recs_df que no fueron filtrados
                
                # Obtener la lista de IDs que sobrevivieron el filtro
                surviving_ids = set(recs_df_filtered['id'].tolist())
                
                # Obtener los nuevos reemplazos de raw_recs_df que no están en la lista de sobrevivientes
                new_recs = raw_recs_df[~raw_recs_df['id'].isin(surviving_ids)].head(missing_count)
                
                # 3d. Unir la lista filtrada con las nuevas recomendaciones
                final_recs_df = pd.concat([recs_df_filtered, new_recs]).head(final_recs_count)
            else:
                # Si no faltan, simplemente limitar al top 10
                final_recs_df = recs_df_filtered.head(final_recs_count)
        else:
            # Si no hay blacklist, solo limitamos al top 10
            final_recs_df = raw_recs_df.head(10)
            
        debug_log(f"✅ Recomendaciones finales tras filtro: {len(final_recs_df)}")
        
        # 4. Guardar y devolver el JSON
        output_json_str = save_recommendations_to_json(final_recs_df, stats)
        
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
        
    except Exception as e:
        print(f"❌ Fallo crítico en ejecución local: {e}", file=sys.stderr)
        sys.exit(1)