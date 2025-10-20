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
        
        script_path = os.path.join(ROOT_DIR, 'src', 'services', 'get_recommendations_for_user.py')
        
        result = subprocess.run([
            sys.executable, script_path, username
        ], capture_output=True, text=True, cwd=ROOT_DIR, timeout=300)
        
        print(f"📋 Script ejecutado. Return code: {result.returncode}")
        
        if result.returncode == 0:
            output = result.stdout.strip()
            return json.loads(output), None
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

# 🔥 CORRECCIÓN: Cambiar el nombre de la función del endpoint
@app.route('/api/recommendations/<username>', methods=['GET'])
def get_user_recommendations(username):  # 🔥 NOMBRE ÚNICO
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
def get_api_status():  # 🔥 NOMBRE ÚNICO
    """Endpoint para verificar estado del servicio"""
    return jsonify({
        "status": "running",
        "timestamp": datetime.now().isoformat()
    })

@app.route('/')
def home_page():  # 🔥 NOMBRE ÚNICO
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
    app.run(host='0.0.0.0', port=port)