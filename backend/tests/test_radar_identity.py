import unittest
from unittest.mock import patch, Mock
from services import radar_identity
from app import app


def team(i,name,country='Brazil'):
    return dict(type='team',entity=dict(id=i,name=name,category=dict(name=country),sport=dict(slug='football')))


class RadarIdentityTests(unittest.TestCase):
    def setUp(self):
        self.identity=patch.object(radar_identity,'espn_identity',return_value={}).start()
        self.addCleanup(patch.stopall)

    def source(self, roster, teams=None):
        def fetch(path):
            if path.startswith('/search/all?'):
                return dict(results=teams if teams is not None else [team(2180,'Chapecoense')])
            if path=='/team/2180/players':
                return dict(players=[dict(player=p) for p in roster])
            if path.startswith('/player/'):
                return dict(player=next(p for p in roster if str(p['id'])==path.split('/')[-1]))
            raise AssertionError(path)
        return Mock(side_effect=fetch)

    def context(self):
        return dict(club='Chapecoense',league='bra.1',full_name='Kauan',display_name='Kauan',espn_player_id='338663')

    def test_homonym_is_resolved_only_inside_match_club(self):
        source=self.source([dict(id=1198003,name='Kauan',position='D')])
        player=radar_identity.resolve(self.context(),source)
        self.assertEqual(player['id'],1198003)
        self.assertEqual(source.call_args_list[0].args[0],'/search/all?q=Chapecoense')
        self.assertNotIn('/player/338663',[c.args[0] for c in source.call_args_list])

    def test_full_name_has_priority_over_short_display(self):
        source=self.source([dict(id=1,name='João Silva'),dict(id=2,name='José Silva')])
        context=dict(club='Chapecoense',league='bra.1',full_name='João Silva',display_name='J. Silva')
        self.assertEqual(radar_identity.resolve(context,source)['id'],1)

    def test_initials_resolve_to_full_roster_name(self):
        source=self.source([dict(id=1,name='João Pedro Silva'),dict(id=2,name='José Santos')])
        context=dict(club='Chapecoense',league='bra.1',display_name='J. Silva')
        self.assertEqual(radar_identity.resolve(context,source)['id'],1)

    def test_ambiguous_initials_do_not_open_first_result(self):
        source=self.source([dict(id=1,name='João Silva'),dict(id=2,name='José Silva')])
        self.assertIsNone(radar_identity.resolve(dict(club='Chapecoense',league='bra.1',display_name='J. Silva'),source))

    def test_missing_player_does_not_trigger_global_player_search(self):
        source=self.source([dict(id=1,name='Outro atleta')])
        self.assertIsNone(radar_identity.resolve(self.context(),source))
        self.assertEqual(len(source.call_args_list),2)

    def test_club_homonym_in_another_country_is_rejected(self):
        source=self.source([dict(id=1,name='Kauan')],teams=[team(999,'Chapecoense','Uruguay'),team(2180,'Chapecoense')])
        self.assertEqual(radar_identity.resolve(self.context(),source)['id'],1)

    def test_saved_squad_keeps_identity_when_club_search_is_unavailable(self):
        source=Mock(side_effect=[ConnectionError('offline'),dict(player=dict(id=1198003,name='Kauan'))])
        snapshot=dict(country='Brazil',players=[dict(club='Chapecoense',player=dict(id=1198003,name='Kauan'))])
        with patch.object(radar_identity.league_catalog,'saved',return_value=snapshot):
            self.assertEqual(radar_identity.resolve(self.context(),source)['id'],1198003)

    def test_api_passes_confirmed_identity_to_dossier(self):
        source=self.source([dict(id=1198003,name='Kauan',position='D')])
        with patch('routes.club_routes.sofa',source),patch('routes.club_routes.build_dossier',return_value=dict(id=1198003,name='Kauan',stats=[])) as dossier,patch('routes.club_routes.market.match_player',return_value=None):
            result=app.test_client().post('/api/search',json=dict(radar_context=self.context()))
        self.assertEqual(result.status_code,200)
        self.assertEqual(result.json['id'],1198003)
        self.assertEqual(dossier.call_args.args[0]['id'],1198003)

    def test_api_rejects_ambiguous_identity_without_building_dossier(self):
        with patch('routes.club_routes.radar_identity.resolve',return_value=None),patch('routes.club_routes.build_dossier') as dossier:
            result=app.test_client().post('/api/search',json=dict(radar_context=self.context()))
        self.assertEqual(result.status_code,404)
        dossier.assert_not_called()

    def test_birth_disambiguates_two_players_with_same_initials(self):
        from datetime import datetime, timezone
        self.identity.return_value=dict(birth='2003-04-07')
        birthday=int(datetime(2003,4,7,tzinfo=timezone.utc).timestamp())
        source=self.source([dict(id=1,name='João Silva',dateOfBirthTimestamp=birthday),dict(id=2,name='José Silva',dateOfBirthTimestamp=birthday+86400)])
        result=radar_identity.resolve(dict(club='Chapecoense',league='bra.1',display_name='J. Silva'),source)
        self.assertEqual(result['id'],1)

    def test_nickname_can_resolve_by_unique_birth_in_confirmed_squad(self):
        self.identity.return_value=dict(birth='2003-04-07')
        source=self.source([dict(id=1,name='Nome completo diferente',dateOfBirthTimestamp=1049673600)])
        self.assertEqual(radar_identity.resolve(self.context(),source)['id'],1)

    def test_radar_endpoint_refuses_name_only_requests(self):
        with patch('routes.club_routes.resolve_player') as global_search:
            result=app.test_client().post('/api/radar/player',json={'player_name':'Kauan'})
        self.assertEqual(result.status_code,400)
        global_search.assert_not_called()

    def test_radar_endpoint_resolves_by_match_team(self):
        source=self.source([dict(id=1198003,name='Kauan',position='D')])
        with patch('routes.club_routes.sofa',source),patch('routes.club_routes.build_dossier',return_value=dict(id=1198003,name='Kauan',stats=[])),patch('routes.club_routes.market.match_player',return_value=None),patch('routes.club_routes.resolve_player') as global_search:
            result=app.test_client().post('/api/radar/player',json=dict(radar_context=self.context()))
        self.assertEqual(result.status_code,200)
        self.assertEqual(result.json['id'],1198003)
        global_search.assert_not_called()
