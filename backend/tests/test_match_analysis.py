import unittest
from unittest.mock import patch, Mock
from datetime import datetime
from app import app
from routes import match_routes as m


def summary():
    return dict(header=dict(id='123',competitions=[dict(date='2026-11-03T22:30Z',status=dict(type=dict(state='post',shortDetail='FT')),
        competitors=[dict(homeAway='home',team=dict(id='1',displayName='Chapecoense'),score='1'),dict(homeAway='away',team=dict(id='2',displayName='Mirassol'),score='2')])]),
        boxscore=dict(teams=[dict(homeAway='home',statistics=[dict(name='totalShots',displayValue='11')]),dict(homeAway='away',statistics=[dict(name='totalShots',displayValue='15')])]),
        rosters=[dict(homeAway='home',team=dict(id='1',displayName='Chapecoense'),roster=[dict(athlete=dict(id='338663',displayName='Kauan'),starter=True,stats=[dict(name='goals',displayValue='1')])])],
        keyEvents=[dict(id='goal',clock=dict(displayValue="12'"),shortText='Gol de Kauan',fieldPositionX=91.4,fieldPositionY=54.0)])


class MatchAnalysisTests(unittest.TestCase):
    def setUp(self):
        self.client=app.test_client()
        self.cache=patch.object(m,'cache').start();self.cache.get.return_value=None
        self.addCleanup(patch.stopall)

    def test_basic_analysis_survives_sofa_block(self):
        with patch.object(m,'fetch_json',return_value=summary()),patch.object(m,'identify_sofa',side_effect=ConnectionError('403')):
            result=self.client.get('/api/radar/match/bra.1/123')
        self.assertEqual(result.status_code,200)
        self.assertEqual(result.json['statistics'][0]['home'],'11')
        self.assertEqual(result.json['lineups']['home'][0]['radar_context']['club'],'Chapecoense')
        self.assertEqual(result.json['timeline'][0]['coordinates']['x'],91.4)
        self.assertIsNone(result.json['sofa'])
        self.assertEqual(result.headers['Cache-Control'],'no-store')

    def test_wrong_espn_event_is_rejected(self):
        with patch.object(m,'fetch_json',return_value=summary()):
            self.assertEqual(self.client.get('/api/radar/match/bra.1/999').status_code,404)

    def test_invalid_league_never_contacts_source(self):
        with patch.object(m,'fetch_json') as fetch:
            self.assertEqual(self.client.get('/api/radar/match/invalid/123').status_code,400)
            fetch.assert_not_called()

    def test_match_mapping_requires_both_teams_orientation_date_and_league(self):
        competition=summary()['header']['competitions'][0]
        timestamp=int(datetime.fromisoformat(competition['date'].replace('Z','+00:00')).timestamp())
        event=dict(id=700,homeTeam=dict(name='Chapecoense'),awayTeam=dict(name='Mirassol'),startTimestamp=timestamp,tournament=dict(uniqueTournament=dict(id=325)))
        with patch.object(m,'sofa',return_value=dict(events=[event])):
            self.assertEqual(m.identify_sofa(competition,'bra.1')['id'],700)
        for bad in [dict(event,awayTeam=dict(name='Internacional')),dict(event,startTimestamp=timestamp+86400),dict(event,tournament=dict(uniqueTournament=dict(id=999))),dict(event,homeTeam=event['awayTeam'],awayTeam=event['homeTeam'])]:
            with patch.object(m,'sofa',return_value=dict(events=[bad])):
                self.assertIsNone(m.identify_sofa(competition,'bra.1'))

    def test_ambiguous_provider_events_are_not_joined(self):
        competition=summary()['header']['competitions'][0]
        event=dict(id=700,homeTeam=dict(name='Chapecoense'),awayTeam=dict(name='Mirassol'),startTimestamp=int(datetime.fromisoformat(competition['date'].replace('Z','+00:00')).timestamp()),tournament=dict(uniqueTournament=dict(id=325)))
        with patch.object(m,'sofa',return_value=dict(events=[event,dict(event,id=701)])):
            self.assertIsNone(m.identify_sofa(competition,'bra.1'))

    def test_heatmap_only_uses_this_game_not_season(self):
        self.cache.get.return_value=True
        roster=dict(home=[dict(sofa_id=44)],away=[])
        with patch.object(m,'sofa_lineups',return_value=roster),patch.object(m,'sofa',return_value=dict(heatmap=[dict(x=20,y=30),dict(x=-1,y=200)])) as source:
            result=self.client.get('/api/radar/event/700/player/44/heatmap')
        self.assertEqual(result.status_code,200)
        self.assertEqual(len(result.json['points']),1)
        self.assertEqual(result.json['event_id'],700)
        source.assert_called_once_with('/event/700/player/44/heatmap')

    def test_heatmap_rejects_player_from_other_match(self):
        self.cache.get.return_value=True
        with patch.object(m,'sofa_lineups',return_value=dict(home=[dict(sofa_id=1)],away=[])),patch.object(m,'sofa') as source:
            result=self.client.get('/api/radar/event/700/player/44/heatmap')
        self.assertEqual(result.status_code,404)
        source.assert_not_called()

    def test_no_unverified_event_heatmap(self):
        self.assertEqual(self.client.get('/api/radar/event/700/player/44/heatmap').status_code,404)

    def test_no_invented_coordinates(self):
        self.assertIsNone(m.coordinates(dict(text='Gol')))
        self.assertIsNone(m.coordinates(dict(fieldPositionX=float('nan'),fieldPositionY=10)))

    def test_verified_game_drives_widgets_and_individual_roster(self):
        event=dict(id=700,slug='chapecoense-mirassol',customId='abc')
        roster=dict(home=[dict(id='44',sofa_id=44,name='Kauan',source='Sofascore',statistics=[])],away=[])
        with patch.object(m,'fetch_json',return_value=summary()),patch.object(m,'identify_sofa',return_value=event),patch.object(m,'sofa_lineups',return_value=roster):
            result=self.client.get('/api/radar/match/bra.1/123')
        self.assertEqual(result.status_code,200)
        self.assertEqual(result.json['sofa']['id'],700)
        self.assertEqual(result.json['lineups']['home'][0]['sofa_id'],44)
        self.assertEqual(result.json['sofa']['widgets']['lineups'],'https://widgets.sofascore.com/embed/lineups?id=700')
        self.cache.set.assert_any_call('radar_verified_event_700',True,expire=86400)
