from contextlib import closing
"""Club scouting: independent provider identities and explicit missing-data states."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from urllib.parse import quote
from flask import Blueprint, jsonify, request
from config import SESSION, HEADERS, cache
from services import market, league_catalog
from services.sofascore_api import fetch_stats_parallel

club_bp = Blueprint('club_scout', __name__)
API = 'https://api.sofascore.com/api/v1'


def sofa(path):
    response = SESSION.get(API + path, headers=HEADERS, timeout=15)
    if response.status_code != 200:
        raise ConnectionError(f'Sofascore indisponível (HTTP {response.status_code}). Tente novamente mais tarde.')
    return response.json()


def player_age(timestamp):
    if not timestamp:
        return None
    dob = datetime.fromtimestamp(timestamp, timezone.utc).date()
    today = datetime.now(timezone.utc).date()
    return today.year-dob.year-((today.month, today.day)<(dob.month, dob.day))


@club_bp.get('/api/scouting/options')
def options():
    try:
        with closing(market.connect()) as db:
            positions = [r[0] for r in db.execute('SELECT DISTINCT sub_position FROM players WHERE sub_position IS NOT NULL ORDER BY sub_position')]
        return jsonify(metadata=league_catalog.metadata(market.metadata()), positions=positions)
    except FileNotFoundError as e:
        return jsonify(error=str(e)), 503


@club_bp.get('/api/scouting/search')
def scouting_search():
    try:
        return jsonify(league_catalog.search(request.args))
    except (ValueError, TypeError) as e:
        return jsonify(error=str(e)), 400
    except FileNotFoundError as e:
        return jsonify(error=str(e)), 503


@club_bp.get('/api/market/player/<int:player_id>')
def market_profile(player_id):
    try:
        result = market.profile(player_id)
        return (jsonify(result), 200) if result else (jsonify(error='Atleta fora da cobertura de mercado.'), 404)
    except FileNotFoundError as e:
        return jsonify(error=str(e)), 503


@club_bp.get('/api/search/suggestions')
def suggestions():
    query = request.args.get('q', '').strip()
    if len(query)<3:
        return jsonify([])
    try:
        data = sofa('/search/all?q=' + quote(query))
        rows=[]
        for item in data.get('results', []):
            p=item.get('entity', {})
            sport=p.get('sport') or p.get('team', {}).get('sport', {})
            if item.get('type')=='player' and sport.get('slug')=='football':
                rows.append(dict(id=p['id'], name=p['name'], team=p.get('team', {}).get('name'), photo=f"/proxy-image/{p['id']}?v=club-v2"))
        return jsonify(rows[:8])
    except Exception as e:
        return jsonify(error=str(e)), 502


def resolve_player(name, dob=None):
    results=sofa('/search/all?q='+quote(name)).get('results', [])
    candidates=[r['entity'] for r in results if r.get('type')=='player' and (r.get('entity', {}).get('sport') or r.get('entity', {}).get('team', {}).get('sport', {})).get('slug')=='football']
    verified=[]
    for candidate in candidates[:5]:
        p=sofa(f"/player/{candidate['id']}").get('player', {})
        birth=datetime.fromtimestamp(p['dateOfBirthTimestamp'], timezone.utc).date().isoformat() if p.get('dateOfBirthTimestamp') else None
        if dob and dob==birth:
            verified.append(p)
        elif not dob and market.normalize(name) in [market.normalize(p.get('name')),market.normalize(p.get('shortName'))]:
            verified.append(p)
    return verified[0] if len(verified)==1 else None


def aggregate_attributes(frame):
    minutes=float(frame['minutes'].sum()) if not frame.empty else 0
    result={}
    for label,col in [('Desarmes p/90','tackles'),('Intercepções p/90','interceptions'),('Cortes p/90','clearances'),('Passes chave p/90','key_passes'),('Defesas p/90','saves')]:
        result[label]=round(float(frame[col].sum())/minutes*90,2) if minutes else None
    for label,col in [('Passes certos %','pass_comp'),('Duelos ganhos %','duels'),('Duelos aéreos %','aerial')]:
        valid=frame[(frame[col]>0)&(frame['minutes']>0)]
        result[label]=round(float((valid[col]*valid['minutes']).sum()/valid['minutes'].sum()),1) if not valid.empty else None
    return result


def build_dossier(p):
    key=f"club_dossier_v5_{p['id']}"
    cached=cache.get(key)
    if cached:
        return cached
    df=fetch_stats_parallel(p['id'])
    stats=[]
    if not df.empty:
        df=df[~df['is_national'].fillna(False)].copy()
        for season,group in df.groupby('season', sort=False):
            valid=group[(group['rating'].notna())&(group['games']>0)]
            rating=round(float((valid.rating*valid.games).sum()/valid.games.sum()),2) if not valid.empty else None
            tournaments=[]
            for _,r in group.iterrows():
                tournaments.append(dict(name=r.tournament,tournament_id=int(r.tournament_id),season_id=int(r.season_id),logo=f'/proxy-tournament/{int(r.tournament_id)}?v=badge-v2',matches=int(r.games),goals=int(r.goals),assists=int(r.assists),minutes=int(r.minutes),rating=float(r.rating) if r.rating==r.rating else None,is_national=False))
            teams={int(r.team_id):r.team_name for _,r in group.iterrows() if r.team_id}
            stats.append(dict(season=str(season), matches=int(group.games.sum()),goals=int(group.goals.sum()),assists=int(group.assists.sum()),minutes=int(group.minutes.sum()),rating=rating,attributes=aggregate_attributes(group),tournaments=tournaments,teams=[dict(id=i,name=n,logo=f'/proxy-team/{i}') for i,n in teams.items()]))
        def season_year(s):
            last=s['season'].split('/')[-1]
            return int(last) if last.isdigit() and len(last)==4 else 2000+int(last) if last.isdigit() else 0
        stats.sort(key=season_year,reverse=True)
    dob=datetime.fromtimestamp(p['dateOfBirthTimestamp'],timezone.utc).date().isoformat() if p.get('dateOfBirthTimestamp') else None
    result=dict(id=p['id'],sofa_id=p['id'],name=p['name'],club=p.get('team',{}).get('name'),nationality=p.get('country',{}).get('name'),position={'G':'GOL','D':'DEF','M':'MEI','F':'ATA'}.get(p.get('position'),'—'),age=player_age(p.get('dateOfBirthTimestamp')),date_of_birth=dob,height=p.get('height'),foot=p.get('preferredFoot'),photo=f"/proxy-image/{p['id']}?v=club-v2",rating=stats[0]['rating'] if stats else None,attributes=aggregate_attributes(df) if not df.empty else {},stats=stats,is_injured=bool(p.get('injured')),statistics_source='Sofascore',statistics_updated_at=datetime.now(timezone.utc).isoformat(),statistics_status='available' if stats else 'unavailable',statistics_partial=bool(df.attrs.get('failures')),statistics_failures=df.attrs.get('failures',0),is_full_profile=True)
    cache.set(key,result,expire=900)
    return result


@club_bp.post('/api/search')
def player_search():
    data=request.get_json(silent=True) or {}
    tm=None
    try:
        if data.get('tm_id'):
            tm=market.profile(int(data['tm_id']))
            if not tm:
                return jsonify(error='Atleta fora da cobertura Transfermarkt.'),404
        if data.get('player_id'):
            player_id=int(data['player_id'])
            p=sofa(f'/player/{player_id}').get('player')
        else:
            name=tm['name'] if tm else str(data.get('player_name','')).strip()
            if not name:
                return jsonify(error='Informe o nome do jogador.'),400
            p=resolve_player(name,tm.get('date_of_birth') if tm else None)
        if not p:
            if tm:
                return jsonify(**tm,stats=[],attributes={},statistics_status='unmatched',statistics_source='Sofascore',is_full_profile=True,statistics_notice='Não foi possível confirmar a identidade no Sofascore. Dados de mercado preservados; estatísticas não associadas por aproximação.')
            return jsonify(error='Jogador não identificado de forma única. Selecione um resultado da busca.'),404
        result=build_dossier(p).copy()
        if data.get('league_id') and not any(t['tournament_id']==int(data['league_id']) for s in result['stats'] for t in s['tournaments']):
            result['statistics_coverage_notice']=f"A fonte não publicou estatísticas de {data.get('league_name') or 'esta liga'} para este atleta no período carregado. Abaixo estão apenas as competições com dados disponíveis."
        if not tm:
            tm=market.match_player(p['name'],result.get('date_of_birth'))
        if tm:
            for key in ['tm_id','market_value_eur','snapshot_date','market_url','transfers','transfer_source','transfer_snapshot_date','contract_until','position_detail']:
                result[key]=tm.get(key)
            result['market_status']='snapshot'
            result['market_value_source']='Transfermarkt'
            result['photo_fallback']=tm.get('photo')
        else:
            raw=p.get('proposedMarketValueRaw') or {}
            value=raw.get('value') if raw.get('currency')=='EUR' else None
            result.update(market_status='unmatched',market_value_eur=value,market_value_source='Sofascore' if value is not None else None,transfers=None,market_notice='Sem correspondência confirmada no Transfermarkt. A estimativa de valor, quando disponível, é fornecida pelo Sofascore; histórico de transferências indisponível.')
            if p.get('contractUntilTimestamp'):
                result['contract_until']=datetime.fromtimestamp(p['contractUntilTimestamp'],timezone.utc).date().isoformat()
        return jsonify(result)
    except (ValueError,TypeError):
        return jsonify(error='Identificador de jogador inválido.'),400
    except FileNotFoundError as e:
        return jsonify(error=str(e)),503
    except Exception as e:
        if tm:
            return jsonify(**tm, stats=[], attributes={}, statistics_status='unavailable', statistics_source='Sofascore', is_full_profile=True, statistics_notice=str(e))
        return jsonify(error=str(e)),502


@club_bp.get('/api/clubs/search')
def club_search():
    q=request.args.get('q','').strip()
    if len(q)<2:
        return jsonify([])
    try:
        rows=sofa('/search/all?q='+quote(q)).get('results',[])
        return jsonify([r['entity'] for r in rows if r.get('type')=='team' and not r['entity'].get('national') and r['entity'].get('sport',{}).get('slug')=='football'][:8])
    except Exception as e:
        return jsonify(error=str(e)),502


@club_bp.get('/api/player/<int:player_id>/ratings')
def season_ratings(player_id):
    try:
        pairs = request.args.get('tournaments', '').split(',')[:20]
        pairs = [tuple(int(n) for n in p.split(':')) for p in pairs if p]
        if not pairs or any(len(p) != 2 or min(p) <= 0 for p in pairs):
            return jsonify(error='Informe os torneios e temporadas do dossiê.'),400
        def fetch_pair(pair):
            t, s = pair
            key=f'club_ratings_{player_id}_{t}_{s}'
            data=cache.get(key)
            if data is None:
                data=sofa(f'/player/{player_id}/unique-tournament/{t}/season/{s}/ratings').get('seasonRatings',[])
                cache.set(key,data,expire=900)
            return data
        records,failures={},0
        with ThreadPoolExecutor(max_workers=3) as pool:
            tasks=[pool.submit(fetch_pair,p) for p in pairs]
            for task in tasks:
                try:
                    for r in task.result():
                        if r.get('rating') is not None and not r.get('opponent',{}).get('national'):
                            records[r['eventId']]=dict(event_id=r['eventId'],timestamp=r.get('startTimestamp') or r.get('event',{}).get('startTimestamp'),rating=r['rating'],opponent=r.get('opponent',{}).get('name'))
                except Exception:
                    failures+=1
        return jsonify(ratings=sorted(records.values(),key=lambda r:r['timestamp'] or 0),partial=failures>0,failures=failures)
    except ValueError:
        return jsonify(error='Torneio ou temporada inválidos.'),400
