from contextlib import closing
"""Checks around financial filters and cross-provider identity, without live services."""
import unittest
import tempfile
import sqlite3
from datetime import date, datetime, timezone
from pathlib import Path
from unittest.mock import patch
from app import app
from services import market
from routes.club_routes import resolve_player


class ScoutingTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent)
        self.db=Path(self.temp.name)/'test.sqlite'
        self.replace=patch.object(market,'DB',self.db)
        self.replace.start()
        today=date.today()
        dob=today.replace(year=today.year-22).isoformat()
        with closing(sqlite3.connect(self.db)) as db:
            db.execute('CREATE TABLE players(player_id INTEGER, name TEXT, search_name TEXT, last_season INTEGER, date_of_birth TEXT, club_country TEXT, region TEXT, sub_position TEXT, position TEXT, foot TEXT, height_in_cm REAL, contract_expiration_date TEXT, market_value_in_eur REAL, current_club_name TEXT, country_of_citizenship TEXT, image_url TEXT, url TEXT)')
            values=[
                (1,'Talento Um','talento um',2025,dob,'Brazil','south-america','Centre-Forward','Attack','left',185,'2026-12-31',5000000,'Clube A','Brazil',None,'https://example.com/1'),
                (2,'Talento Dois','talento dois',2025,dob,'Brazil','south-america','Goalkeeper','Goalkeeper','right',190,None,None,'Clube B','Brazil',None,'https://example.com/2'),
                (3,'Talento Três','talento tres',2025,dob,'Spain','europe','Centre-Forward','Attack','left',180,'2028-06-30',2000000,'Clube C','Brazil',None,'https://example.com/3'),
                (4,'Aposentado','aposentado',2020,'1970-01-01','Brazil','south-america','Centre-Forward','Attack','right',180,None,10000,'Retired','Brazil',None,None),
                (5,'Homônimo','homonimo',2025,'2001-01-01','Brazil','south-america','Centre-Back','Defence','right',182,None,0,'Clube D','Brazil',None,None),
                (6,'Homônimo','homonimo',2025,'2002-01-01','Brazil','south-america','Centre-Back','Defence','right',182,'2025-06-30',100000,'Clube E','Brazil',None,None)]
            db.executemany('INSERT INTO players VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',values)
            db.execute('CREATE TABLE transfers(player_id INTEGER,transfer_date TEXT,from_club_name TEXT,to_club_name TEXT,transfer_fee REAL)')
            db.execute("INSERT INTO transfers VALUES (1,'2025-07-01','Origem','Destino',200000)")
            db.commit()
        self.client=app.test_client()

    def tearDown(self):
        self.replace.stop()
        self.temp.cleanup()

    def test_combined_region_position_budget_age_filters(self):
        result=market.search(dict(country='Brazil',region='south-america',position='Centre-Forward',max_value='5000000',min_age='22',max_age='22',foot='left',min_height='180'))
        self.assertEqual([p['tm_id'] for p in result['players']],[1])

    def test_missing_value_is_not_treated_as_free(self):
        result=market.search(dict(max_value='0'))
        self.assertEqual([p['tm_id'] for p in result['players']],[5])

    def test_contract_unknown_filter(self):
        self.assertEqual({p['tm_id'] for p in market.search(dict(contract='unknown'))['players']},{2,5})

    def test_expired_contract_is_not_assumed_free_agent(self):
        self.assertEqual(market.search(dict(contract='free'))['total'],0)

    def test_expiring_contract_is_based_on_snapshot(self):
        self.assertEqual([p['tm_id'] for p in market.search(dict(contract='expiring'))['players']],[1])

    def test_old_seasons_are_excluded_from_discovery(self):
        self.assertNotIn(4,[p['tm_id'] for p in market.search({})['players']])

    def test_snapshot_date_and_source_are_visible(self):
        self.assertFalse(market.metadata()['is_live'])
        self.assertEqual(market.metadata()['snapshot_date'],'2026-07-06')

    def test_all_twelve_south_american_countries_are_filter_options(self):
        rows=[c for c in market.metadata()['countries'] if c['region']=='south-america']
        self.assertEqual({c['country'] for c in rows},set(market.REGIONS['south-america']))
        self.assertEqual(len(rows),12)

    def test_four_african_markets_include_league_and_coverage(self):
        rows=[c for c in market.metadata()['countries'] if c['region']=='africa']
        self.assertEqual({c['country'] for c in rows},{'Egypt','Morocco','Algeria','South Africa'})
        self.assertTrue(all(c['league'] and not c['has_data'] for c in rows))

    def test_uncovered_country_is_not_reported_as_no_matching_players(self):
        result=market.search(dict(region='africa',country='Egypt'))
        self.assertEqual(result['coverage_status'],'not_covered')
        self.assertTrue(result['coverage_notice'])
        self.assertEqual(result['players'],[])

    def test_covered_country_with_no_matches_remains_a_covered_market(self):
        result=market.search(dict(country='Brazil',min_value='999999999'))
        self.assertEqual(result['coverage_status'],'available')
        self.assertIsNone(result['coverage_notice'])

    def test_accent_normalization(self):
        self.assertEqual([p['tm_id'] for p in market.search(dict(q='Três'))['players']],[3])

    def test_ambiguous_identity_without_birthdate_is_not_joined(self):
        self.assertIsNone(market.match_player('Homônimo'))
        self.assertEqual(market.match_player('Homônimo','2002-01-01')['tm_id'],6)

    def test_profile_has_separate_provider_identity_and_history(self):
        p=market.profile(1)
        self.assertEqual(p['id'],'tm:1')
        self.assertEqual(len(p['transfers']),1)
        self.assertIsNone(p['rating'])

    def test_invalid_ranges_and_values_are_rejected(self):
        for query in ['min_value=5&max_value=1','min_age=25&max_age=18','min_value=not-a-number','min_value=nan','max_value=inf','min_age=12.5','contract=unsupported','page=nan']:
            with self.subTest(query=query):
                self.assertEqual(self.client.get('/api/scouting/search?'+query).status_code,400)

    def test_injection_is_parameterized(self):
        self.assertEqual(market.search(dict(q="' OR 1=1 --"))['total'],0)
        self.assertEqual(market.metadata()['total'],5)

    def test_removed_automatic_callup_api(self):
        self.assertEqual(self.client.get('/api/convocacao/processar').status_code,404)

    def test_missing_sofa_keeps_market_profile_without_fake_statistics(self):
        with patch('routes.club_routes.resolve_player',side_effect=ConnectionError('Serviço indisponível')):
            r=self.client.post('/api/search',json={'tm_id':1})
        self.assertEqual(r.status_code,200)
        self.assertEqual(r.json['statistics_status'],'unavailable')
        self.assertEqual(r.json['stats'],[])
        self.assertEqual(r.json['market_value_eur'],5000000)

    def test_conflicting_birthdates_do_not_join(self):
        timestamp=int(datetime(2005,2,7,tzinfo=timezone.utc).timestamp())
        with patch('routes.club_routes.sofa',side_effect=[{'results':[{'type':'player','entity':{'id':99,'team':{'sport':{'slug':'football'}}}}]}, {'player':{'id':99,'name':'Talento','dateOfBirthTimestamp':timestamp}}]):
            self.assertIsNone(resolve_player('Talento','2005-02-08'))


if __name__=='__main__':
    unittest.main()
