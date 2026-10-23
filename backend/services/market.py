"""Transfermarkt-derived public snapshot. Never presented as a live quote."""
from contextlib import closing
from pathlib import Path
from datetime import date
import calendar
import sqlite3
import unicodedata
import json
import math

DB = Path(__file__).resolve().parents[1] / 'data' / 'market.sqlite'
SOURCE = 'Transfermarkt via dcaribou/transfermarkt-datasets'
SOURCE_URL = 'https://github.com/dcaribou/transfermarkt-datasets'
SNAPSHOT_DATE = '2026-07-06'
REGIONS = {
    'south-america': ['Brazil', 'Argentina', 'Colombia', 'Chile', 'Uruguay', 'Ecuador', 'Paraguay', 'Peru', 'Bolivia', 'Venezuela', 'Guyana', 'Suriname'],
    'north-america': ['United States', 'Mexico', 'Canada', 'Costa Rica'],
    'asia': ['Japan', 'Korea, South', 'Saudi Arabia', 'China', 'Qatar', 'United Arab Emirates'],
    'oceania': ['Australia', 'New Zealand'],
    'africa': ['Egypt', 'Morocco', 'Algeria', 'South Africa'],
}
EUROPE = ['England', 'Spain', 'Italy', 'Germany', 'France', 'Portugal', 'Netherlands', 'Belgium', 'Austria', 'Switzerland', 'Denmark', 'Norway', 'Sweden', 'Scotland', 'Greece', 'Poland', 'Romania', 'Serbia', 'Croatia', 'Czech Republic', 'Russia', 'Ukraine', 'Türkiye', 'Turkey']
REGIONS['europe'] = EUROPE
AFRICAN_LEAGUES = {'Egypt': 'Premier League egípcia', 'Morocco': 'Botola Pro', 'Algeria': 'Ligue 1 argelina', 'South Africa': 'Premiership sul-africana'}


def normalize(value):
    value = unicodedata.normalize('NFKD', value or '').encode('ascii', 'ignore').decode().lower()
    return ' '.join(value.replace('-', ' ').replace('.', '').split())


def connect():
    if not DB.exists():
        raise FileNotFoundError('Base de mercado ausente. Execute python sync_market.py na pasta backend.')
    db = sqlite3.connect(DB)
    db.row_factory = sqlite3.Row
    return db


def metadata():
    with closing(connect()) as db:
        total = db.execute('SELECT count(*) FROM players WHERE last_season >= 2025').fetchone()[0]
        observed = {r['country']: dict(r) for r in db.execute('SELECT club_country AS country, region, count(*) AS count FROM players WHERE last_season >= 2025 AND club_country IS NOT NULL GROUP BY club_country ORDER BY club_country')}
    # Geographic options are independent from the coverage of the dated catalogue.
    for region in ['south-america', 'africa']:
        for country in REGIONS[region]:
            observed.setdefault(country, dict(country=country, region=region, count=0))
            observed[country]['region']=region
    countries=[]
    for country,row in sorted(observed.items()):
        row['has_data']=row['count']>0
        row['coverage_status']='available' if row['has_data'] else 'not_covered'
        row['league']=AFRICAN_LEAGUES.get(country)
        countries.append(row)
    return dict(source=SOURCE, source_url=SOURCE_URL, snapshot_date=SNAPSHOT_DATE, is_live=False, total=total, countries=countries,
                notice='Valores, contratos e clubes da base Transfermarkt de 06/07/2026. Cobertura parcial; não são cotações em tempo real.')


def enrich(row):
    p = dict(row)
    dob = date.fromisoformat(p['date_of_birth'][:10]) if p.get('date_of_birth') else None
    today = date.today()
    p['age'] = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day)) if dob else None
    p['market_value_eur'] = p.pop('market_value_in_eur', None)
    p['tm_id'] = p.pop('player_id')
    p['id'] = f"tm:{p['tm_id']}"
    p['photo'] = p.pop('image_url', None)
    p['club'] = p.pop('current_club_name', None)
    p['nationality'] = p.pop('country_of_citizenship', None)
    p['position_detail'] = p.pop('sub_position', None)
    p['contract_until'] = (p.pop('contract_expiration_date', None) or '')[:10] or None
    p['source'] = SOURCE
    p['snapshot_date'] = SNAPSHOT_DATE
    p['market_status'] = 'snapshot'
    p['rating'] = None
    return p


def search(filters, page_size=24):
    where, values = ['last_season >= 2025'], []
    def add(sql, *args):
        where.append(sql)
        values.extend(args)
    for field, column in [('country', 'club_country'), ('region', 'region'), ('position', 'sub_position'), ('foot', 'foot')]:
        if filters.get(field):
            add(f'{column} = ?', filters[field])
    if filters.get('q'):
        add('(search_name LIKE ? OR current_club_name LIKE ?)', '%' + normalize(filters['q']) + '%', '%' + filters['q'] + '%')
    today = date.today()
    for key in ['min_value', 'max_value', 'min_age', 'max_age', 'min_height', 'max_height']:
        if filters.get(key) not in (None, ''):
            try:
                value = float(filters[key])
                if not math.isfinite(value) or value < 0 or value > 1_000_000_000:
                    raise ValueError()
            except (ValueError, TypeError):
                raise ValueError(f'Valor inválido para {key}.')
            if key.endswith('value'):
                add('market_value_in_eur ' + ('>= ?' if key.startswith('min') else '<= ?'), value)
            elif key.endswith('height'):
                add('height_in_cm ' + ('>= ?' if key.startswith('min') else '<= ?'), value)
            else:
                if value != int(value) or value > 100:
                    raise ValueError('A idade deve ser um número inteiro entre 0 e 100.')
                age = int(value)
                years = age if key.startswith('min') else age + 1
                cutoff = date(today.year - years, today.month, min(today.day, calendar.monthrange(today.year-years, today.month)[1])).isoformat()
                add('substr(date_of_birth,1,10) ' + ('<= ?' if key.startswith('min') else '> ?'), cutoff)
    for lower, upper in [('min_value', 'max_value'), ('min_age', 'max_age'), ('min_height', 'max_height')]:
        if filters.get(lower) not in ('', None) and filters.get(upper) not in ('', None) and float(filters[lower]) > float(filters[upper]):
            raise ValueError('O mínimo não pode ser maior que o máximo.')
    # Contract state is evaluated at snapshot date, not inferred from an expired snapshot.
    contract = filters.get('contract', '')
    if contract == 'expiring':
        add("substr(contract_expiration_date,1,10) BETWEEN ? AND ?", SNAPSHOT_DATE, '2027-01-06')
    elif contract == 'long':
        add("substr(contract_expiration_date,1,10) > ?", '2027-07-06')
    elif contract == 'unknown':
        add("(contract_expiration_date IS NULL OR contract_expiration_date = '')")
    elif contract == 'free':
        add("lower(current_club_name) IN ('without club', 'without club ', 'sem clube')")
    elif contract:
        raise ValueError('Situação de contrato inválida.')
    order = {'value_desc': 'market_value_in_eur DESC', 'value_asc': 'market_value_in_eur IS NULL, market_value_in_eur ASC', 'age_asc': 'date_of_birth DESC', 'name': 'name ASC'}.get(filters.get('sort'), 'market_value_in_eur DESC')
    page = max(1, int(filters.get('page', 1)))
    clause = ' AND '.join(where)
    with closing(connect()) as db:
        count = db.execute('SELECT count(*) FROM players WHERE ' + clause, values).fetchone()[0]
        rows = db.execute(f'SELECT * FROM players WHERE {clause} ORDER BY {order}, player_id LIMIT ? OFFSET ?', values + [page_size, (page - 1)*page_size]).fetchall()
    meta=metadata()
    country=next((c for c in meta['countries'] if c['country']==filters.get('country')),None)
    region_countries=[c for c in meta['countries'] if c['region']==filters.get('region')]
    uncovered=(country is not None and not country['has_data']) or (not filters.get('country') and region_countries and not any(c['has_data'] for c in region_countries))
    coverage_notice='Este mercado está disponível para seleção, mas o catálogo Transfermarkt de 06/07/2026 não contém atletas de clubes deste país/região. Isso não significa que não existam jogadores com o perfil procurado.' if uncovered else None
    return dict(players=[enrich(p) for p in rows], total=count, page=page, page_size=24, metadata=meta,coverage_status='not_covered' if uncovered else 'available',coverage_notice=coverage_notice)


def profile(player_id):
    with closing(connect()) as db:
        row = db.execute('SELECT * FROM players WHERE player_id = ?', (int(player_id),)).fetchone()
        if row is None:
            return None
        p = enrich(row)
        p['transfers'] = [dict(r) for r in db.execute('SELECT * FROM transfers WHERE player_id = ? ORDER BY transfer_date DESC', (int(player_id),))]
    p['transfer_source'] = SOURCE
    p['transfer_snapshot_date'] = SNAPSHOT_DATE
    p['market_url'] = p.get('url')
    return p


def match_player(name, date_of_birth=None):
    with closing(connect()) as db:
        rows = db.execute('SELECT player_id, date_of_birth FROM players WHERE search_name = ?', (normalize(name),)).fetchall()
    if date_of_birth:
        rows = [r for r in rows if (r['date_of_birth'] or '')[:10] == date_of_birth]
    # Ambiguous identities are deliberately left unmatched.
    return profile(rows[0]['player_id']) if len(rows) == 1 else None
