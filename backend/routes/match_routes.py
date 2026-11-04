"""Match analysis joins providers by both clubs and kickoff, never by athlete name alone."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import math
from flask import Blueprint, jsonify
from config import SESSION, HEADERS, cache
from services import league_catalog, radar_identity

match_bp=Blueprint('match_analysis',__name__)
LEAGUES=set(radar_identity.COUNTRIES)|{'uefa.champions','conmebol.libertadores','conmebol.sudamericana'}
LABELS={'possessionPct':'Posse de bola (%)','totalShots':'Finalizações','shotsOnTarget':'No gol',
        'wonCorners':'Escanteios','foulsCommitted':'Faltas','yellowCards':'Cartões amarelos',
        'redCards':'Cartões vermelhos','offsides':'Impedimentos','saves':'Defesas',
        'accuratePasses':'Passes certos','totalPasses':'Passes','interceptions':'Interceptações',
        'totalTackles':'Desarmes disputados','goals':'Gols','goalAssists':'Assistências',
        'minutesPlayed':'Minutos','rating':'Nota','totalPass':'Passes','accuratePass':'Passes certos',
        'totalTackle':'Desarmes','touches':'Toques','expectedGoals':'Gols esperados (xG)'}


def fetch_json(url, ttl=20):
    key='match_source_v1_'+url
    data=cache.get(key)
    if data is not None:return data
    response=SESSION.get(url,headers=HEADERS,timeout=12)
    response.raise_for_status()
    data=response.json()
    cache.set(key,data,expire=ttl)
    return data


def sofa(path):
    return fetch_json('https://api.sofascore.com/api/v1'+path)


def same_team(team, other):
    left=[team.get(k) for k in ['displayName','name','shortDisplayName','abbreviation'] if team.get(k)]
    right=[other.get(k) for k in ['name','shortName','fullName'] if other.get(k)]
    return any(league_catalog.club_identity(a)==league_catalog.club_identity(b)
               and league_catalog.club_identity(a) for a in left for b in right)


def identify_sofa(competition, league):
    kickoff=datetime.fromisoformat(competition['date'].replace('Z','+00:00'))
    sides={c['homeAway']:c['team'] for c in competition['competitors']}
    def day_events(offset):
        day=(kickoff+timedelta(days=offset)).date().isoformat()
        return sofa('/sport/football/scheduled-events/'+day).get('events',[])
    with ThreadPoolExecutor(max_workers=3) as pool:
        days=list(pool.map(day_events,[-1,0,1]))
    candidates={}
    expected=league_catalog.PRIMARY.get(radar_identity.COUNTRIES.get(league))
    for events in days:
        for event in events:
            if abs(event.get('startTimestamp',0)-kickoff.timestamp())>3*3600:continue
            if expected and event.get('tournament',{}).get('uniqueTournament',{}).get('id')!=expected:continue
            if same_team(sides['home'],event.get('homeTeam',{})) and same_team(sides['away'],event.get('awayTeam',{})):
                candidates[event['id']]=event
    return next(iter(candidates.values())) if len(candidates)==1 else None


def espn_lineups(data, competition, league, event_id):
    players={'home':[],'away':[]}
    for group in data.get('rosters',[]):
        side=group.get('homeAway')
        if side not in players:continue
        team=group.get('team',{})
        for row in group.get('roster',[]):
            athlete=row.get('athlete',{})
            if not athlete.get('id'):continue
            players[side].append(dict(id=str(athlete['id']),name=athlete.get('displayName') or athlete.get('fullName'),
                jersey=row.get('jersey'),starter=bool(row.get('starter')),source='ESPN',sofa_id=None,
                statistics=[dict(label=LABELS.get(s['name'],s.get('displayName',s['name'])),value=s.get('displayValue')) for s in row.get('stats',[]) if s.get('name') in LABELS],
                radar_context=dict(display_name=athlete.get('displayName'),full_name=athlete.get('fullName'),
                    espn_player_id=str(athlete['id']),club=team.get('displayName'),espn_team_id=team.get('id'),league=league,match_id=str(event_id),jersey=row.get('jersey'))))
    return players


def sofa_lineups(event_id):
    data=sofa(f'/event/{event_id}/lineups')
    lineups={'home':[],'away':[]}
    for side in lineups:
        for row in data.get(side,{}).get('players',[]):
            player=row.get('player',{})
            if not player.get('id'):continue
            lineups[side].append(dict(id=str(player['id']),sofa_id=player['id'],name=player['name'],
                jersey=row.get('jerseyNumber'),starter=not row.get('substitute',False),source='Sofascore',
                statistics=[dict(label=LABELS[k],value=v) for k,v in row.get('statistics',{}).items() if k in LABELS and isinstance(v,(int,float))]))
    return lineups


def coordinates(play):
    x,y=play.get('fieldPositionX'),play.get('fieldPositionY')
    if not all(isinstance(v,(int,float)) and math.isfinite(v) and 0<=v<=100 for v in [x,y]):return None
    result=dict(x=x,y=y)
    x2,y2=play.get('fieldPosition2X'),play.get('fieldPosition2Y')
    if all(isinstance(v,(int,float)) and math.isfinite(v) and 0<=v<=100 for v in [x2,y2]):result.update(x2=x2,y2=y2)
    return result


@match_bp.get('/api/radar/match/<league>/<int:event_id>')
def analysis(league,event_id):
    if league not in LEAGUES:return jsonify(error='Liga inválida.'),400
    try:
        data=fetch_json(f'https://site.api.espn.com/apis/site/v2/sports/soccer/{league}/summary?event={event_id}')
        if str(data.get('header',{}).get('id'))!=str(event_id):return jsonify(error='Partida não confirmada na fonte.'),404
        competition=data['header']['competitions'][0]
        teams={c['homeAway']:dict(id=str(c['team']['id']),name=c['team']['displayName'],score=c.get('score','—')) for c in competition['competitors']}
        stats={g.get('homeAway'):{s['name']:s.get('displayValue') for s in g.get('statistics',[])} for g in data.get('boxscore',{}).get('teams',[])}
        statistics=[dict(label=label,home=stats.get('home',{}).get(key),away=stats.get('away',{}).get(key)) for key,label in LABELS.items() if key in stats.get('home',{}) or key in stats.get('away',{})]
        timeline=[dict(id=p.get('id'),clock=p.get('clock',{}).get('displayValue',''),text=p.get('shortText') or p.get('text') or p.get('type',{}).get('text'),coordinates=coordinates(p),team_id=str(p.get('team',{}).get('id',''))) for p in data.get('keyEvents',[])]
        result=dict(id=str(event_id),league=league,date=competition['date'],teams=teams,statistics=statistics,
            lineups=espn_lineups(data,competition,league,event_id),timeline=timeline,status=competition.get('status',{}).get('type',{}),
            updated_at=datetime.now(timezone.utc).isoformat(),source='ESPN',sofa=None,sofa_notice='Dados avançados do Sofascore ainda não disponíveis para esta partida.')
        # Advanced availability is independent of the basic match analysis.
        try:
            key=f'radar_match_link_v1_{league}_{event_id}'
            linked=cache.get(key)
            if linked is None:
                linked=identify_sofa(competition,league)
                cache.set(key,linked or False,expire=86400 if linked else 60)
            if linked:
                sid=int(linked['id'])
                cache.set(f'radar_verified_event_{sid}',True,expire=86400)
                result['sofa']=dict(id=sid,url=f'https://www.sofascore.com/football/match/{linked.get("slug","match")}/{linked.get("customId","")}#id:{sid}',
                    widgets=dict(lineups=f'https://widgets.sofascore.com/embed/lineups?id={sid}',momentum=f'https://widgets.sofascore.com/embed/attackMomentum?id={sid}'))
                result['sofa_notice']=''
                try:
                    roster=sofa_lineups(sid)
                    if any(roster.values()):result['lineups']=roster
                except Exception:
                    result['sofa_notice']='Widgets disponíveis; o elenco detalhado não foi retornado pelo Sofascore.'
        except Exception:
            result['sofa_notice']='O Sofascore não respondeu ou bloqueou a consulta. Estatísticas e lances ESPN continuam disponíveis.'
        response=jsonify(result);response.headers['Cache-Control']='no-store';return response
    except Exception:
        return jsonify(error='Não foi possível carregar esta partida. Tente novamente.'),502


@match_bp.get('/api/radar/event/<int:event_id>/player/<int:player_id>/heatmap')
def heatmap(event_id,player_id):
    if not cache.get(f'radar_verified_event_{event_id}'):return jsonify(error='Abra a análise da partida antes de consultar o atleta.'),404
    try:
        roster=sofa_lineups(event_id)
        if player_id not in {p['sofa_id'] for side in roster.values() for p in side}:
            return jsonify(error='Atleta não pertence ao elenco desta partida.'),404
        data=sofa(f'/event/{event_id}/player/{player_id}/heatmap')
        points=[dict(x=p['x'],y=p['y'],count=p.get('count',1)) for p in data.get('heatmap',[]) if coordinates(dict(fieldPositionX=p.get('x'),fieldPositionY=p.get('y')))]
        return jsonify(event_id=event_id,player_id=player_id,points=points,source='Sofascore',notice='' if points else 'A fonte não disponibilizou mapa de calor deste atleta neste jogo.')
    except Exception:
        return jsonify(event_id=event_id,player_id=player_id,points=[],source='Sofascore',notice='Mapa de calor indisponível na fonte para este jogo.'),200
