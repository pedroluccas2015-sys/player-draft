"""Discover current club squads independently of Transfermarkt's market coverage."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from datetime import datetime, timezone, date
from pathlib import Path
import json
import threading
from config import SESSION, HEADERS, cache
from services import market

ROOT = Path(__file__).resolve().parents[1] / 'data' / 'leagues'
LOCK = threading.Lock()
PRIMARY = {'Chile':11653, 'Uruguay':278, 'Ecuador':240, 'Paraguay':11541,
           'Peru':406, 'Bolivia':16736, 'Venezuela':231, 'Guyana':33932,
           'Suriname':18576, 'Egypt':808, 'Morocco':937, 'Algeria':841,
           'South Africa':358, 'Brazil':325, 'England':17, 'Spain':8,
           'Germany':35, 'France':34, 'Italy':23}
ALIASES = {'Korea, South':'South Korea', 'Türkiye':'Turkey', 'United States':'USA', 'Czech Republic':'Czechia'}
DETAILS = {'GK':'Goalkeeper','CB':'Centre-Back','LB':'Left-Back','RB':'Right-Back',
           'DM':'Defensive Midfield','CM':'Central Midfield','AM':'Attacking Midfield',
           'LM':'Left Midfield','RM':'Right Midfield','LW':'Left Winger','RW':'Right Winger',
           'ST':'Centre-Forward','CF':'Second Striker'}

def get(path):
    key='league_source_v1_'+path
    value=cache.get(key)
    if value is not None:
        return value
    response=SESSION.get('https://api.sofascore.com/api/v1'+path,headers=HEADERS,timeout=15)
    response.raise_for_status()
    value=response.json()
    cache.set(key,value,expire=21600)
    return value

def saved(country):
    path=ROOT/(market.normalize(country).replace(' ','_')+'.json')
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (FileNotFoundError,ValueError):
        return None

def sync(country, force=False):
    previous=saved(country)
    if previous and not force:
        age=(datetime.now(timezone.utc)-datetime.fromisoformat(previous['updated_at'])).total_seconds()
        if age<21600:
            return previous
    try:
        tournament_id=PRIMARY.get(country)
        if not tournament_id:
            cats=get('/sport/football/categories')['categories']
            accepted={country,ALIASES.get(country,country)}
            category=next((c for c in cats if c['name'] in accepted),None)
            if not category:
                raise ValueError('País não encontrado na fonte de elencos.')
            groups=get(f"/category/{category['id']}/unique-tournaments").get('groups',[])
            tournaments=[t for g in groups for t in g.get('uniqueTournaments',[])
                         if not any(x in t['name'].lower() for x in ['women','cup','u19','u20','u21','friendly'])]
            tournament_id=max(tournaments,key=lambda t:t.get('userCount',0))['id']
        info=get(f'/unique-tournament/{tournament_id}').get('uniqueTournament',{})
        seasons=get(f'/unique-tournament/{tournament_id}/seasons').get('seasons',[])
        teams={}
        chosen=None
        for season in seasons[:2]:
            tables=get(f"/unique-tournament/{tournament_id}/season/{season['id']}/standings/total").get('standings',[])
            teams={r['team']['id']:r['team'] for table in tables for r in table.get('rows',[]) if not r['team'].get('national')}
            if teams:
                chosen=season
                break
        if not teams:
            raise ValueError('A fonte ainda não disponibiliza a classificação e os clubes desta liga.')
        players={}
        failures=0
        def roster(team):
            return team,get(f"/team/{team['id']}/players").get('players',[])
        with ThreadPoolExecutor(max_workers=3) as pool:
            tasks=[pool.submit(roster,t) for t in teams.values()]
            for task in tasks:
                try:
                    team,rows=task.result()
                    for row in rows:
                        p=row.get('player',{})
                        if p.get('id') and p.get('gender','M')=='M':
                            players[p['id']]=dict(player={k:p[k] for k in ['id','name','dateOfBirthTimestamp','position','positionsDetailed','country','preferredFoot','height','contractUntilTimestamp','proposedMarketValueRaw'] if k in p},club=team['name'])
                except Exception:
                    failures+=1
        result=dict(country=country,tournament_id=tournament_id,league=info.get('name'),
                    season=chosen.get('year'),updated_at=datetime.now(timezone.utc).isoformat(),
                    teams=len(teams),failures=failures,players=list(players.values()),status='partial' if failures else 'available')
        if not players:
            result['status']='not_covered'
            result['notice']='Clubes identificados, mas a fonte não publicou os elencos desta liga.'
        ROOT.mkdir(parents=True,exist_ok=True)
        path=ROOT/(market.normalize(country).replace(' ','_')+'.json')
        with LOCK:
            temp=path.with_suffix('.tmp')
            temp.write_text(json.dumps(result,ensure_ascii=False),encoding='utf-8')
            temp.replace(path)
        return result
    except Exception as exc:
        if previous:
            return dict(previous,stale=True,notice='Última consulta preservada; atualização da fonte indisponível.')
        return dict(country=country,players=[],status='not_covered',notice=str(exc))

def dto(entry,country,index):
    p=entry['player']
    birth=datetime.fromtimestamp(p['dateOfBirthTimestamp'],timezone.utc).date().isoformat() if p.get('dateOfBirthTimestamp') else None
    matches=index.get((market.normalize(p.get('name')),birth),[]) if birth else []
    tm=market.enrich(matches[0]) if len(matches)==1 else None
    raw=p.get('proposedMarketValueRaw') or {}
    value=raw.get('value') if raw.get('currency')=='EUR' else None
    today=date.today()
    dob=date.fromisoformat(birth) if birth else None
    region=next((r for r,cs in market.REGIONS.items() if country in cs),None)
    result=dict(id=p['id'],sofa_id=p['id'],name=p['name'],club=entry['club'],club_country=country,region=region,
                nationality=p.get('country',{}).get('name'),date_of_birth=birth,
                age=today.year-dob.year-((today.month,today.day)<(dob.month,dob.day)) if dob else None,
                position={'G':'GOL','D':'DEF','M':'MEI','F':'ATA'}.get(p.get('position'),'—'),
                position_detail=DETAILS.get((p.get('positionsDetailed') or [''])[0]),
                foot=(p.get('preferredFoot') or '').lower(),height_in_cm=p.get('height'),
                contract_until=datetime.fromtimestamp(p['contractUntilTimestamp'],timezone.utc).date().isoformat() if p.get('contractUntilTimestamp') else None,
                market_value_eur=value,market_value_source='Sofascore' if value is not None else None,
                photo=f"/proxy-image/{p['id']}?v=portrait-v3",source='Sofascore',rating=None)
    if tm:
        result.update(tm_id=tm['tm_id'],market_value_eur=tm['market_value_eur'],market_value_source='Transfermarkt',
                      snapshot_date=market.SNAPSHOT_DATE,photo_fallback=tm.get('photo'),position_detail=tm.get('position_detail') or result['position_detail'])
    return result

def matches(p,f):
    for key,field in [('position','position_detail'),('foot','foot')]:
        if f.get(key) and p.get(field)!=f[key]:
            return False
    if f.get('q') and market.normalize(f['q']) not in market.normalize(p['name']+' '+p['club']):
        return False
    for key,field in [('value','market_value_eur'),('age','age'),('height','height_in_cm')]:
        for bound in ['min','max']:
            value=f.get(bound+'_'+key)
            if value not in ('',None) and (p.get(field) is None or (p[field]<float(value) if bound=='min' else p[field]>float(value))):
                return False
    contract=f.get('contract')
    end=p.get('contract_until')
    if contract=='unknown' and end: return False
    if contract=='free': return False  # A squad member cannot be inferred to be a free agent.
    if contract=='expiring' and (not end or not market.SNAPSHOT_DATE<=end<='2027-01-06'): return False
    if contract=='long' and (not end or end<='2027-07-06'): return False
    return True

def metadata(base):
    for row in base['countries']:
        data=saved(row['country'])
        if data:
            row.update(squad_count=len(data['players']),league=data.get('league'),squads_updated_at=data.get('updated_at'))
            row['count']=max(row['count'],len(data['players']))
            row['has_data']=row['has_data'] or bool(data['players'])
            row['coverage_status']='available' if row['has_data'] else 'not_covered'
    return base

def search(filters):
    base=market.search(dict(filters,page=1),page_size=100000)
    countries=[filters['country']] if filters.get('country') else [r['country'] for r in base['metadata']['countries'] if not filters.get('region') or r['region']==filters['region']]
    # Do not nest country and squad executors: keep remote concurrency bounded to three.
    catalogues=[sync(c) for c in countries]
    with closing(market.connect()) as db:
        index={}
        for row in db.execute('SELECT * FROM players'):
            index.setdefault((row['search_name'],(row['date_of_birth'] or '')[:10]),[]).append(row)
    players={p['id']:p for p in base['players']}
    for catalogue in catalogues:
        for entry in catalogue['players']:
            p=dto(entry,catalogue['country'],index)
            p.update(league_id=catalogue.get('tournament_id'),league_name=catalogue.get('league'),squads_updated_at=catalogue.get('updated_at'))
            if p.get('tm_id'):
                players.pop(f"tm:{p['tm_id']}",None)
            if matches(p,filters): players[p['id']]=p
    rows=list(players.values())
    sort=filters.get('sort')
    rows.sort(key=lambda p: ((p.get('age') is None,p.get('age') or 0,p['name']) if sort=='age_asc' else (p['name'],) if sort=='name' else (p.get('market_value_eur') is None,(p.get('market_value_eur') or 0)*(1 if sort=='value_asc' else -1),p['name'])))
    page=max(1,int(filters.get('page',1)))
    base.update(players=rows[(page-1)*24:page*24],total=len(rows),page=page,page_size=24,
                metadata=metadata(base['metadata']),leagues=[{k:v for k,v in c.items() if k!='players'} for c in catalogues],
                coverage_status='available' if rows or any(c['players'] for c in catalogues) or base['coverage_status']=='available' else 'not_covered',
                coverage_notice='Elencos consultados no Sofascore. Valores Transfermarkt de 06/07/2026 quando há correspondência confirmada; demais estimativas identificadas como Sofascore. Campos desconhecidos não atendem filtros específicos.')
    return base
