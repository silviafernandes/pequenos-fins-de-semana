import json
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import update
from official_agendas import agenda_links,provider_links,visitmaia_sessions
from eligibility import assess

NOW=datetime(2026,11,22,12,tzinfo=ZoneInfo('Europe/Lisbon'))
URL='https://visitmaia.pt/public/eventos/parada-de-natal-maia-natal-2026'


class OfficialAgendasTests(unittest.TestCase):
    def test_porto_relative_overlay_uses_the_card_title_and_keeps_unknown_title_keywords(self):
        html='<base href="https://www.agenda-porto.pt/"><div data-bl-name="Card. Card Event"><div data-bl-name="Title">Inventário</div><a href="evento/inventario/"></a></div><a href="local/venue/">Local</a><a href="https://example.org/evento/other/">Other</a>'
        self.assertEqual(agenda_links(html,'https://www.agenda-porto.pt/seccao/familias/',NOW),[('https://www.agenda-porto.pt/evento/inventario/','Inventário')])

    def test_municipal_lists_skip_navigation_and_expired_numeric_dates(self):
        html='<a href="/servicos/comunicacao-e-imagem/eventos/sub18">Sub18</a><div class="linl_block"><a href="/evento/old">Antigo</a><div class="dates"><span class="dia">21</span><span class="mes">11</span><span class="ano">26</span></div></div><a href="/evento/baby">Música para bebés</a><a href="/evento/baby#same">Duplicado</a>'
        self.assertEqual(agenda_links(html,'https://www.cm-matosinhos.pt/municipio/agenda',NOW),[('https://www.cm-matosinhos.pt/evento/baby','Música para bebés')])

    def test_culture_and_tourism_profiles_only_keep_their_event_pages(self):
        for base,href in [('https://www.culturamatosinhos.pt/eventos-9','/eventos/evento-81/baby'),('https://www.cm-maia.pt/viver/cultura/noticias-e-eventos','/viver/cultura/evento-2/baby'),('https://visitmaia.pt/public/eventos','/public/eventos/baby')]:
            with self.subTest(base=base):
                links=agenda_links('<a href="'+href+'">Atividade</a><a href="/contactos">Contactos</a>',base,NOW)
                self.assertEqual(len(links),1)
                if 'cm-maia' in base:self.assertEqual(links[0][0],'https://www.cm-maia.pt/viver/cultura/noticias-e-eventos/evento-12/baby')

    def test_provider_following_is_limited_to_explicit_information_links_on_known_hosts(self):
        html='<a href="https://www.bibliotecasdoporto.pt/evento/baby/">Mais info</a><a href="https://example.org/evento/baby/">Mais info</a><a href="https://casadamusica.com/event/other/">Relacionado</a><a href="https://docs.google.com/forms/d/e/form">Inscrever</a>'
        self.assertEqual(provider_links(html,'https://www.agenda-porto.pt/evento/baby/'),['https://www.bibliotecasdoporto.pt/evento/baby/'])

    def test_visit_maia_publishes_the_explicit_all_age_session_with_real_times_and_location(self):
        html=(ROOT/'tests/fixtures/visitmaia-parade.html').read_text()
        events=visitmaia_sessions(html,URL,NOW,update.make_event)
        self.assertEqual(len(events),1)
        event=events[0]
        self.assertEqual((event['date'],event['start'],event['end']),('2026-12-06','17:30','18:30'))
        self.assertEqual(event['ageText'],'Todas as idades')
        self.assertEqual(event['sessionEvidence']['admission'],'all-ages')
        self.assertEqual(event['price'],'Gratuito')
        self.assertEqual(event['status'],'unverified')
        self.assertIsNone(event['bookingUrl'])
        registry=json.loads((ROOT/'public/data/venues.json').read_text())
        self.assertEqual(assess(event,registry,NOW)['validationStatus'],'verified')

    def test_family_wording_three_plus_missing_time_and_conflicting_venue_do_not_publish(self):
        html=(ROOT/'tests/fixtures/visitmaia-parade.html').read_text()
        for old,new in [('Para todas as idades','Para famílias'),('Para todas as idades','A partir dos 3 anos'),('"startTime":"17:30"','"startTime":""'),('"endDate":"2026-12-06"','"endDate":"2027-01-03"'),('"location":"Praça Dr. José Vieira de Carvalho"','"location":"Outro local"'),('"timeZone":"Europe/Lisbon"','"timeZone":"America/New_York"'),('Parada de Natal – Maia Natal 2026</h4>','Cancelada: Parada de Natal – Maia Natal 2026</h4>')]:
            with self.subTest(new=new):self.assertEqual(visitmaia_sessions(html.replace(old,new),URL,NOW,update.make_event),[])

    def test_a_provider_is_parsed_at_its_original_url_in_the_full_scanner(self):
        root='https://www.agenda-porto.pt/seccao/familias/'
        detail='https://www.agenda-porto.pt/evento/som/'
        provider='https://casadamusica.com/event/som-de-ca-e-de-la/'
        pages={root:'<base href="https://www.agenda-porto.pt/"><a href="evento/som/">Som</a>',detail:'<a href="'+provider+'">Mais info</a>',provider:(ROOT/'tests/fixtures/music-programme.html').read_text()}
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(update,'DATA',Path(folder)),patch.object(update,'fetch',side_effect=lambda url,**kw:(pages.get(url),None if url in pages else 'HTTP 404')),patch.object(update.time,'sleep'):
                discoveries,data,_,_,_=update.scan([{'name':'Porto · Agenda Famílias','url':root,'type':'city-agenda'}],{}, {},NOW)
        self.assertGreater(len(data['events']),0)
        self.assertTrue(all(e['sessionEvidence']['sourceUrl']==provider for e in data['events']))
        self.assertGreater(discoveries['sourceIndex']['Porto · Agenda Famílias']['parsedSessions'],0)


if __name__=='__main__':unittest.main()
