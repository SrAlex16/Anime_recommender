# app.py (en la RAIZ del proyecto)
from flask import Flask, request, jsonify
from flask_cors import CORS
import subprocess
import sys
import os
import json
from datetime import datetime

def create_app():
    app = Flask(__name__)
    CORS(app)

    # Configurar paths
    ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, ROOT_DIR)

    def run_pipeline(username):
        """Ejecutar el pipeline completo de recomendación"""
        try:
            print(f"🚀 Iniciando pipeline para usuario: {username}")
            
            script_path = os.path.join(ROOT_DIR, 'src', 'services', 'get_recommendations_for_user.py')
            
            print(f"📁 Script path: {script_path}")
            print(f"📁 Working dir: {ROOT_DIR}")
            print(f"📁 Current dir: {os.getcwd()}")
            
            # Listar archivos para debug
            if os.path.exists("data"):
                try:
                    data_files = os.listdir("data")
                    print(f"📁 Archivos en data/: {data_files}")
                except Exception as e:
                    print(f"📁 Error listando archivos data/: {e}")
            
            # Verificar si el script existe
            if not os.path.exists(script_path):
                print(f"❌ Script no encontrado: {script_path}")
                return None, f"Script no encontrado: {script_path}"
            
            # 🔥 FORZAR ENCODING UTF-8
            env = os.environ.copy()
            env['PYTHONIOENCODING'] = 'utf-8'
            env['PYTHONUTF8'] = '1'
            
            result = subprocess.run([
                sys.executable, '-u', script_path, username  # 🔥 -u para unbuffered
            ], capture_output=True, text=True, cwd=ROOT_DIR, timeout=300, env=env)
            
            print(f"📋 Return code: {result.returncode}")
            print(f"📋 STDOUT length: {len(result.stdout)}")
            print(f"📋 STDOUT preview: {result.stdout[:500]}...")
            print(f"📋 STDERR: {result.stderr}")
            
            if result.returncode == 0:
                # Verificar que stdout no esté vacío
                if not result.stdout.strip():
                    print("❌ STDOUT está vacío")
                    return None, "El script no produjo ninguna salida"
                
                try:
                    # 🔥 Intentar diferentes enfoques para parsear JSON
                    output_text = result.stdout.strip()
                    
                    # Buscar JSON en la salida (por si hay logs antes)
                    if output_text.startswith('{'):
                        json_text = output_text
                    else:
                        # Buscar el primer { y último }
                        start_idx = output_text.find('{')
                        end_idx = output_text.rfind('}') + 1
                        if start_idx != -1 and end_idx != 0:
                            json_text = output_text[start_idx:end_idx]
                        else:
                            json_text = output_text
                    
                    print(f"📋 JSON text to parse (first 200 chars): {json_text[:200]}...")
                    output = json.loads(json_text)
                    return output, None
                    
                except json.JSONDecodeError as e:
                    print(f"❌ Error decodificando JSON: {e}")
                    print(f"❌ Contenido recibido (primeros 1000 chars): {result.stdout[:1000]}")
                    return None, f"Error decodificando JSON: {str(e)}"
            else:
                error_msg = result.stderr or "Error desconocido en el pipeline"
                print(f"❌ Error en pipeline: {error_msg}")
                return None, error_msg
                
        except subprocess.TimeoutExpired:
            print("❌ Error de timeout del subproceso (5 minutos).")
            return None, "El proceso de recomendación tardó más de 5 minutos."
        except Exception as e:
            print(f"❌ Error al ejecutar el subproceso: {e}")
            return None, f"Error interno al ejecutar el pipeline: {str(e)}"

    # 🔥 ENDPOINTS CON NOMBRES ÚNICOS
    @app.route('/api/recommendations/<username>', methods=['GET'])
    def handle_user_recommendations(username):
        """Endpoint principal para generar recomendaciones"""
        print(f"🎯 Solicitando recomendaciones para: {username}")
        
        try:
            response_data, error = run_pipeline(username)
            
            if response_data and response_data.get('status') == 'success':
                print(f"🎉 Éxito. Recomendaciones generadas: {len(response_data['recommendations'])} animes")
                return jsonify(response_data), 200
            else:
                error_msg = error or response_data.get('message', 'Error desconocido en el pipeline')
                return jsonify({
                    "status": "error",
                    "message": error_msg,
                    "timestamp": datetime.now().isoformat()
                }), 400
            
        except Exception as e:
            print(f"❌ Error en endpoint: {e}")
            return jsonify({
                "status": "error",
                "message": f"Error interno del servidor: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }), 500

    @app.route('/api/status', methods=['GET'])
    def handle_api_status():
        """Endpoint para verificar estado del servicio"""
        return jsonify({
            "status": "running",
            "timestamp": datetime.now().isoformat(),
            "environment": os.environ.get('RENDER', 'development'),
            "python_version": sys.version
        })

    @app.route('/api/health', methods=['GET'])
    def handle_health_check():
        """Health check endpoint para Render"""
        return jsonify({
            "status": "healthy",
            "timestamp": datetime.now().isoformat()
        })

    @app.route('/')
    def handle_home():
        """Página de inicio"""
        return jsonify({
            "message": "Anime Recommendation API",
            "version": "2.0",
            "description": "Ejecuta pipeline completo de recomendación",
            "endpoints": {
                "health": "/api/health",
                "status": "/api/status", 
                "recommendations": "/api/recommendations/<username>"
            },
            "example": "https://anime-recommender-1-x854.onrender.com/api/recommendations/SrAlex16"
        })

    return app

# Crear la aplicación Flask
app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"🚀 Iniciando servidor en puerto {port}")
    print(f"📁 Directorio actual: {os.getcwd()}")
    print(f"📁 ROOT_DIR: {os.path.dirname(os.path.dirname(os.path.abspath(__file__)))}")
    app.run(host='0.0.0.0', port=port)