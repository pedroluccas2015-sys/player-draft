import unittest
from urllib.parse import parse_qs, urlparse
from unittest.mock import patch
from app import app


def row(player_id, rating, position='F', appearances=1):
    return dict(player=dict(id=player_id,name=f'Atleta {player_id}',position=position),team=dict(name='Clube'),rating=rating,appearances=appearances,goals=0,assists=0)


class RankingTests(unittest.TestCase):
    def setUp(self):
        self.client=app.test_client()
        cached=patch('routes.ranking_routes.cache')
        self.cache=cached.start()
        self.cache.get.return_value=None
        self.addCleanup(cached.stop)

    def response(self, rows, position='all'):
        with patch('routes.ranking_routes.sofa',side_effect=[{'seasons':[{'id':99,'year':'2026'}]},{'results':rows,'pages':1}]) as source:
            result=self.client.get(f'/api/rankings?league_id=325&position={position}')
            calls=source.call_args_list
        self.assertEqual(result.status_code,200)
        return result.json,calls

    def test_all_positions_are_sorted_then_limited_to_five(self):
        data,calls=self.response([row(i,6+i/10) for i in range(1,9)])
        self.assertEqual([p['id'] for p in data['players']],[8,7,6,5,4])
        query=parse_qs(urlparse(calls[1].args[0]).query)
        self.assertNotIn('group',query)
        self.assertEqual(query['limit'],['20'])
        self.assertIn('appearances',query['fields'][0])
        self.assertNotIn('filters',query)

    def test_every_position_is_filtered_upstream_before_top_five(self):
        for position in ['G','D','M','F']:
            with self.subTest(position=position):
                data,calls=self.response([row(i,8-i/100,position) for i in range(1,8)],position)
                self.assertEqual(len(data['players']),5)
                self.assertTrue(all(p['position']==position for p in data['players']))
                query=parse_qs(urlparse(calls[1].args[0]).query)
                self.assertEqual(query['filters'],[f'position.in.{position}'])

    def test_highest_rating_is_not_excluded_by_old_global_match_cutoff(self):
        data,_=self.response([row(1,9,appearances=1)]+[row(i,8-i/100,appearances=30) for i in range(2,8)])
        self.assertEqual(data['players'][0]['id'],1)
        self.assertEqual(data['minimum_matches'],1)

    def test_missing_and_invalid_ratings_are_not_ranked(self):
        data,_=self.response([row(1,None),row(2,float('nan')),row(3,0),row(4,12),row(5,8,appearances=0),row(6,7.5)])
        self.assertEqual([p['id'] for p in data['players']],[6])
        self.assertIn('1 atleta(s)',data['notice'])

    def test_pagination_is_used_if_first_page_has_fewer_than_five_valid_scores(self):
        with patch('routes.ranking_routes.sofa',side_effect=[{'seasons':[{'id':99,'year':'2026'}]},{'results':[row(1,9),row(2,8.9)],'pages':2},{'results':[row(3,8.8),row(4,8.7),row(5,8.6)],'pages':2}]) as source:
            r=self.client.get('/api/rankings?league_id=325&position=F')
        self.assertEqual(len(r.json['players']),5)
        self.assertEqual(parse_qs(urlparse(source.call_args_list[-1].args[0]).query)['offset'],['20'])

    def test_previous_available_season_is_labeled(self):
        with patch('routes.ranking_routes.sofa',side_effect=[{'seasons':[{'id':100,'year':'2027'},{'id':99,'year':'2026'}]},{'results':[],'pages':1},{'results':[row(i,8) for i in range(1,6)],'pages':1}]):
            r=self.client.get('/api/rankings?league_id=325&position=F')
        self.assertTrue(r.json['fallback_season'])
        self.assertEqual(r.json['season'],'2026')

    def test_duplicates_do_not_fill_the_five_places(self):
        data,_=self.response([row(1,9),row(1,9),row(2,8.9),row(3,8.8),row(4,8.7),row(5,8.6)])
        self.assertEqual(len({p['id'] for p in data['players']}),5)

    def test_invalid_position_does_not_call_provider(self):
        with patch('routes.ranking_routes.sofa') as source:
            self.assertEqual(self.client.get('/api/rankings?position=invalid').status_code,400)
            source.assert_not_called()
