from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel
from sklearn.decomposition import TruncatedSVD
import requests
import json
import time
import os
from datetime import datetime
import ast

app = Flask(__name__)
CORS(app)

class AnimeRecommender:
    def __init__(self):
        self.anime_df = None
        self.cosine_sim = None
        self.tfidf = None
        
    def load_anime_data(self):
        """Cargar dataset de anime desde URL pública"""
        try:
            url = "https://raw.githubusercontent.com/HenryTSI/anime-recommender-system/main/data/anime_cleaned.csv"
            self.anime_df = pd.read_csv(url)
            print(f"✅ Datos de anime cargados: {len(self.anime_df)} animes")
            
            # Preprocesar datos
            for col in ['genres', 'tags']:
                self.anime_df[col] = self.anime_df[col].apply(
                    lambda x: ast.literal_eval(x) if pd.notna(x) and isinstance(x, str) and '[' in x else []
                )
                self.anime_df[col] = self.anime_df[col].apply(
                    lambda x: ' '.join([str(i).replace(" ", "") for i in x])
                )
            
            self.anime_df['combined_features'] = self.anime_df.apply(
                lambda row: f"{row['title']} {row['genres']} {row['tags']} {row['description']}", 
                axis=1
            )
            
            return True
        except Exception as e:
            print(f"❌ Error cargando datos: {e}")
            return False
    
    def build_model(self):
        """Construir modelo de recomendación"""
        try:
            self.tfidf = TfidfVectorizer(stop_words='english')
            self.anime_df['combined_features'] = self.anime_df['combined_features'].fillna('')
            tfidf_matrix = self.tfidf.fit_transform(self.anime_df['combined_features'])
            
            n_components = min(200, tfidf_matrix.shape[1] - 1)
            svd = TruncatedSVD(n_components=n_components, random_state=42)
            latent_matrix = svd.fit_transform(tfidf_matrix)
            
            self.cosine_sim = linear_kernel(latent_matrix, latent_matrix)
            print("✅ Modelo entrenado exitosamente")
            return True
        except Exception as e:
            print(f"❌ Error entrenando modelo: {e}")
            return False

# Instancia global del recomendador
recommender = AnimeRecommender()

def download_user_list(username):
    """Descargar lista de usuario desde MAL"""
    try:
        full_list = []
        offset = 0
        page_size = 300
        
        print(f"📡 Descargando lista de {username}...")
        
        while True:
            url = f"https://myanimelist.net/animelist/{username}/load.json?status=7&offset={offset}"
            
            time.sleep(0.5)
            response = requests.get(url, headers={'User-Agent': 'MAL-API-App'})
            
            if response.status_code != 200:
                return None
            
            data = response.json()
            if not data:
                break
                
            full_list.extend(data)
            offset += len(data)
            
            if len(data) < page_size:
                break
        
        print(f"✅ Lista descargada: {len(full_list)} animes")
        return full_list
    except Exception as e:
        print(f"❌ Error descargando lista: {e}")
        return None

def get_recommendations_for_user(username, top_n=10):
    """Generar recomendaciones para un usuario"""
    try:
        # 1. Descargar lista del usuario
        user_list = download_user_list(username)
        if not user_list:
            return None, "No se pudo descargar la lista del usuario"
        
        # 2. Procesar ratings del usuario
        user_ratings = []
        for item in user_list:
            anime_id = item.get('anime_id')
            score = int(str(item.get('score', 0))) if str(item.get('score', '0')).isdigit() else 0
            status_id = item.get('status')
            
            if anime_id and score > 0:
                user_ratings.append({
                    'anime_id': anime_id,
                    'user_score': score,
                    'status': status_id
                })
        
        if not user_ratings:
            return None, "El usuario no tiene animes calificados"
        
        # 3. Fusionar con dataset principal
        user_df = pd.DataFrame(user_ratings)
        user_df['anime_id'] = pd.to_numeric(user_df['anime_id'], errors='coerce')
        
        # Asumiendo que tu dataset tiene columna 'MAL_ID' para hacer match
        df_merged = recommender.anime_df.merge(
            user_df, 
            left_on='MAL_ID', 
            right_on='anime_id', 
            how='left'
        )
        
        df_merged['user_score'] = df_merged['user_score'].fillna(0)
        
        # 4. Generar recomendaciones
        score_vector = df_merged['user_score'].values / 10
        total_scores = np.dot(recommender.cosine_sim, score_vector)
        
        df_recommendations = df_merged.copy()
        df_recommendations['hybrid_score'] = total_scores
        
        # Filtrar animes ya vistos
        watched_ids = [item['anime_id'] for item in user_list]
        df_recommendations = df_recommendations[~df_recommendations['MAL_ID'].isin(watched_ids)]
        
        # Filtrar por score mínimo y ordenar
        df_recommendations = df_recommendations[df_recommendations['score'] >= 70]
        df_recommendations = df_recommendations.sort_values('hybrid_score', ascending=False)
        
        return df_recommendations.head(top_n), None
        
    except Exception as e:
        print(f"❌ Error generando recomendaciones: {e}")
        return None, str(e)

def generate_statistics(user_list, recommendations):
    """Generar estadísticas del usuario"""
    try:
        total_rated = len([item for item in user_list if int(str(item.get('score', 0))) > 0])
        favorites_count = len([item for item in user_list if int(str(item.get('score', 0))) >= 8])
        
        return {
            'total_animes_catalog': len(recommender.anime_df),
            'total_user_animes': len(user_list),
            'total_rated': total_rated,
            'favorites_count': favorites_count,
            'recommendations_generated': len(recommendations) if recommendations is not None else 0
        }
    except Exception as e:
        print(f"❌ Error generando estadísticas: {e}")
        return {}

# Rutas de la API
@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})

@app.route('/api/recommendations/<username>', methods=['GET'])
def get_recommendations(username):
    """Endpoint principal para obtener recomendaciones"""
    try:
        start_time = time.time()
        
        # Validar username
        if not username or len(username.strip()) == 0:
            return jsonify({
                "status": "error",
                "message": "Username no puede estar vacío"
            }), 400
        
        username = username.strip()
        
        # Descargar lista para estadísticas
        user_list = download_user_list(username)
        if not user_list:
            return jsonify({
                "status": "error", 
                "message": "No se pudo acceder a la lista del usuario. Verifica que el username sea correcto y la lista sea pública."
            }), 404
        
        # Generar recomendaciones
        recommendations, error = get_recommendations_for_user(username)
        
        if error:
            return jsonify({
                "status": "error",
                "message": error
            }), 400
        
        # Preparar respuesta
        recommendations_list = []
        for _, row in recommendations.iterrows():
            recommendations_list.append({
                'id': int(row.get('MAL_ID', 0)),
                'title': row.get('title', 'Título Desconocido'),
                'score': float(row.get('score', 0)),
                'type': row.get('type', 'N/A'),
                'genres': row.get('genres', '').split() if isinstance(row.get('genres'), str) else [],
                'description': row.get('description', '')[:200] + '...' if row.get('description') else '',
                'hybrid_score': float(row.get('hybrid_score', 0))
            })
        
        # Generar estadísticas
        stats = generate_statistics(user_list, recommendations)
        
        response_data = {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "processing_time": f"{time.time() - start_time:.2f}s",
            "count": len(recommendations_list),
            "statistics": stats,
            "recommendations": recommendations_list
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Error interno del servidor: {str(e)}"
        }), 500

@app.route('/api/status', methods=['GET'])
def get_status():
    """Endpoint para verificar estado del modelo"""
    model_loaded = recommender.anime_df is not None and recommender.cosine_sim is not None
    return jsonify({
        "model_loaded": model_loaded,
        "anime_count": len(recommender.anime_df) if model_loaded else 0,
        "timestamp": datetime.now().isoformat()
    })

# Inicializar modelo al arrancar
@app.before_first_request
def initialize_model():
    print("🚀 Inicializando modelo de recomendación...")
    if recommender.load_anime_data() and recommender.build_model():
        print("✅ Modelo inicializado exitosamente")
    else:
        print("❌ Error inicializando modelo")

if __name__ == '__main__':
    # Inicializar modelo inmediatamente
    if recommender.load_anime_data() and recommender.build_model():
        print("✅ Modelo cargado exitosamente")
    else:
        print("❌ Error cargando modelo")
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)