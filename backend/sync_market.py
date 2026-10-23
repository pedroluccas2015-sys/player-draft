"""Build the local catalogue from the public, dated Transfermarkt snapshot.

Usage: python sync_market.py [--source-dir path-containing-csv-gz]
"""
import argparse
import gzip
import io
import json
import sqlite3
from contextlib import closing
from pathlib import Path
import pandas as pd
from curl_cffi import requests
from services.market import DB, REGIONS, normalize, SNAPSHOT_DATE, SOURCE_URL

BASE = 'https://pub-e682421888d945d684bcae8890b0ec20.r2.dev/data/'


def sync(source_dir=None):
    def load(name):
        if source_dir:
            return pd.read_csv(Path(source_dir) / (name + '.csv.gz'))
        response = requests.get(BASE + name + '.csv.gz', timeout=90)
        response.raise_for_status()
        return pd.read_csv(io.BytesIO(response.content), compression='gzip')
    players, competitions, transfers = [load(n) for n in ('players', 'competitions', 'transfers')]
    country_map = dict(zip(competitions.competition_id, competitions.country_name))
    country_map.update({'COL1': 'Colombia'})
    players['club_country'] = players.current_club_domestic_competition_id.map(country_map)
    country_regions = {country: region for region, countries in REGIONS.items() for country in countries}
    players['region'] = players.club_country.map(country_regions)
    players['search_name'] = players.name.map(normalize)
    players['date_of_birth'] = players.date_of_birth.str.slice(0, 10)
    players['contract_expiration_date'] = players.contract_expiration_date.str.slice(0, 10)
    DB.parent.mkdir(parents=True, exist_ok=True)
    temp = DB.with_suffix('.new.sqlite')
    with closing(sqlite3.connect(temp)) as db:
        players.to_sql('players', db, if_exists='replace', index=False)
        transfers.to_sql('transfers', db, if_exists='replace', index=False)
        db.execute('CREATE INDEX player_identity ON players(search_name)')
        db.execute('CREATE UNIQUE INDEX player_id_index ON players(player_id)')
        db.execute('CREATE INDEX filters_index ON players(region, club_country, sub_position)')
        db.execute('CREATE INDEX transfer_player ON transfers(player_id)')
        db.commit()
    temp.replace(DB)
    (DB.parent/'SOURCE.json').write_text(json.dumps(dict(source_url=SOURCE_URL, snapshot_date=SNAPSHOT_DATE, players=len(players), transfers=len(transfers)), indent=2))
    print(f'Player Draft: {len(players)} atletas e {len(transfers)} transferências. Base de {SNAPSHOT_DATE}.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source-dir')
    sync(parser.parse_args().source_dir)
