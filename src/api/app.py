# src/api/app.py

from flask import Flask, jsonify, request
from flask_cors import CORS
import subprocess
import sys
import os
import json
from datetime import datetime

# ✅ Importar blueprint de blacklist Y la nueva función de soporte
from src.api.blacklist import blacklist_bp, get_blacklist_last_modified_time 

def create_app():
    app = Flask(__name__)
    CORS(app)

    # Registrar blueprint de blacklist
    app.register_blueprint(blacklist_bp)

    # Configurar paths - desde src/api/
    ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    sys.path.insert(0, ROOT_DIR)
    
    # 💡 CACHÉ GLOBAL EN MEMORIA (se limpia si el proceso de Render se reinicia)
    # Almacenaremos {cache_key: result_data}
    recommendations_cache = {} 

    # ---------------- Pipeline Recommendations ----------------
    def run_pipeline(username):
        """Ejecutar el pipeline completo de recomendación"""
        # ... (CÓDIGO run_pipeline EXISTENTE - NO CAMBIA)
        try:
            script_path = os.path.join(ROOT_DIR, 'src', 'services', 'get_recommendations_for_user.py')
            if not os.path.exists(script_path):
                return None, f"Script no encontrado: {script_path}"

            env = os.environ.copy()
            env['PYTHONIOENCODING'] = 'utf-8'
            env['PYTHONUTF8'] = '1'

            result = subprocess.run(
                [sys.executable, '-u', script_path, username],
                capture_output=True, text=True, timeout=300, cwd=ROOT_DIR, env=env
            )
            
            # 🛑 CRÍTICO: Si hay un código de retorno de error (no 0)
            if result.returncode != 0:
                error_msg = f"Error en el script Python (Código {result.returncode}). STDERR: {result.stderr}"
                # Intentamos parsear la salida JSON de error si existe, si no, devolvemos el mensaje genérico
                try:
                    # El script debería haber impreso un JSON de error al stdout
                    error_data = json.loads(result.stdout) 
                    # Devolvemos el mensaje del JSON que el script intentó generar
                    return None, error_data.get('message', error_msg)
                except json.JSONDecodeError:
                    # Si stdout no es JSON, es porque otra cosa falló e imprimió basura
                    # Devolvemos el stderr completo, que es más informativo
                    return None, f"El pipeline falló. Output no JSON. STDERR: {result.stderr.strip()}"

            # Si returncode es 0, asumimos que stdout es JSON de éxito
            return result.stdout, None
            
        except subprocess.TimeoutExpired:
            return None, "El proceso de generación de recomendaciones excedió el tiempo límite (300s)."
        except Exception as e:
            return None, f"Error interno en la ejecución del pipeline: {str(e)}"

    @app.route('/api/recommendations/<username>', methods=['GET'])
    def get_recommendations_route(username):
        
        # 1. GENERAR CLAVE DE CACHÉ 💡
        try:
            # El timestamp de la blacklist será la parte variable de la clave
            blacklist_ts = get_blacklist_last_modified_time() 
        except Exception:
            blacklist_ts = 0.0
            
        cache_key = f"{username}_{blacklist_ts}"

        # 2. VERIFICAR CACHÉ 💡
        if cache_key in recommendations_cache:
            # CASO 1: Éxito (Blacklist no modificada) -> Retorno INSTANTÁNEO
            result = recommendations_cache[cache_key].copy()
            result['message'] = "Cargado desde caché de API (Blacklist no modificada)."
            return jsonify(result), 200

        # 3. EJECUTAR PIPELINE COMPLETO
        # CASO 2: Blacklist modificada o primera ejecución -> Ejecutar proceso pesado
        app.logger.info(f"Cache miss para {username}. Ejecutando pipeline completo (Timeout riesgo alto)...")
        result_json_str, error_msg = run_pipeline(username)

        if error_msg:
            return jsonify({
                "status": "error",
                "message": error_msg,
                "timestamp": datetime.now().isoformat()
            }), 500
        
        try:
            result_data = json.loads(result_json_str)
        except json.JSONDecodeError:
            return jsonify({
                "status": "error",
                "message": f"Error interno: La salida del modelo no es JSON válida.",
                "timestamp": datetime.now().isoformat()
            }), 500
        
        # 4. GUARDAR EN CACHÉ antes de devolver el resultado 💡
        if result_data.get('status') == 'success':
            # Guardamos el resultado con la nueva clave de caché
            recommendations_cache[cache_key] = result_data 
            app.logger.info(f"Resultado de {username} guardado en caché con clave: {cache_key}")
            
        return jsonify(result_data), 200

    @app.route('/api/health')
    def health_check():
        # ... (CÓDIGO EXISTENTE)
        ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        critical_dirs = ['data', os.path.join('src', 'model'), os.path.join('src', 'data')]

        for dir_path in critical_dirs:
            if not os.path.exists(os.path.join(ROOT_DIR, dir_path)):
                return jsonify({
                    "status": "error",
                    "message": f"Directorio crítico no encontrado: {dir_path}",
                    "timestamp": datetime.now().isoformat()
                }), 500

        return jsonify({
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "python_version": sys.version
        }), 200

    @app.route('/')
    def home():
        return jsonify({
            "message": "Anime Recommendation API",
            "version": "2.0",
            "description": "Sistema de recomendación de anime basado en contenido",
            "endpoints": {
                "health": "/api/health",
                "status": "/api/status",
                "recommendations": "/api/recommendations/<username>",
                "blacklist_post": "/api/blacklist (POST)",
                "blacklist_get": "/api/blacklist (GET)"
            },
            "example": "https://anime-recommender-1-x854.onrender.com/api/recommendations/SrAlex16"
        })

    return app

# ---------------- Crear instancia ----------------
app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"🚀 Iniciando servidor en puerto {port}")
    app.run(host='0.0.0.0', port=port)