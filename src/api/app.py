# api/app.py

from flask import Flask, request, jsonify
from flask_cors import CORS
import subprocess
import sys
import os
import json
import time
from datetime import datetime

app = Flask(__name__)
CORS(app)

# Configurar paths
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT_DIR)

def run_pipeline(username):
    """Ejecutar el pipeline completo de recomendación"""
    try:
        print(f"🚀 Iniciando pipeline para usuario: {username}")
        
        # Ruta al script principal
        os.path.join(ROOT_DIR, 'src', 'services', 'get_recommendations_for_user.py')
        
        # Ejecutar el script con el username como argumento
        result = subprocess.run([
            sys.executable, script_path, username
        ], capture_output=True, text=True, cwd=ROOT_DIR, timeout=300)  # 5 minutos timeout
        
        print(f"📋 Script ejecutado. Return code: {result.returncode}")
        
        if result.returncode == 0:
            # El script imprime JSON a stdout
            output = result.stdout.strip()
            print(f"✅ Pipeline completado exitosamente")
            return json.loads(output), None
        else:
            error_msg = result.stderr or "Error desconocido en el pipeline"
            print(f"❌ Error en pipeline: {error_msg}")
            return None, error_msg
            
    except subprocess.TimeoutExpired:
        error_msg = "El proceso tardó demasiado tiempo (más de 5 minutos)"
        print(f"❌ {error_msg}")
        return None, error_msg
    except json.JSONDecodeError as e:
        error_msg = f"Error decodificando JSON: {e}"
        print(f"❌ {error_msg}")
        return None, error_msg
    except Exception as e:
        error_msg = f"Error ejecutando pipeline: {str(e)}"
        print(f"❌ {error_msg}")
        return None, error_msg

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "healthy", 
        "timestamp": datetime.now().isoformat()
    })

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
        print(f"🎯 Solicitando recomendaciones para: {username}")
        
        # Ejecutar pipeline completo
        result, error = run_pipeline(username)
        
        if error:
            return jsonify({
                "status": "error",
                "message": error,
                "timestamp": datetime.now().isoformat()
            }), 400
        
        if result and result.get('status') == 'success':
            processing_time = time.time() - start_time
            
            response_data = {
                "status": "success",
                "timestamp": datetime.now().isoformat(),
                "processing_time": f"{processing_time:.2f}s",
                "count": result.get('count', 0),
                "statistics": result.get('statistics', {}),
                "recommendations": result.get('recommendations', [])
            }
            
            print(f"✅ Recomendaciones generadas: {len(response_data['recommendations'])} animes")
            return jsonify(response_data)
        else:
            error_msg = result.get('message', 'Error desconocido en el pipeline') if result else error
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
def get_status():
    """Endpoint para verificar estado del servicio"""
    return jsonify({
        "status": "running",
        "timestamp": datetime.now().isoformat()
    })

@app.route('/')
def home():
    """Página de inicio"""
    return jsonify({
        "message": "Anime Recommendation API",
        "version": "2.0",
        "description": "Ejecuta pipeline completo de recomendación",
        "endpoints": {
            "health": "/api/health",
            "status": "/api/status", 
            "recommendations": "/api/recommendations/<username>"
        }
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"🚀 Iniciando servidor en puerto {port}")
    print(f"📁 Root directory: {ROOT_DIR}")
    app.run(host='0.0.0.0', port=port, debug=False)