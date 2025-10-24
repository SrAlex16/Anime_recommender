# src/api/app.py
from flask import Flask, request, jsonify
from flask_cors import CORS
import subprocess
import sys
import os
import json
from datetime import datetime
import traceback

# CRÍTICO: Configurar paths - Sube 3 niveles: src/api/ -> src/ -> ROOT_DIR
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT_DIR)

# Directorios a verificar en el health check
DIRS_TO_CHECK = [
    'data',
    'src/data',
    'src/model',
    'src/services',
    'src/api'
]

def create_app():
    """Crea y configura la instancia de la aplicación Flask."""
    app = Flask(__name__)
    CORS(app) # Habilitar CORS para permitir llamadas desde el frontend

    def debug_log(message):
        """Función de logging para debug - FORZAR FLUSH"""
        print(f"🔍 [DEBUG - API] {message}", file=sys.stderr, flush=True)

    def run_pipeline(username):
        """Ejecutar el pipeline completo de recomendación"""
        try:
            debug_log(f"🚀 Iniciando pipeline para usuario: {username}")
            
            # Ruta al script principal que orquesta el proceso
            script_path = os.path.join(ROOT_DIR, 'src', 'services', 'get_recommendations_for_user.py')
            
            debug_log(f"📁 Script path: {script_path}")
            debug_log(f"📁 Working dir: {ROOT_DIR}")
            
            # Verificar si el script existe
            if not os.path.exists(script_path):
                debug_log(f"❌ Script no encontrado: {script_path}")
                return None, f"Script no encontrado: {script_path}"
            
            # FORZAR ENCODING UTF-8 para manejo de subprocesos en entornos de servidor
            env = os.environ.copy()
            env['PYTHONIOENCODING'] = 'utf-8'
            env['PYTHONUTF8'] = '1'
            
            # Ejecutar el script como subproceso con el nombre de usuario
            result = subprocess.run([
                sys.executable, '-u', script_path, username
            ], capture_output=True, text=True, cwd=ROOT_DIR, env=env, timeout=360) # Timeout de 6 minutos (360s)
            
            # 🔥 CRÍTICO: El script de servicio imprime el resultado JSON final en stdout.
            # No usar STDOUT para logging, solo STDERR.
            
            if result.returncode != 0:
                error_message = f"El script finalizó con código de error {result.returncode}."
                debug_log(f"❌ {error_message} STDERR: {result.stderr}")
                
                # Intentar parsear el error si el script lo imprimió en stdout
                try:
                    error_data = json.loads(result.stdout.strip())
                    if error_data.get('status') == 'error':
                        return None, error_data.get('message', error_message)
                except json.JSONDecodeError:
                    pass
                
                # Si no se pudo obtener un error específico, usar el stderr
                return None, f"{error_message} Detalles: {result.stderr.strip()[:200]}"


            # Intentar decodificar el JSON de la salida estándar
            try:
                # El resultado JSON es la única cosa que debe estar en result.stdout
                response_json = json.loads(result.stdout.strip())
                debug_log("✅ Pipeline ejecutado exitosamente.")
                return response_json, None
            except json.JSONDecodeError as e:
                debug_log(f"❌ Error al decodificar JSON de la salida. STDERR: {result.stderr}. STDOUT: {result.stdout}")
                return None, f"Error interno del servidor: No se pudo procesar la respuesta del pipeline. Detalles: {str(e)}"

        except subprocess.TimeoutExpired:
            error_msg = "Timeout: El pipeline tardó demasiado en ejecutarse (> 6 minutos)."
            debug_log(f"❌ {error_msg}")
            return None, error_msg
        except Exception as e:
            error_msg = f"Error grave al ejecutar el subproceso: {str(e)}"
            debug_log(f"❌ {error_msg} Traceback: {traceback.format_exc()}")
            return None, error_msg

    # --- ENDPOINTS ---

    @app.route('/api/recommendations/<username>', methods=['GET'])
    def get_recommendations(username):
        """Endpoint para obtener las recomendaciones de anime para un usuario."""
        username = username.strip()
        if not username:
            return jsonify({
                "status": "error",
                "message": "El nombre de usuario no puede estar vacío.",
                "timestamp": datetime.now().isoformat()
            }), 400

        # El pipeline devuelve un dict o None, y un error_msg o None
        result, error = run_pipeline(username)

        if error:
            # Si hay un error, el código de estado HTTP será 500
            return jsonify({
                "status": "error",
                "message": error,
                "timestamp": datetime.now().isoformat()
            }), 500
        
        # Si no hay error, el resultado debe ser el JSON completo (incluyendo status: success)
        if result:
            return jsonify(result), 200
        else:
            # Fallback si result es None pero error es None (no debería pasar)
            return jsonify({
                "status": "error",
                "message": "Error desconocido al generar recomendaciones.",
                "timestamp": datetime.now().isoformat()
            }), 500

    @app.route('/api/health', methods=['GET'])
    def health_check():
        """Endpoint para verificar la salud y la configuración de la API."""
        try:
            # Verificar si los directorios clave existen
            for dir_path in DIRS_TO_CHECK:
                if not os.path.exists(os.path.join(ROOT_DIR, dir_path)):
                    return jsonify({
                        "status": "error", 
                        "message": f"Directorio clave no encontrado: {dir_path}",
                        "timestamp": datetime.now().isoformat()
                    }), 500
                    
            return jsonify({
                "status": "healthy", 
                "timestamp": datetime.now().isoformat(),
                "python_version": sys.version
            })
        except Exception as e:
            debug_log(f"❌ Error en health_check: {str(e)}")
            return jsonify({
                "status": "error",
                "message": str(e),
                "timestamp": datetime.now().isoformat()
            }), 500

    @app.route('/')
    def home():
        """Página de inicio (ruta raíz)"""
        return jsonify({
            "message": "Anime Recommendation API",
            "version": "2.0",
            "description": "Sistema de recomendación de anime basado en contenido (Content-Based Filtering)",
            "endpoints": {
                "health": "/api/health",
                "recommendations": "/api/recommendations/<username>"
            },
            "example": "https://anime-recommender-1-x854.onrender.com/api/recommendations/SrAlex16"
        })

    return app

# 🔥 CRÍTICO: Crear la instancia de app
app = create_app()

if __name__ == '__main__':
    # Usar el puerto proporcionado por el entorno, o 5000 por defecto
    port = int(os.environ.get('PORT', 5000))
    print(f"🚀 Iniciando servidor en puerto {port}")
    # Nota: En un entorno de producción como Render, se usa Gunicorn o similar.
    # Esta parte es para ejecución local o un simple entorno de desarrollo.
    app.run(host='0.0.0.0', port=port, debug=True)
