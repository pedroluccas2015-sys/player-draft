from concurrent.futures import ThreadPoolExecutor
from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta, timezone
from urllib.parse import quote
from config import cache, SESSION, HEADERS

team_bp = Blueprint('team_routes', __name__)

@team_bp.route('/api/scoreboard', methods=['GET'])
def api_scoreboard():
    league = request.args.get('league', 'bra.1')
    if league not in ['bra.1','eng.1','ita.1','esp.1','ger.1','fra.1','por.1','uefa.champions','conmebol.libertadores','conmebol.sudamericana','usa.1']:
        return jsonify(error='Liga inválida.'),400
    
    cache_key = f"scoreboard_v4_{league}"
    cached_data = cache.get(cache_key)
    if cached_data is not None:
        print(f" Retornando Placar do cache para: {league}")
        return jsonify(cached_data)

    hoje = datetime.now()
    dias_atras = hoje - timedelta(days=45)
    dias_frente = hoje + timedelta(days=10) 
    
    data_inicio = dias_atras.strftime('%Y%m%d')
    data_fim = dias_frente.strftime('%Y%m%d')

    url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{league}/scoreboard?limit=100&dates={data_inicio}-{data_fim}"
    
    try:
        # ESPN accepts calendar months; date ranges return HTTP 400.
        def get_month(offset):
            year = hoje.year + (hoje.month - 1 + offset) // 12
            month = (hoje.month - 1 + offset) % 12 + 1
            res = SESSION.get(f"https://site.api.espn.com/apis/site/v2/sports/soccer/{league}/scoreboard?limit=1000&dates={year}{month:02d}", timeout=15)
            res.raise_for_status()
            return res.json().get('events', [])
        with ThreadPoolExecutor(max_workers=3) as pool:
            months = list(pool.map(get_month, [-1, 0, 1]))
        events_by_id = {event['id']: event for month in months for event in month}
        if True:
            data = {'events': list(events_by_id.values())}
            events = data.get('events', [])     
            
            past_and_live = []
            upcoming = []
            has_live_match = False
            
            #separação de jogos (ao vivo vs agendados)
            for e in events:
                status_type = e.get('status', {}).get('type', {})
                state = status_type.get('state', '')
                is_completed = status_type.get('completed', False)
                
                if state == 'in':
                    has_live_match = True
                    
                if is_completed or state in ['in', 'post']:
                    past_and_live.append(e)
                elif state == 'pre':
                    upcoming.append(e)
          
            past_and_live.sort(key=lambda x: x['date'], reverse=True)
            upcoming.sort(key=lambda x: x['date']) 
            
            last_6_matches = past_and_live[:6]
            next_6_matches = upcoming[:6]
            
            def parse_matches(event_list):
                parsed_list = []
                for event in event_list:
                    try:
                        competition = event['competitions'][0]
                        competitors = competition['competitors']
                        
                        home = next((c for c in competitors if c['homeAway'] == 'home'), None)
                        away = next((c for c in competitors if c['homeAway'] == 'away'), None)
                     
                        details = competition.get('details', [])
                        home_scorers, away_scorers = [], []
                        home_red_cards, away_red_cards = [], [] # Novo array de expulsões
                    
                        for detail in details:
                            detail_text = detail.get('type', {}).get('text', '')
                            
                            is_scoring_play = detail.get('scoringPlay', False) or 'Goal' in detail_text
                            is_red_card = 'Red Card' in detail_text or detail.get('redCard', False)
                            
                            if is_scoring_play or is_red_card:
                                team_id = detail.get('team', {}).get('id')
                                clock = detail.get('clock', {}).get('displayValue', '')
                              
                                player_name = "Desconhecido"
                                if 'athletesInvolved' in detail and detail['athletesInvolved']:
                                    ath = detail['athletesInvolved'][0]
                                    player_name = ath.get('shortName') or ath.get('displayName') or "Desconhecido"
                                elif 'participants' in detail and detail['participants']:
                                    part = detail['participants'][0]
                                    ath = part.get('athlete', part) 
                                    player_name = ath.get('shortName') or ath.get('displayName') or "Desconhecido"
                               
                                if player_name == "Desconhecido" and 'text' in detail:
                                    text_split = detail['text'].split('-')
                                    if len(text_split) > 0:
                                        player_name = text_split[0].strip()
                                                                                        
                                event_info = {"name": player_name, "time": clock}
                                
                                if is_scoring_play:
                                    is_own_goal = 'Own' in detail_text
                                    event_info['is_own'] = is_own_goal
                                    if home and team_id == home['team']['id']:
                                        if is_own_goal: away_scorers.append(event_info)
                                        else: home_scorers.append(event_info)
                                    elif away and team_id == away['team']['id']:
                                        if is_own_goal: home_scorers.append(event_info)
                                        else: away_scorers.append(event_info)
                                        
                                elif is_red_card:
                                    if home and team_id == home['team']['id']:
                                        home_red_cards.append(event_info)
                                    elif away and team_id == away['team']['id']:
                                        away_red_cards.append(event_info)

                        status_desc = event['status']['type'].get('description', '')
                        is_completed = event['status']['type'].get('completed', False)
                        state = event['status']['type']['state']
                        
                        match_date_raw = event.get('date', '')
                        formatted_date = match_date_raw
                        if match_date_raw:
                            try:
                                dt_obj = datetime.fromisoformat(match_date_raw.replace("Z", "+00:00"))
                                dt_obj = dt_obj.astimezone(timezone(timedelta(hours=-3))) # Ajuste Fuso Brasil
                                formatted_date = dt_obj.strftime("%d/%m %H:%M")
                            except:
                                pass
                        
                        parsed_list.append({
                            'id': event['id'],
                            'date': formatted_date,
                            'status': status_desc,
                            'short_status': 'AGENDADO' if state == 'pre' else ('ENCERRADO' if is_completed else status_desc[:30]),
                            'home_team': home['team']['displayName'] if home else 'Casa',
                            'home_score': home['score'] if home else '0',
                            'home_logo': home['team'].get('logo', ''),
                            'home_scorers': home_scorers,
                            'home_red_cards': home_red_cards,
                            'away_team': away['team']['displayName'] if away else 'Visitante',
                            'away_score': away['score'] if away else '0',
                            'away_logo': away['team'].get('logo', ''),
                            'away_scorers': away_scorers,
                            'away_red_cards': away_red_cards
                        })
                    except Exception as parse_err:
                        print(f"Erro ao parsear um evento: {parse_err}")
                        continue
                return parsed_list

            
            final_response = {
                'league_name': data['leagues'][0]['name'] if data.get('leagues') else league, 
                'matches': parse_matches(last_6_matches),    
                'upcoming': parse_matches(next_6_matches)     
            }
            
            #ATRIBUIÇÃO DE CACHE DINÂMICO
            ttl_seconds = 30 if has_live_match else 3600
            cache.set(cache_key, final_response, expire=ttl_seconds)
            
            print(f" Placar salvo! Jogo ao vivo rolando? {'SIM (Cache 30s)' if has_live_match else 'NÃO (Cache 1 hora)'}")
            
            return jsonify(final_response)
            
    except Exception as e:
        print(f"Erro na API da ESPN: {e}")
        return jsonify({"error": "Falha ao buscar placares."}), 502
        
    return jsonify({"error": "Nenhum dado encontrado"}), 404


@team_bp.route('/api/team-squad', methods=['GET'])
def get_team_squad():
    team_id = request.args.get('id')
    team_name = request.args.get('name')
    
    # Fallback: Se o frontend enviou apenas o nome, descobrimos o ID real programaticamente
    if not team_id and team_name:
        from urllib.parse import quote
        url_busca = f"https://api.sofascore.com/api/v1/search/all?q={quote(team_name)}"
        try:
            res_b = SESSION.get(url_busca, headers=HEADERS)
            if res_b.status_code == 200:
                for r in res_b.json().get('results', []):
                    if r.get('type') == 'team' and not r.get('entity', {}).get('national') and r.get('entity', {}).get('sport', {}).get('slug') == 'football':
                        team_id = r['entity']['id']
                        break
        except Exception as e:
            print(f"Erro no fallback de busca de time: {e}")

    if not team_id:
        return jsonify({"error": "ID do clube não identificado."}), 400

    # Chamada oficial do Sofascore para obter os jogadores de um time usando o ID correto
    url_squad = f"https://api.sofascore.com/api/v1/team/{team_id}/players"
    try:
        res = SESSION.get(url_squad, headers=HEADERS, timeout=10)
        if res.status_code == 200:
            players_data = res.json().get('players', [])
            squad_list = []
            
            for item in players_data:
                p = item.get('player', {})
                squad_list.append({
                    "id": p.get('id'),
                    "name": p.get('name'),
                    "position": p.get('position', 'F')
                })
            return jsonify({"squad": squad_list})
    except Exception as e:
        print(f"Erro ao carregar jogadores do time {team_id}: {e}")
        
    return jsonify({"squad": []})