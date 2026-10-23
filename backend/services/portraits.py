"""Resolve list portraits without building or opening a player dossier."""
from datetime import datetime, timezone
from urllib.parse import urlparse
from config import SESSION, HEADERS, cache
from services import market


def valid_image(response):
    content_type = response.headers.get('Content-Type', '').split(';')[0]
    return response.status_code == 200 and len(response.content) > 100 and content_type in {'image/png', 'image/jpeg', 'image/webp', 'image/avif'}


def athlete_portrait(player_id):
    key = f'athlete_portrait_v1_{player_id}'
    cached = cache.get(key)
    if cached is not None:
        return cached
    try:
        response = SESSION.get(f'https://api.sofascore.com/api/v1/player/{player_id}/image', headers=HEADERS, timeout=8)
        if valid_image(response):
            result = (response.content, response.headers['Content-Type'])
            cache.set(key, result, expire=3600)
            return result
    except Exception:
        pass
    try:
        # A small identity lookup only: no statistics, tournament requests, or dossier.
        response = SESSION.get(f'https://api.sofascore.com/api/v1/player/{player_id}', headers=HEADERS, timeout=8)
        response.raise_for_status()
        player = response.json().get('player', {})
        timestamp = player.get('dateOfBirthTimestamp')
        if not timestamp:
            return None
        dob = datetime.fromtimestamp(timestamp, timezone.utc).date().isoformat()
        match = market.match_player(player.get('name'), dob)
        url = match.get('photo') if match else None
        if not url or urlparse(url).scheme != 'https' or urlparse(url).hostname != 'img.a.transfermarkt.technology':
            return None
        response = SESSION.get(url, timeout=8)
        if valid_image(response):
            result = (response.content, response.headers['Content-Type'])
            cache.set(key, result, expire=3600)
            return result
    except Exception:
        pass
    return None
