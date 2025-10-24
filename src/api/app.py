# src/api/app.py
from flask import Flask, jsonify, request
from flask_cors import CORS
import subprocess
import sys
import os
import json
from datetime import datetime

# ✅ Importar blueprint de blacklist
from src.api.blacklist import blacklist_bp

def create_app():
    app = Flask(__name__)
    CORS(app)

    # Registrar blueprint de blacklist
    app.register_blueprint(blacklist_bp)

    # Configurar paths - desde src/api/
    ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    sys.path.insert(0, ROOT_DIR)

    # ---------------- Pipeline Recommendations ----------------
    def run_pipeline(username):
        """Ejecutar el pipeline completo de recomendación"""
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

            if result.returncode != 0:
                error_message = f"Pipeline falló con código {result.returncode}."
                try:
                    error_data = json.loads(result.stdout.strip())
                    if error_data.get('status') == 'error':
                        error_message = error_data.get('message', error_message)
                except:
                    if result.stderr:
                        error_message += f" STDERR: {result.stderr}"
                return None, error_message

            try:
                data = json.loads(result.stdout.strip())
                return data, None
            except json.JSONDecodeError:
                return None, "Respuesta inválida del pipeline (no es JSON válido)."

        except subprocess.TimeoutExpired:
            return None, "Timeout: El proceso de recomendación tardó demasiado (5 minutos)."
        except Exception as e:
            return None, str(e)

    # ---------------- Endpoints ----------------
    @app.route('/api/recommendations/<username>', methods=['GET'])
    def get_recommendations(username):
        """Genera recomendaciones para un usuario de MyAnimeList."""
        data, error = run_pipeline(username)
        if error:
            return jsonify({
                "status": "error",
                "message": error,
                "timestamp": datetime.now().isoformat()
            }), 500
        return jsonify(data), 200

    @app.route('/api/health', methods=['GET'])
    def health_check():
        """Retorna el estado de salud de la aplicación"""
        return jsonify({
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "python_version": sys.version
        }), 200

    @app.route('/api/status', methods=['GET'])
    def status():
        """Verifica archivos y directorios críticos"""
        critical_files = [
            'data/final_dataset.csv',
            'src/data/fetch_datasets.py',
            'src/model/train_model.py',
            'src/services/get_recommendations_for_user.py',
        ]
        critical_dirs = ['data', 'src/data', 'src/model', 'src/services']

        for file_path in critical_files:
            if not os.path.exists(os.path.join(ROOT_DIR, file_path)):
                return jsonify({
                    "status": "error",
                    "message": f"Archivo crítico no encontrado: {file_path}",
                    "timestamp": datetime.now().isoformat()
                }), 500

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
