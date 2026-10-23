"""Rank inside the selected position, then select the five highest ratings."""
import math
from urllib.parse import urlencode
from flask import Blueprint, request, jsonify
from config import cache
from routes.club_routes import sofa

ranking_bp = Blueprint('ranking_routes', __name__)
LEAGUES={'325','17','8','23','35','34','7'}
POSITIONS={'all','G','D','M','F'}


def league_seasons(league):
    key=f'ranking_seasons_v1_{league}'
    seasons=cache.get(key)
    if seasons is None:
        seasons=sofa(f'/unique-tournament/{league}/seasons').get('seasons',[])
        cache.set(key,seasons,expire=3600)
    return seasons


def ranked_players(league,season_id,position):
    players={}
    limit=20
    for page in range(5):
        params=dict(limit=limit,offset=page*limit,order='-rating',accumulation='total',fields='rating,goals,assists,appearances')
        if position!='all':
            params['filters']=f'position.in.{position}'
        data=sofa(f'/unique-tournament/{league}/season/{season_id}/statistics?'+urlencode(params))
        rows=data.get('results',data.get('statistics',[]))
        added=0
        for row in rows:
            p=row.get('player',{})
            stats=row.get('statistics',row)
            try:
                rating=float(stats['rating'])
                matches=int(stats.get('appearances') or 0)
            except (KeyError,ValueError,TypeError):
                continue
            if not p.get('id') or not math.isfinite(rating) or not 0<rating<=10 or matches<1:
                continue
            if position!='all' and p.get('position') and p['position']!=position:
                continue
            if p['id'] in players:
                continue
            players[p['id']]=dict(id=p['id'],name=p.get('name','Atleta'),position=p.get('position') or (position if position!='all' else None),rating=rating,team=row.get('team',{}).get('name'),goals=stats.get('goals'),assists=stats.get('assists'),matches=matches,photo=f"/proxy-image/{p['id']}?v=portrait-v3")
            added+=1
        if len(players)>=5 or not rows or not added or (data.get('pages') is not None and page+1>=int(data['pages'])):
            break
    ordered=sorted(players.values(),key=lambda p:(-p['rating'],-p['matches'],p['id']))
    for p in ordered:
        p['rating']=round(p['rating'],2)
    return ordered[:5]


@ranking_bp.get('/api/rankings')
def get_rankings():
    league=request.args.get('league_id','325')
    position=request.args.get('position','all')
    if league not in LEAGUES or position not in POSITIONS:
        return jsonify(error='Liga ou posição inválida.'),400
    key=f'club_top5_v5_{league}_{position}'
    result=cache.get(key)
    if result is not None:
        return jsonify(result)
    try:
        seasons=league_seasons(league)
        players=[]
        selected=seasons[0] if seasons else {}
        previous=False
        for index,season in enumerate(seasons[:3]):
            players=ranked_players(league,season['id'],position)
            selected=season
            previous=index>0
            if players:
                break
        notice='Cinco maiores notas da liga no recorte selecionado, com pelo menos uma partida. A posição é aplicada antes de selecionar os cinco atletas; empates são ordenados por partidas e identificador.'
        if previous:
            notice+=' A temporada mais recente não retornou notas para este recorte; exibida a temporada disponível indicada acima.'
        if len(players)<5:
            notice+=f' A fonte disponibilizou {len(players)} atleta(s) com nota neste recorte; nenhum resultado foi inventado para completar cinco.'
        result=dict(players=players,season=selected.get('year'),minimum_matches=1,source='Sofascore',position=position,limit=5,returned=len(players),fallback_season=previous,notice=notice)
        cache.set(key,result,expire=900)
        return jsonify(result)
    except Exception as e:
        return jsonify(error=str(e)),502
