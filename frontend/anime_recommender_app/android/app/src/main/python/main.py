# android/app/src/main/python/main.py
import sys
import os
import json
from model.mobile_recommender import MobileAnimeRecommender

print("=== Anime Recommender Mobile Module Loaded ===")

# Instancia global del recomendador móvil
mobile_recommender = None

def init_mobile_recommender():
    """Inicializa el sistema de recomendación móvil"""
    global mobile_recommender
    
    try:
        print("🚀 Initializing mobile anime recommender...")
        
        mobile_recommender = MobileAnimeRecommender()
        
        # Ruta a los datos pre-procesados en assets
        data_path = os.path.join(os.path.dirname(__file__), "../assets/data/final_dataset.csv")
        
        # Cargar datos
        success, message = mobile_recommender.load_and_preprocess_data(data_path)
        if not success:
            return f"Error loading data: {message}"
        
        # Entrenar modelo
        success, message = mobile_recommender.train_model()
        if not success:
            return f"Error training model: {message}"
            
        return "Mobile recommender initialized successfully"
            
    except Exception as e:
        return f"Error initializing mobile recommender: {str(e)}"

def get_mobile_recommendations(preferences_json):
    """Obtiene recomendaciones usando el modelo móvil"""
    global mobile_recommender
    
    try:
        preferences = json.loads(preferences_json)
        print(f"📱 Received preferences: {preferences}")
        
        if mobile_recommender is None:
            init_result = init_mobile_recommender()
            if "Error" in init_result:
                return [{"error": init_result}]
        
        recommendations = mobile_recommender.get_recommendations(preferences, top_n=10)
        return recommendations
        
    except Exception as e:
        return [{"error": f"Mobile recommendation error: {str(e)}"}]

def get_user_statistics():
    """Obtiene estadísticas del usuario"""
    global mobile_recommender
    
    try:
        if mobile_recommender is None:
            init_result = init_mobile_recommender()
            if "Error" in init_result:
                return {"error": init_result}
        
        stats = mobile_recommender.get_user_stats()
        return stats
        
    except Exception as e:
        return {"error": str(e)}

def test_function():
    """Función simple para probar que Python funciona"""
    return "¡Python móvil está funcionando correctamente en Flutter!"

if __name__ == "__main__":
    print(test_function())