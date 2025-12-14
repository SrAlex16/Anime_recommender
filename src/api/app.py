# src/api/app.py
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
            
            result = subprocess.run([
                sys.executable, '-u', script_path, username
            ], capture_output=True, text=True, cwd=ROOT_DIR, timeout=300, env=env)
            
            print(f"📋 Return code: {result.returncode}")
            print(f"📋 STDOUT length: {len(result.stdout)}")
            print(f"📋 STDOUT preview: {result.stdout[:200]}...")
            
            if result.returncode == 0:
                if not result.stdout.strip():
                    print("❌ STDOUT está vacío")
                    return None, "El script no produjo ninguna salida"
                
                try:
                    output_text = result.stdout.strip()
                    
                    # Buscar JSON en la salida
                    if output_text.startswith('{'):
                        json_text = output_text
                    else:
                        start_idx = output_text.find('{')
                        end_idx = output_text.rfind('}') + 1
                        if start_idx != -1 and end_idx != 0:
                            json_text = output_text[start_idx:end_idx]
                        else:
                            json_text = output_text
                    
                    print(f"📋 JSON a parsear: {json_text[:100]}...")
                    output = json.loads(json_text)
                    return output, None
                    
                except json.JSONDecodeError as e:
                    print(f"❌ Error decodificando JSON: {e}")
                    print(f"❌ Contenido completo: {result.stdout}")
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

    # ENDPOINTS
    @app.route('/api/recommendations/<username>', methods=['GET'])
    def get_user_recommendations(username):
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
    def get_api_status():
        """Endpoint para verificar estado del servicio"""
        return jsonify({
            "status": "running",
            "timestamp": datetime.now().isoformat()
        })

    @app.route('/api/health', methods=['GET'])
    @app.route('/api/health', methods=['GET'])
    def health_check():
        """Health check más robusto para Render"""
        try:
            # Verificar que los directorios críticos existen
            required_dirs = ['src', 'src/api', 'src/data', 'src/model']
            for dir_path in required_dirs:
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
                "recommendations": "/api/recommendations/<username>"
            },
            "example": "https://anime-recommender-1-x854.onrender.com/api/recommendations/SrAlex16"
        })

    @app.route("/api/status", methods=["GET"])
    def status():
        return jsonify({
            "status": "ok",
            "service": "anime-recommender",
            "timestamp": datetime.utcnow().isoformat() + "Z",
        })
    
    @app.route('/api/blacklist', methods=['POST'])
    def add_to_blacklist():
        try:
            data = request.get_json(force=True)
            anime_ids = data.get('anime_ids', [])
            if not isinstance(anime_ids, list):
                return jsonify({"status": "error", "message": "anime_ids debe ser lista"}), 400

            # Guardar en JSON local (sobrescribimos)
            blacklist_path = os.path.join(ROOT_DIR, "data", "blacklist.json")
            existing = []
            if os.path.exists(blacklist_path):
                with open(blacklist_path, 'r', encoding='utf-8') as f:
                    existing = json.load(f)
            # Unión sin duplicados
            existing = list(set(existing + [str(i) for i in anime_ids]))
            with open(blacklist_path, 'w', encoding='utf-8') as f:
                json.dump(existing, f)

            print(f"✅ Blacklist actualizada: {len(existing)} IDs")
            return jsonify({"status": "success", "count": len(anime_ids)}), 200
        except Exception as e:
            print("❌ Error blacklist:", e)
            return jsonify({"status": "error", "message": str(e)}), 500
        
    @app.route('/api/blacklist', methods=['GET'])
    def get_blacklist():
        """Obtener la lista completa de IDs en blacklist"""
        try:
            blacklist_path = os.path.join(ROOT_DIR, 'data', 'blacklist.json')
            
            if not os.path.exists(blacklist_path):
                return jsonify({
                    "status": "success",
                    "blacklist": [],
                    "timestamp": datetime.now().isoformat()
                }), 200
            
            with open(blacklist_path, 'r', encoding='utf-8') as f:
                blacklist = json.load(f)
            
            return jsonify({
                "status": "success",
                "blacklist": blacklist,
                "count": len(blacklist),
                "timestamp": datetime.now().isoformat()
            }), 200
            
        except Exception as e:
            print(f"❌ Error obteniendo blacklist: {e}")
            return jsonify({
                "status": "error",
                "message": str(e),
                "timestamp": datetime.now().isoformat()
            }), 500
        
    @app.route('/api/blacklist', methods=['POST'])
    def add_to_blacklist():
        """Añadir IDs a la blacklist"""
        try:
            data = request.get_json()
            anime_ids = data.get('anime_ids', [])
            
            if not anime_ids:
                return jsonify({
                    "status": "error",
                    "message": "No se proporcionaron IDs para añadir",
                    "timestamp": datetime.now().isoformat()
                }), 400
            
            # Convertir a enteros
            anime_ids = [int(id) for id in anime_ids if str(id).isdigit()]
            
            blacklist_path = os.path.join(ROOT_DIR, 'data', 'blacklist.json')
            os.makedirs(os.path.dirname(blacklist_path), exist_ok=True)
            
            # Cargar blacklist existente
            existing_blacklist = []
            if os.path.exists(blacklist_path):
                with open(blacklist_path, 'r', encoding='utf-8') as f:
                    existing_blacklist = json.load(f)
            
            # Añadir nuevos IDs (sin duplicados)
            updated_blacklist = list(set(existing_blacklist + anime_ids))
            
            # Guardar
            with open(blacklist_path, 'w', encoding='utf-8') as f:
                json.dump(updated_blacklist, f, indent=2)
            
            print(f"✅ {len(anime_ids)} IDs añadidos a blacklist. Total: {len(updated_blacklist)}")
            
            return jsonify({
                "status": "success",
                "message": f"{len(anime_ids)} animes añadidos a la blacklist",
                "blacklist": updated_blacklist,
                "count": len(updated_blacklist),
                "timestamp": datetime.now().isoformat()
            }), 200
            
        except Exception as e:
            print(f"❌ Error añadiendo a blacklist: {e}")
            return jsonify({
                "status": "error",
                "message": str(e),
                "timestamp": datetime.now().isoformat()
            }), 500
        
    @app.route('/api/blacklist', methods=['DELETE'])
    def remove_from_blacklist():
        """Eliminar IDs de la blacklist"""
        try:
            data = request.get_json()
            anime_ids = data.get('anime_ids', [])
            
            if not anime_ids:
                return jsonify({
                    "status": "error",
                    "message": "No se proporcionaron IDs para eliminar",
                    "timestamp": datetime.now().isoformat()
                }), 400
            
            # Convertir a enteros
            anime_ids = [int(id) for id in anime_ids if str(id).isdigit()]
            
            blacklist_path = os.path.join(ROOT_DIR, 'data', 'blacklist.json')
            
            if not os.path.exists(blacklist_path):
                return jsonify({
                    "status": "success",
                    "message": "La blacklist está vacía",
                    "blacklist": [],
                    "timestamp": datetime.now().isoformat()
                }), 200
            
            # Cargar blacklist
            with open(blacklist_path, 'r', encoding='utf-8') as f:
                existing_blacklist = json.load(f)
            
            # Eliminar IDs
            updated_blacklist = [id for id in existing_blacklist if id not in anime_ids]
            
            # Guardar
            with open(blacklist_path, 'w', encoding='utf-8') as f:
                json.dump(updated_blacklist, f, indent=2)
            
            print(f"✅ {len(anime_ids)} IDs eliminados de blacklist. Total: {len(updated_blacklist)}")
            
            return jsonify({
                "status": "success",
                "message": f"{len(anime_ids)} animes eliminados de la blacklist",
                "blacklist": updated_blacklist,
                "count": len(updated_blacklist),
                "timestamp": datetime.now().isoformat()
            }), 200
            
        except Exception as e:
            print(f"❌ Error eliminando de blacklist: {e}")
            return jsonify({
                "status": "error",
                "message": str(e),
                "timestamp": datetime.now().isoformat()
            }), 500
        
    return app

# 🔥 CRÍTICO: Crear la instancia de app
app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"🚀 Iniciando servidor en puerto {port}")
    app.run(host='0.0.0.0', port=port)