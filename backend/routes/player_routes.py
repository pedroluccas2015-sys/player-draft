from flask import Blueprint, jsonify
from config import SESSION, HEADERS

player_bp = Blueprint('player_routes', __name__)

@player_bp.route('/api/heatmap/<int:player_id>/<int:t_id>/<int:s_id>')
def api_heatmap(player_id, t_id, s_id):
    url = f"https://api.sofascore.com/api/v1/player/{player_id}/unique-tournament/{t_id}/season/{s_id}/heatmap/overall"
    try:
        res = SESSION.get(url, headers=HEADERS)
        if res.status_code == 200:
            return jsonify(res.json())
        return jsonify({"error": "Not Found", "heatmap": []}), 404
    except Exception as e:
        return jsonify({"error": str(e), "heatmap": []}), 500

