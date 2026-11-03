import unittest
from unittest.mock import patch, Mock
from flask import Flask
from routes.team_routes import team_bp


def event(i, state='post', date='2026-11-03T20:00Z', score='0'):
    return dict(id=str(i), date=date, status=dict(type=dict(state=state, completed=state=='post', description='In Progress', shortDetail="72'")), competitions=[dict(competitors=[dict(homeAway=side, score=score, team=dict(id=side, displayName=side)) for side in ['home','away']])])


class ScoreboardTests(unittest.TestCase):
    def setUp(self):
        app = Flask(__name__)
        app.register_blueprint(team_bp)
        self.client = app.test_client()
        self.cached = patch('routes.team_routes.cache').start()
        self.cached.get.return_value = None
        self.addCleanup(patch.stopall)

    def fetch(self, calendar, daily):
        def get(url, **kwargs):
            events = calendar if len(url.split('dates=')[1]) == 6 else daily
            return Mock(json=lambda: dict(events=events))
        with patch('routes.team_routes.SESSION.get', side_effect=get):
            return self.client.get('/api/scoreboard?league=bra.1')

    def test_daily_score_overrides_monthly_snapshot(self):
        result = self.fetch([event(1, 'pre')], [event(1, 'in', score='2')])
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json['matches'][0]['home_score'], '2')
        self.assertTrue(result.json['matches'][0]['is_live'])
        self.assertIn("72'", result.json['matches'][0]['short_status'])
        self.assertEqual(result.headers['Cache-Control'], 'no-store')
        self.assertEqual(self.cached.set.call_args.kwargs['expire'], 15)

    def test_all_live_matches_survive_six_card_limit(self):
        live = [event(i, 'in', date='2026-11-03T18:00Z') for i in range(10)]
        result = self.fetch([event(100+i) for i in range(8)], live)
        self.assertEqual(len(result.json['matches']), 10)
        self.assertTrue(all(m['is_live'] for m in result.json['matches']))

    def test_cached_response_cannot_be_cached_by_browser(self):
        self.cached.get.return_value = dict(matches=[], upcoming=[])
        result = self.client.get('/api/scoreboard')
        self.assertEqual(result.headers['Cache-Control'], 'no-store')

    def test_provider_failure_is_not_cached_as_success(self):
        with patch('routes.team_routes.SESSION.get', side_effect=RuntimeError('offline')):
            self.assertEqual(self.client.get('/api/scoreboard').status_code, 502)
        self.cached.set.assert_not_called()

    def test_invalid_league_is_rejected(self):
        self.assertEqual(self.client.get('/api/scoreboard?league=invalid').status_code, 400)
