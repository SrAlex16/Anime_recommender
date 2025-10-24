from flask import Blueprint, request, jsonify

# Creamos un blueprint para separar la lógica
blacklist_bp = Blueprint("blacklist", __name__, url_prefix="/api/blacklist")

# Lista simulada de IDs bloqueados (puede reemplazarse con DB)
blocked_animes = set()

@blacklist_bp.route("", methods=["POST"])
def add_to_blacklist():
    data = request.get_json()
    if not data or "anime_ids" not in data:
        return jsonify({"error": "anime_ids es requerido"}), 400

    try:
        anime_ids = set(data["anime_ids"])
        blocked_animes.update(anime_ids)
        return jsonify({"status": "success", "blocked_animes": list(blocked_animes)}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@blacklist_bp.route("", methods=["GET"])
def get_blacklist():
    return jsonify({"blocked_animes": list(blocked_animes)}), 200
