from pathlib import Path
from flask import Flask, send_from_directory, jsonify

from routes.team_routes import team_bp
from routes.club_routes import club_bp
from routes.player_routes import player_bp
from routes.proxy_routes import proxy_bp
from routes.ranking_routes import ranking_bp


FRONTEND_DIST = Path(__file__).resolve().parents[1] / 'frontend' / 'dist'
app = Flask(__name__, static_folder=str(FRONTEND_DIST / 'assets'), static_url_path='/assets')

app.register_blueprint(team_bp)
app.register_blueprint(club_bp)
app.register_blueprint(player_bp)
app.register_blueprint(proxy_bp)
app.register_blueprint(ranking_bp)


@app.route('/')
@app.route('/<path:path>')
def index(path='index.html'):
    if path.startswith(('api/', 'proxy-')):
        return jsonify(error='Rota não encontrada'), 404
    if not (FRONTEND_DIST / 'index.html').is_file():
        return jsonify(error='Interface não compilada. Execute npm install e npm run build em frontend.'), 503
    if (FRONTEND_DIST / path).is_file():
        return send_from_directory(FRONTEND_DIST, path)
    return send_from_directory(FRONTEND_DIST, 'index.html')

if __name__ == '__main__':
    app.run(debug=False, host="127.0.0.1", port=5000)
