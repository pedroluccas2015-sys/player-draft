import unittest
from unittest.mock import patch
from services import league_catalog as catalog
from app import app


class LeagueCatalogTests(unittest.TestCase):
    def player(self, **extra):
        p=dict(id=123,name='Atleta',dateOfBirthTimestamp=1104537600,position='F',positionsDetailed=['ST'],
               proposedMarketValueRaw={'value':250000,'currency':'EUR'},country={'name':'Egypt'})
        p.update(extra)
        return catalog.dto(dict(player=p,club='Clube egípcio'),'Egypt',{})

    def test_actual_squad_identity_and_source_are_preserved(self):
        p=self.player()
        self.assertEqual(p['sofa_id'],123)
        self.assertEqual(p['club_country'],'Egypt')
        self.assertEqual(p['market_value_source'],'Sofascore')
        self.assertEqual(p['position_detail'],'Centre-Forward')
        self.assertNotIn('tm_id',p)

    def test_non_eur_estimate_is_not_silently_converted(self):
        p=self.player(proposedMarketValueRaw={'value':250000,'currency':'USD'})
        self.assertIsNone(p['market_value_eur'])
        self.assertFalse(catalog.matches(p,dict(max_value='300000')))

    def test_unknown_age_height_and_position_fail_specific_filters(self):
        p=self.player(dateOfBirthTimestamp=None,positionsDetailed=[])
        for f in [dict(min_age='18'),dict(max_height='190'),dict(position='Centre-Forward')]:
            self.assertFalse(catalog.matches(p,f))

    def test_no_contract_does_not_make_squad_member_free(self):
        p=self.player()
        self.assertFalse(catalog.matches(p,dict(contract='free')))
        self.assertTrue(catalog.matches(p,dict(contract='unknown')))

    def test_known_price_and_position_filters(self):
        p=self.player()
        self.assertTrue(catalog.matches(p,dict(min_value='200000',max_value='250000',position='Centre-Forward')))
        self.assertFalse(catalog.matches(p,dict(max_value='249999')))

    def test_badge_preserves_content_type_and_rejects_html(self):
        with patch('routes.proxy_routes.cache') as cache,patch('routes.proxy_routes.SESSION.get') as get:
            cache.get.return_value=None
            response=get.return_value
            response.status_code=200
            response.content=b'webp bytes'*30
            response.headers={'Content-Type':'image/webp'}
            r=app.test_client().get('/proxy-tournament/808')
            self.assertEqual(r.status_code,200)
            self.assertEqual(r.content_type,'image/webp')
            response.headers={'Content-Type':'text/html'}
            self.assertEqual(app.test_client().get('/proxy-tournament/808').status_code,404)

    def test_small_invalid_logo_is_not_cached_as_a_badge(self):
        with patch('routes.proxy_routes.cache') as cache,patch('routes.proxy_routes.SESSION.get') as get:
            cache.get.return_value=None
            get.return_value.status_code=200
            get.return_value.content=b'x'
            get.return_value.headers={'Content-Type':'image/png'}
            self.assertEqual(app.test_client().get('/proxy-tournament/808').status_code,404)
            cache.set.assert_not_called()


if __name__=='__main__': unittest.main()
