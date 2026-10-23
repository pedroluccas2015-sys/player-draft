from pathlib import Path
from bootstrap import initialize

initialize()
from diskcache import Cache
from curl_cffi import requests

# Stable paths regardless of the working directory used to start Flask.
cache = Cache(str(Path(__file__).resolve().parent / 'scout_cache'))
SESSION = requests.Session(timeout=15)
HEADERS = {"Accept": "application/json", "User-Agent": "PlayerDraft/1.0"}
