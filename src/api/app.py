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
    # Sube dos niveles para ir a la raíz del proyecto
    ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    sys.path.insert(0, ROOT_DIR)

    # ---------------- Pipeline Recommendations ----------------
    def run_pipeline(username):
        """Ejecutar el pipeline completo de recomendación"""
        try:
            # Llama al script orquestador que gestiona la descarga y el modelo
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

            # El script de python devuelve un JSON string en su stdout
            output = result.stdout.strip()
            
            if result.returncode != 0:
                error_message = f"Pipeline falló con código {result.returncode}."
                if result.stderr:
                     error_message += f" STDERR: {result.stderr.strip()[:500]}"
                return None, error_message
            
            # El output debe ser un JSON
            try:
                # El script está diseñado para imprimir un JSON final
                return json.loads(output), None
            except json.JSONDecodeError:
                error_message = f"Error al decodificar JSON de salida. STDOUT: {output[:500]}"
                if result.stderr:
                    error_message += f" STDERR: {result.stderr.strip()[:500]}"
                return None, error_message


        except subprocess.TimeoutExpired:
            return None, "Timeout: El pipeline de recomendación tardó demasiado (más de 5 minutos)."
        except Exception as e:
            return None, f"Error inesperado al ejecutar el pipeline: {str(e)}"

    @app.route('/api/recommendations/<username>', methods=['GET'])
    def get_recommendations(username):
        if not username:
            return jsonify({
                "status": "error",
                "message": "El nombre de usuario es requerido.",
                "timestamp": datetime.now().isoformat()
            }), 400

        print(f"⚙️ Iniciando pipeline para usuario: {username}")
        recommendations_data, error = run_pipeline(username)

        if error:
            print(f"❌ Error en la recomendación: {error}")
            return jsonify({
                "status": "error",
                "message": error,
                "timestamp": datetime.now().isoformat()
            }), 500

        # El JSON ya viene estructurado con 'status', 'recommendations', 'statistics', etc.
        return jsonify(recommendations_data), 200


    @app.route('/api/health')
    def health_check():
        """Verificación de salud simple"""
        try:
            # Verificar un módulo crítico, por ejemplo, pandas
            import pandas as pd
        except ImportError as e:
            return jsonify({
                "status": "error",
                "message": f"Dependencia crítica no encontrada: {e}",
                "timestamp": datetime.now().isoformat()
            }), 500

        # Verificar si existen directorios críticos
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
    app.run(host='0.0.0.0', port=port, debug=True)