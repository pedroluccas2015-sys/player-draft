"""Resolve ESPN match participants inside their own club, never by global player name."""
from services import league_catalog
from datetime import datetime, timezone
from config import SESSION, cache

COUNTRIES = {'bra.1':'Brazil','eng.1':'England','ita.1':'Italy','esp.1':'Spain',
             'ger.1':'Germany','fra.1':'France','por.1':'Portugal','usa.1':'USA'}
GENERIC = {'clube','club','de','do','da','dos','das','regatas','futebol','football','fc','ec','sc','ac','cf','afc','esporte'}


def club_key(name):
    return set(league_catalog.identity_name(name).split()) - GENERIC


def same_club(name, variants):
    key=club_key(name)
    return bool(key) and any(key==club_key(v) for v in variants if v)


def name_matches(query, player):
    """Allow initials and abbreviated names only within the confirmed squad."""
    query=league_catalog.identity_name(query).split()
    if not query:
        return False
    variants=[player.get(k) for k in ['name','shortName','fullName'] if player.get(k)]
    for variant in variants:
        tokens=league_catalog.identity_name(variant).split()
        remaining=iter(tokens)
        if all(any(t==q or (len(q)==1 and t.startswith(q)) for t in remaining) for q in query):
            return True
    return False


def espn_identity(context):
    athlete=str(context.get('espn_player_id') or '')
    league=context.get('league')
    allowed=set(COUNTRIES)|{'uefa.champions','conmebol.libertadores','conmebol.sudamericana'}
    if not athlete.isdigit() or league not in allowed:
        return {}
    key=f'radar_espn_identity_v1_{league}_{athlete}'
    saved=cache.get(key)
    if saved is not None:
        return saved
    try:
        response=SESSION.get(f'https://sports.core.api.espn.com/v2/sports/soccer/leagues/{league}/athletes/{athlete}',timeout=10)
        response.raise_for_status()
        data=response.json()
        if str(data.get('id'))!=athlete:
            return {}
        result=dict(birth=(data.get('dateOfBirth') or '')[:10],
                    name=' '.join(filter(None,[data.get('firstName'),data.get('lastName')])))
        cache.set(key,result,expire=86400)
        return result
    except Exception:
        return {}


def resolve(context, source):
    club=str(context.get('club') or '').strip()
    names=list(dict.fromkeys(str(context.get(k) or '').strip() for k in ['full_name','display_name']))
    names=[name for name in names if name]
    if not club or not names:
        raise ValueError('Clube e nome do atleta são obrigatórios no radar.')
    club_names=[club]+[str(n) for n in context.get('club_aliases',[]) if isinstance(n,str)]
    country=COUNTRIES.get(context.get('league'))
    squads=[]
    # Team search is constrained to an exact club alias and (for domestic leagues) country.
    from urllib.parse import quote
    try:
        rows=source('/search/all?q='+quote(club)).get('results',[])
        teams={}
        for row in rows:
            team=row.get('entity',{})
            if row.get('type')!='team' or team.get('national') or team.get('sport',{}).get('slug')!='football':
                continue
            category=team.get('category',{}).get('name') or team.get('country',{}).get('name')
            if country and category and category!=country:
                continue
            if any(same_club(alias,[team.get(k) for k in ['name','shortName','fullName']]) for alias in club_names):
                teams[team['id']]=team
        if len(teams)==1:
            team=next(iter(teams.values()))
            squads=[r['player'] for r in source(f"/team/{team['id']}/players").get('players',[]) if r.get('player')]
    except (ConnectionError, KeyError):
        # Saved club squads retain provider IDs when the roster service is unavailable.
        pass
    if not squads:
        catalogues=[league_catalog.saved(country)] if country else []
        # Read files directly for international competitions (country names may contain aliases).
        if not country:
            import json
            catalogues=[json.loads(path.read_text(encoding='utf-8')) for path in league_catalog.ROOT.glob('*.json')]
        clubs={}
        for catalogue in catalogues:
            for entry in (catalogue or {}).get('players',[]):
                if any(same_club(alias,[entry['club']]) for alias in club_names):
                    clubs.setdefault((catalogue['country'],entry['club']),[]).append(entry['player'])
        if len(clubs)==1:
            squads=next(iter(clubs.values()))
    # Prefer a full name; only use the display abbreviation when it gives one candidate.
    for name in names:
        candidates={p['id']:p for p in squads if p.get('id') and name_matches(name,p)}
        if len(candidates)>1 and context.get('jersey'):
            candidates={i:p for i,p in candidates.items() if str(p.get('jerseyNumber') or '')==str(context['jersey'])}
        if len(candidates)==1:
            return source(f"/player/{next(iter(candidates))}").get('player')
        if len(candidates)>1:
            break
    # Provider birth data can disambiguate initials or a nickname absent from the roster.
    identity=espn_identity(context)
    birth=identity.get('birth')
    if birth:
        candidates={}
        for p in squads:
            timestamp=p.get('dateOfBirthTimestamp')
            if timestamp and datetime.fromtimestamp(timestamp,timezone.utc).date().isoformat()==birth:
                candidates[p['id']]=p
        if len(candidates)==1:
            return source(f"/player/{next(iter(candidates))}").get('player')
    return None
