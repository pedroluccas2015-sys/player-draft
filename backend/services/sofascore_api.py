import time
import pandas as pd
from concurrent.futures import ThreadPoolExecutor

# Puxa a sessão global que configuramos antes
from config import SESSION, HEADERS, cache

def fetch_single_tournament_stats(player_id, t_id, s_id, year_label, t_name, retries=3):
    """Busca estatística de um torneio com sistema de Retry para evitar Error 429 e Timeouts"""
    cache_key = f"club_tournament_v2_{player_id}_{t_id}_{s_id}"
    cached = cache.get(cache_key)
    if cached is not None: return cached
    url = f"https://api.sofascore.com/api/v1/player/{player_id}/unique-tournament/{t_id}/season/{s_id}/statistics/overall"

    for attempt in range(retries):
        try:
            res = SESSION.get(url, headers=HEADERS, timeout=15)
            
            if res.status_code == 200:
                json_data = res.json()
                stats = json_data.get('statistics', {})
                
                team_data = json_data.get('team', {})
                team_id = team_data.get('id', 0)
                team_name = team_data.get('name', 'Clube não informado')
                is_national = team_data.get('national', False)
            
            if res.status_code == 200:
                stats = res.json().get('statistics', {})
                if stats:
                    def seguro(chave1, chave2=None, chave3=None):
                        val = stats.get(chave1)
                        if val is None and chave2: val = stats.get(chave2)
                        if val is None and chave3: val = stats.get(chave3)
                        return float(val) if val is not None else 0.0

                    duels_perc = seguro('duelsWonPercentage')
                    if duels_perc == 0:
                        dw = seguro('duelsWon', 'duelWon', 'groundDuelsWon')
                        dl = seguro('duelsLost', 'duelLost', 'groundDuelsLost')
                        if (dw + dl) > 0: duels_perc = (dw / (dw + dl)) * 100
                            
                    aerial_perc = seguro('aerialDuelsWonPercentage')
                    if aerial_perc == 0:
                        aw = seguro('aerialDuelsWon', 'aerialWon')
                        al = seguro('aerialDuelsLost', 'aerialLost')
                        if (aw + al) > 0: aerial_perc = (aw / (aw + al)) * 100

                    result = {
                        'season': year_label,
                        'season_id': s_id,
                        'tournament': t_name,
                        'tournament_id': t_id,
                        'team_id': team_id,     
                        'team_name': team_name, 
                        'is_national': is_national,
                        'goals': seguro('goals'),
                        'assists': seguro('assists'),
                        'games': seguro('appearances'),
                        'minutes': seguro('minutesPlayed'),
                        'rating': seguro('rating') or None,
                        'tackles': seguro('tackles'),
                        'interceptions': seguro('interceptions'),
                        'clearances': seguro('clearances'),
                        'pass_comp': seguro('accuratePassesPercentage'),
                        'key_passes': seguro('keyPasses'),
                        'crosses': seguro('accurateCrosses'),
                        'duels': duels_perc,     
                        'aerial': aerial_perc,   
                        'fouls': seguro('fouls'),

                        'saves': seguro('saves'),
                        'clean_sheets': seguro('cleanSheet', 'cleanSheets'),
                        'goals_conceded': seguro('goalsConceded'),
                        'penalty_saves': seguro('penaltySaves')
                    }
                    cache.set(cache_key, result, expire=900)
                    return result
                return None 

            elif res.status_code == 429:
                time.sleep(2 * (attempt + 1))
                continue
            else:
                break
        except Exception as e:
            if attempt == retries - 1:
                print(f" Desistindo do Torneio {t_id} após {retries} tentativas. (Provável bloqueio do Sofascore)")
            else:
                print(f"⏳ Timeout no Torneio {t_id} (Tentativa {attempt + 1}/{retries}). A recuperar o fôlego...")
                time.sleep(2.5) 
            continue
       
    return None

def fetch_stats_parallel(player_id):
    """Busca estatísticas usando múltiplas 'threads' em paralelo"""
    all_stats = []
    url_seasons = f"https://api.sofascore.com/api/v1/player/{player_id}/statistics/seasons"
    
    try:
        response = SESSION.get(url_seasons, headers=HEADERS, timeout=10)
        if response.status_code != 200: return pd.DataFrame()
        tournaments = response.json().get('uniqueTournamentSeasons', [])

        tasks = []
        for tourn in tournaments:
            t_id = tourn['uniqueTournament']['id']
            t_name = tourn['uniqueTournament'].get('name', 'Desconhecido')
            if any(n in t_name.lower() for n in ['nations league', 'european championship', 'copa américa', 'copa america', 'world championship', 'world cup qualification', 'international friendly', 'friendlies', 'africa cup', 'asian cup', 'gold cup']) or (t_name.lower() == 'world cup'):
                continue

            for season in tourn['seasons']:
                year_str = season['year']

                if '/' in year_str:
                    ano_final = year_str.split('/')[-1].strip()
                    if len(ano_final) == 4:
                        ano_final = ano_final[2:]
                elif year_str.isdigit():
                    ano_final = year_str[-2:] if len(year_str) == 4 else year_str
                else:
                    continue  

                if ano_final.isdigit() and int(ano_final) >= (__import__('datetime').datetime.now().year - 6) % 100:
                    tasks.append((player_id, t_id, season['id'], season['year'], t_name))

        with ThreadPoolExecutor(max_workers=3) as executor:
            results = list(executor.map(lambda p: fetch_single_tournament_stats(*p), tasks))
      
        all_stats = [r for r in results if r is not None]
        falhas = results.count(None)

        if falhas > 0:
            print(f" AVISO: {falhas} torneios falharam ao carregar (Cloudflare/Timeout). Os dados podem estar incompletos.")
    
    except Exception as e:
        print(f"Erro no paralelismo: {e}")
   
    frame = pd.DataFrame(all_stats)
    frame.attrs['failures'] = falhas if 'falhas' in locals() else 0
    return frame