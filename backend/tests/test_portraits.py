import unittest
from unittest.mock import Mock, patch
from services.portraits import athlete_portrait


def response(content=b'x'*200,content_type='image/png',player=None):
    item=Mock(status_code=200,content=content,headers={'Content-Type':content_type})
    item.json.return_value={'player':player} if player else {}
    return item


class PortraitTests(unittest.TestCase):
    def setUp(self):
        cache=patch('services.portraits.cache')
        self.cache=cache.start()
        self.cache.get.return_value=None
        self.addCleanup(cache.stop)
        session=patch('services.portraits.SESSION')
        self.session=session.start()
        self.addCleanup(session.stop)

    def test_valid_sofa_image_does_not_fetch_identity_or_dossier(self):
        self.session.get.return_value=response()
        self.assertEqual(athlete_portrait(12),(b'x'*200,'image/png'))
        self.assertEqual(self.session.get.call_count,1)
        self.assertTrue(self.session.get.call_args.args[0].endswith('/player/12/image'))

    def test_transparent_pixel_uses_verified_market_image_before_dossier(self):
        self.session.get.side_effect=[response(b'x'*68),response(player={'name':'Atleta','dateOfBirthTimestamp':946684800}),response(b'j'*300,'image/jpeg')]
        with patch('services.portraits.market.match_player',return_value={'photo':'https://img.a.transfermarkt.technology/portrait/header/1.jpg'}) as match:
            self.assertEqual(athlete_portrait(12),(b'j'*300,'image/jpeg'))
            match.assert_called_once_with('Atleta','2000-01-01')
        self.assertEqual(self.session.get.call_count,3)
        self.assertFalse(any('statistics' in call.args[0] for call in self.session.get.call_args_list))

    def test_unconfirmed_identity_does_not_load_another_players_photo(self):
        self.session.get.side_effect=[response(b'x'*68),response(player={'name':'Atleta','dateOfBirthTimestamp':946684800})]
        with patch('services.portraits.market.match_player',return_value=None):
            self.assertIsNone(athlete_portrait(12))
        self.assertEqual(self.session.get.call_count,2)

    def test_market_portrait_host_is_restricted(self):
        self.session.get.side_effect=[response(b'x'*68),response(player={'name':'Atleta','dateOfBirthTimestamp':946684800})]
        with patch('services.portraits.market.match_player',return_value={'photo':'http://127.0.0.1/private'}):
            self.assertIsNone(athlete_portrait(12))
        self.assertEqual(self.session.get.call_count,2)

    def test_cached_photo_needs_no_provider_requests(self):
        self.cache.get.return_value=(b'cached image','image/jpeg')
        self.assertEqual(athlete_portrait(12),(b'cached image','image/jpeg'))
        self.session.get.assert_not_called()


if __name__=='__main__':
    unittest.main()
