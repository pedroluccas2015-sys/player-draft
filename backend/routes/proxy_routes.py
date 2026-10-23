from flask import Blueprint
from config import SESSION, HEADERS, cache
from services.portraits import athlete_portrait

proxy_bp = Blueprint('proxy_routes', __name__)

@proxy_bp.route('/proxy-image/<int:player_id>')
def proxy_image(player_id):
    result = athlete_portrait(player_id)
    if result is None:
        return 'Not Found', 404, {'Cache-Control': 'no-store'}
    body, content_type = result
    return body, 200, {'Content-Type': content_type, 'Cache-Control': 'public, max-age=3600'}

@proxy_bp.route('/proxy-tournament/<int:t_id>')
def proxy_tournament(t_id):
    key=f'tournament_badge_v2_{t_id}'
    stored=cache.get(key)
    if stored:
        return stored[0],200,{'Content-Type':stored[1],'Cache-Control':'public, max-age=21600'}
    # The normal logo sits on a light tile in the dossier; preserve its real MIME type.
    for suffix in ['image','image/dark']:
        try:
            response=SESSION.get(f'https://api.sofascore.com/api/v1/unique-tournament/{t_id}/{suffix}',headers=HEADERS,timeout=10)
            mime=response.headers.get('Content-Type','').split(';')[0]
            if response.status_code==200 and mime in ['image/png','image/jpeg','image/webp','image/avif','image/svg+xml'] and len(response.content)>100:
                cache.set(key,(response.content,mime),expire=21600)
                return response.content,200,{'Content-Type':mime,'Cache-Control':'public, max-age=21600'}
        except Exception:
            continue
    return 'Not Found',404,{'Cache-Control':'no-store'}

@proxy_bp.route('/proxy-team/<int:team_id>')
def proxy_team(team_id):
    url = f"https://api.sofascore.com/api/v1/team/{team_id}/image"
    try:
        img_res = SESSION.get(url, headers=HEADERS)
        if img_res.status_code == 200:
            return (img_res.content, 200, {'Content-Type': 'image/png', 'Cache-Control': 'public, max-age=864000'})
        return "Not Found", 404
    except Exception:
        return "Not Found", 404
