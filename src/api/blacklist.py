# src/api/blacklist.py

from flask import Blueprint, request, jsonify
import os
import json
from threading import Lock # Para manejo de concurrencia al escribir/leer el archivo

# Configuración de Paths
# CRÍTICO: Asegúrate de que esta ruta apunte al directorio 'data' en la raíz.
# El archivo .py está en src/api/, subimos dos niveles para ir a la raíz y luego a data.
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(ROOT_DIR, "data")
BLACKLIST_FILE = os.path.join(DATA_DIR, "runtime_blacklist.json") # Nuevo archivo
os.makedirs(DATA_DIR, exist_ok=True)

# Usar un Lock para evitar que dos workers escriban el archivo a la vez.
file_lock = Lock()

# Creamos un blueprint para separar la lógica
blacklist_bp = Blueprint("blacklist", __name__, url_prefix="/api/blacklist")

# --- FUNCIONES DE PERSISTENCIA ---

def load_blacklist():
    """Carga la blacklist desde el archivo JSON."""
    with file_lock:
        if not os.path.exists(BLACKLIST_FILE):
            return set()
        try:
            with open(BLACKLIST_FILE, 'r', encoding='utf-8') as f:
                # El archivo debe contener una lista de IDs
                return set(json.load(f))
        except Exception:
            # Si el archivo está corrupto o vacío, retorna un set vacío
            return set()

def save_blacklist(blocked_ids):
    """Guarda la blacklist en el archivo JSON."""
    with file_lock:
        try:
            # Convertir el set a una lista para guardar en JSON
            with open(BLACKLIST_FILE, 'w', encoding='utf-8') as f:
                json.dump(list(blocked_ids), f)
        except Exception as e:
            # Si el guardado falla, al menos la app no cae con un 503
            print(f"❌ Error al guardar la blacklist: {e}")
            pass

@blacklist_bp.route("", methods=["POST"])
def add_to_blacklist():
    # 💡 La lista de IDs ya no es global, se carga al inicio
    blocked_animes = load_blacklist() 
    
    data = request.get_json()
    if not data or "anime_ids" not in data:
        return jsonify({"error": "anime_ids es requerido"}), 400

    try:
        # Asegurarse de que los IDs sean enteros antes de añadirlos al set
        # Vienen como strings del front-end, convertirlos es CRÍTICO.
        anime_ids = set(map(int, data["anime_ids"])) 
        blocked_animes.update(anime_ids)
        
        # 💡 Guardar la nueva lista
        save_blacklist(blocked_animes) 
        
        return jsonify({"status": "success", "blocked_animes": list(blocked_animes)}), 200
    except Exception as e:
        # En caso de error (e.g., IDs no son números), retorna 500
        return jsonify({"error": str(e)}), 500

@blacklist_bp.route("", methods=["GET"])
def get_blacklist():
    blocked_animes = load_blacklist()
    return jsonify({"blocked_animes": list(blocked_animes)}), 200

def get_blacklist_last_modified_time():
    """Retorna el timestamp (tiempo de última modificación) del archivo de blacklist."""
    # Retorna 0.0 si el archivo aún no existe.
    if os.path.exists(BLACKLIST_FILE):
        # Usamos os.path.getmtime que retorna el timestamp UNIX
        return os.path.getmtime(BLACKLIST_FILE)
    # Si el archivo no existe (no hay blacklist), la clave de caché es constante.
    return 0.0