# src/api/app.py
from flask import Flask, request, jsonify
from flask_cors import CORS
import subprocess
import sys
import os
import json
from datetime import datetime
# ✅ NUEVOS IMPORTS para la blacklist
from src.model.train_model import add_to_blacklist, load_blacklist 
from src.api.blacklist import blacklist_bp

# Endpoint de prueba
@app.route("/api/health")
def health():
    import sys
    import platform
    return {
        "status": "healthy",
        "python_version": platform.python_version(),
        "timestamp": __import__("datetime").datetime.utcnow().isoformat()
    }

def create_app():
    app = Flask(__name__)
    CORS(app)

    # Registrar el blueprint de blacklist
    app.register_blueprint(blacklist_bp)

    # Configurar paths - desde src/api/
    ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    sys.path.insert(0, ROOT_DIR)

    def run_pipeline(username):
        """Ejecutar el pipeline completo de recomendación"""
        try:
            print(f"🚀 Iniciando pipeline para usuario: {username}")
            
            script_path = os.path.join(ROOT_DIR, 'src', 'services', 'get_recommendations_for_user.py')
            
            print(f"📁 Script path: {script_path}")
            print(f"📁 Working dir: {ROOT_DIR}")
            print(f"📁 Current dir: {os.getcwd()}")
            
            # Verificar si el script existe
            if not os.path.exists(script_path):
                print(f"❌ Script no encontrado: {script_path}")
                return None, f"Script no encontrado: {script_path}"
            
            # FORZAR ENCODING UTF-8
            env = os.environ.copy()
            env['PYTHONIOENCODING'] = 'utf-8'
            env['PYTHONUTF8'] = '1'
            
            # Usar sys.executable para asegurar el entorno virtual
            result = subprocess.run([
                sys.executable, '-u', script_path, username
            ], capture_output=True, text=True, timeout=300, cwd=ROOT_DIR, env=env) # Timeout a 5 minutos
            
            # Imprimir STDOUT y STDERR para debugging
            print(f"📋 STDOUT (pipeline): {result.stdout}")
            print(f"📋 STDERR (pipeline): {result.stderr}")

            if result.returncode != 0:
                error_message = f"El pipeline de Python falló con código {result.returncode}."
                
                # Intentar extraer error del output si existe
                try:
                    # El script final debería imprimir un JSON de error al stdout
                    error_data = json.loads(result.stdout.strip())
                    if error_data.get('status') == 'error':
                        error_message = error_data.get('message', error_message)
                except:
                    # Si no es un JSON, usar el stderr
                    if result.stderr:
                         error_message += f" STDERR: {result.stderr}"
                    
                print(f"❌ Error en la ejecución del pipeline: {error_message}")
                return None, error_message

            # El resultado debe ser un string JSON en la salida estándar
            output_json_str = result.stdout.strip()
            
            # Intentar decodificar la salida JSON
            try:
                data = json.loads(output_json_str)
                return data, None
            except json.JSONDecodeError:
                 print(f"❌ Error de decodificación JSON en el output del pipeline. Output: {output_json_str}")
                 return None, "Respuesta inválida del pipeline (no es JSON válido)."
            
        except subprocess.TimeoutExpired:
            return None, "Timeout: El proceso de recomendación tardó demasiado (5 minutos)."
        except Exception as e:
            return None, str(e)


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
        
        # El pipeline ya devuelve el formato JSON final (incluyendo status: 'success')
        return jsonify(data), 200

    # --- ✅ NUEVO ENDPOINT: Blacklist API (POST) ---
    @app.route('/api/blacklist', methods=['POST'])
    def handle_blacklist():
        """
        Añade IDs de anime a la blacklist global.
        Espera un cuerpo JSON con la clave 'anime_ids': [123, 456, ...]
        """
        try:
            # 1. Verificar el tipo de contenido
            if not request.is_json:
                return jsonify({
                    "status": "error",
                    "message": "Content-Type debe ser 'application/json'",
                    "timestamp": datetime.now().isoformat()
                }), 415 # Unsupported Media Type

            data = request.get_json()
            anime_ids = data.get('anime_ids')

            # 2. Validar el cuerpo de la petición
            if not anime_ids or not isinstance(anime_ids, list):
                return jsonify({
                    "status": "error",
                    "message": "Falta la clave 'anime_ids' o no es una lista válida",
                    "timestamp": datetime.now().isoformat()
                }), 400 # Bad Request

            # 3. Procesar la blacklist
            final_list = add_to_blacklist(anime_ids)
            
            # 4. Respuesta de éxito
            return jsonify({
                "status": "success",
                "message": f"{len(anime_ids)} IDs procesados. Total en blacklist: {len(final_list)}",
                "total_blacklisted": len(final_list),
                "timestamp": datetime.now().isoformat()
            }), 200

        except Exception as e:
            # 5. Respuesta de error interno
            print(f"❌ Error en /api/blacklist: {e}")
            return jsonify({
                "status": "error",
                "message": f"Error interno del servidor al actualizar blacklist: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }), 500 # Internal Server Error
    
    # --- ✅ NUEVO ENDPOINT: Blacklist API (GET - opcional para verificación) ---
    @app.route('/api/blacklist', methods=['GET'])
    def get_blacklist():
        """Retorna la lista completa de IDs en la blacklist."""
        try:
            blacklist = load_blacklist()
            return jsonify({
                "status": "success",
                "data": blacklist,
                "total_blacklisted": len(blacklist),
                "timestamp": datetime.now().isoformat()
            }), 200
        except Exception as e:
            return jsonify({
                "status": "error",
                "message": f"Error al obtener blacklist: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }), 500

    @app.route('/api/health', methods=['GET'])
    def health_check():
        """Retorna el estado de salud de la aplicación (solo verifica Flask)."""
        try:
            # Este es un chequeo muy básico, solo verifica que la aplicación Flask está corriendo.
            return jsonify({
                "status": "healthy", 
                "timestamp": datetime.now().isoformat()
            }), 200
        except Exception as e:
            return jsonify({
                "status": "error",
                "message": str(e),
                "timestamp": datetime.now().isoformat()
            }), 500

    @app.route('/api/status', methods=['GET'])
    def status():
        """Retorna el estado del sistema, incluyendo verificación de archivos críticos."""
        # Rutas a verificar
        critical_files = [
            'data/final_dataset.csv',
            'src/data/fetch_datasets.py',
            'src/model/train_model.py',
            'src/services/get_recommendations_for_user.py',
        ]
        
        try:
            # 1. Verificar archivos críticos
            for file_path in critical_files:
                if not os.path.exists(os.path.join(ROOT_DIR, file_path)):
                    return jsonify({
                        "status": "error", 
                        "message": f"Archivo crítico no encontrado: {file_path}",
                        "timestamp": datetime.now().isoformat()
                    }), 500
            
            # 2. Verificar directorios
            critical_dirs = ['data', 'src/data', 'src/model', 'src/services']
            for dir_path in critical_dirs:
                if not os.path.exists(os.path.join(ROOT_DIR, dir_path)):
                    return jsonify({
                        "status": "error", 
                        "message": f"Directorio {dir_path} no encontrado",
                        "timestamp": datetime.now().isoformat()
                    }), 500
                    
            return jsonify({
                "status": "healthy", 
                "timestamp": datetime.now().isoformat(),
                "python_version": sys.version
            })
        except Exception as e:
            return jsonify({
                "status": "error",
                "message": str(e),
                "timestamp": datetime.now().isoformat()
            }), 500

    @app.route('/')
    def home():
        """Página de inicio"""
        return jsonify({
            "message": "Anime Recommendation API",
            "version": "2.0",
            "description": "Sistema de recomendación de anime basado en contenido",
            "endpoints": {
                "health": "/api/health",
                "status": "/api/status", 
                "recommendations": "/api/recommendations/<username>",
                "blacklist_post": "/api/blacklist (POST)", # ✅ NUEVO ENDPOINT
                "blacklist_get": "/api/blacklist (GET)" # ✅ NUEVO ENDPOINT
            },
            "example": "https://anime-recommender-1-x854.onrender.com/api/recommendations/SrAlex16"
        })

    return app

# 🔥 CRÍTICO: Crear la instancia de app
app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"🚀 Iniciando servidor en puerto {port}")
    app.run(host='0.0.0.0', port=port)
