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

class PlayerAliasTests(unittest.TestCase):
    def dto(self, names, birth=866764800):
        rows=[dict(search_name=name,club_country='Brazil',current_club_name='Clube de Regatas do Flamengo') for name in names]
        index={('__birth__','1997-06-20'):rows}
        entry=dict(player=dict(id=840219,name='Pedro Guilherme',dateOfBirthTimestamp=birth),club='Flamengo')
        with patch.object(catalog.market,'enrich',return_value=dict(tm_id=432895,market_value_eur=20000000,position_detail='Centre-Forward')) as enrich:
            result=catalog.dto(entry,'Brazil',index)
        return result,enrich

    def test_short_name_and_extended_name_share_identity(self):
        result,enrich=self.dto(['pedro'])
        self.assertEqual(result['tm_id'],432895)
        self.assertEqual(result['sofa_id'],840219)
        self.assertEqual(result['club'],'Flamengo')
        enrich.assert_called_once()

    def test_different_birth_date_is_not_joined(self):
        result,enrich=self.dto(['pedro'],birth=866505600)
        self.assertNotIn('tm_id',result)
        enrich.assert_not_called()

    def test_ambiguous_aliases_are_not_joined(self):
        result,enrich=self.dto(['pedro','pedro guilherme'])
        self.assertNotIn('tm_id',result)
        enrich.assert_not_called()

    def test_unrelated_names_are_not_joined_on_birth_alone(self):
        result,enrich=self.dto(['paulo'])
        self.assertNotIn('tm_id',result)
        enrich.assert_not_called()

    def test_one_day_discrepancy_requires_same_club(self):
        result,enrich=self.dto(['pedro'],birth=866678400)
        self.assertEqual(result['tm_id'],432895)
        enrich.assert_called_once()

    def test_one_day_discrepancy_with_different_club_is_not_joined(self):
        row=dict(search_name='pedro',club_country='Brazil',current_club_name='Santos')
        entry=dict(player=dict(id=840219,name='Pedro Guilherme',dateOfBirthTimestamp=866678400),club='Flamengo')
        result=catalog.dto(entry,'Brazil',{('__birth__','1997-06-20'):[row]})
        self.assertNotIn('tm_id',result)


class GeneralIdentityTests(unittest.TestCase):
    def test_alias_rules_apply_to_all_names(self):
        for left,right in [('Pedro Guilherme','Pedro'),('Wawa Christ','Christ Wawa'),
                           ('Sondre Brunstad Fet','Sondre Fet'),('Jeppe Kjaer','Jeppe Kjær'),
                           ('Andrej Đurić','Andrej Djuric')]:
            with self.subTest(left=left):
                self.assertTrue(catalog.compatible_names(left,right))

    def test_minor_spelling_requires_club_confirmation(self):
        self.assertTrue(catalog.compatible_names('Adam Lundqvist','Adam Lundkvist',True))
        self.assertFalse(catalog.compatible_names('Adam Lundqvist','Adam Lundkvist',False))

    def test_twins_and_unrelated_players_remain_separate(self):
        self.assertFalse(catalog.compatible_names('Emil Konradsen Ceide','Mikkel Konradsen Ceide',True))
        self.assertFalse(catalog.compatible_names('Jeppe Okkels','Viktor Bergh',True))


class AuthoritativeSquadTests(unittest.TestCase):
    def catalogue(self):
        return [dict(country='Brazil',players=[dict(club='Botafogo',player=dict(id=1064039,name='Danilo Santos'))])]

    def test_danilo_market_card_is_removed_despite_conflicting_birth_dates(self):
        players=[dict(id='tm:808509',name='Danilo',club='S. A. F. Botafogo',club_country='Brazil',date_of_birth='2001-04-29')]
        self.assertEqual(catalog.market_only_players(players,self.catalogue()),{})

    def test_different_nicknames_do_not_create_extra_cards_in_covered_club(self):
        players=[dict(id='tm:1',name='Apelido diferente',club='Botafogo',club_country='Brazil')]
        self.assertEqual(catalog.market_only_players(players,self.catalogue()),{})

    def test_uncovered_clubs_keep_market_players(self):
        players=[dict(id='tm:1',name='Danilo',club='Clube ainda sem elenco',club_country='Brazil')]
        self.assertEqual(list(catalog.market_only_players(players,self.catalogue())),['tm:1'])

    def test_homonymous_club_in_another_country_is_not_removed(self):
        players=[dict(id='tm:1',club='Botafogo',club_country='Portugal')]
        self.assertEqual(list(catalog.market_only_players(players,self.catalogue())),['tm:1'])

    def test_regional_clubs_are_not_collapsed(self):
        self.assertNotEqual(catalog.club_identity('Botafogo SP'),catalog.club_identity('Botafogo'))

class ClubAliasEvidenceTests(unittest.TestCase):
    def test_multiple_confirmed_players_link_different_club_names(self):
        players=[dict(tm_id=i,club='Corinthians',club_country='Brazil') for i in range(4)]
        rows={i:dict(club_country='Brazil',current_club_name='Sport Club Corinthians Paulista') for i in range(4)}
        aliases=catalog.confirmed_club_aliases(players,rows)
        self.assertIn(('Brazil',catalog.club_identity('Sport Club Corinthians Paulista')),aliases)

    def test_one_transfer_does_not_remove_market_players_of_old_club(self):
        players=[dict(tm_id=1,club='Clube novo',club_country='Brazil')]
        rows={1:dict(club_country='Brazil',current_club_name='Clube antigo')}
        self.assertEqual(catalog.confirmed_club_aliases(players,rows),set())

    def test_alias_accepted_only_for_unique_authoritative_club(self):
        players=[dict(tm_id=i,club='Clube A' if i<3 else 'Clube B',club_country='Brazil') for i in range(6)]
        rows={i:dict(club_country='Brazil',current_club_name='Clube antigo') for i in range(6)}
        self.assertEqual(catalog.confirmed_club_aliases(players,rows),set())
