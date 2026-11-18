import sys
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import update
from source_health import source_health,annotate_sources,health_summary


class CollectionHealthTests(unittest.TestCase):
    def test_accessible_page_does_not_mean_events_were_collected(self):
        self.assertEqual(source_health({'ok':True})['status'],'no-sessions')
        self.assertEqual(source_health({'ok':True,'relevantLinks':2})['status'],'discovery-only')
        self.assertEqual(source_health({'ok':True,'parsedSessions':2})['status'],'collected')

    def test_detail_errors_partial_crawl_and_reviews_are_visible_even_with_sessions(self):
        for flag in [{'detailErrors':[{'error':'404'}]},{'truncated':True}]:
            self.assertEqual(source_health({'ok':True,'parsedSessions':2,**flag})['status'],'partial')
        self.assertEqual(source_health({'ok':True,'reviewNeeded':True,'reviewedSessions':8})['status'],'review-needed')
        self.assertEqual(source_health({'ok':True,'posterCandidates':[{'status':'needs-review'}]})['status'],'review-needed')
        self.assertEqual(source_health({'ok':False,'parsedSessions':8})['status'],'unavailable')

    def test_catalogue_outings_and_counts_use_actual_collection(self):
        sources={'feed':{'ok':True,'readMode':'public-json','eligibleSessions':3},'zoo':{'ok':True,'readMode':'family-outings','outingsCount':0,'reviewNeeded':True}}
        annotate_sources(sources)
        self.assertEqual(health_summary(sources),{'collected':1,'review-needed':1})

    def test_html_base_resolves_real_porto_and_serralves_event_urls(self):
        for host,path,link in [('www.bibliotecasdoporto.pt','programa/','evento/oficina-para-bebes/'),('www.serralves.pt','agenda-serralves/','atividades-serralves/oficina-de-familias/')]:
            links,_=update.links_from(f'<base href="https://{host}/"><a href="{link}">Oficina</a>',f'https://{host}/{path}')
            self.assertEqual(links[0][0],f'https://{host}/{link}')
        links,_=update.links_from('<base href="javascript:bad"><a href="event">Oficina</a>','https://example.org/agenda/')
        self.assertEqual(links[0][0],'https://example.org/agenda/event')

    def test_image_only_and_ver_mais_links_can_be_discovered_by_event_slug(self):
        self.assertTrue(update.possible_link('https://museudoporto.pt/recurso/oficina-para-familias-artistas-ariscas/','Ver mais'))
        self.assertTrue(update.possible_link('https://www.cm-maia.pt/agenda/evento-42/agenda-biblioteca-municipal-nov-26','Agenda Biblioteca Municipal | nov.26'))
        self.assertFalse(update.possible_link('https://example.org/evento/teatro-3-6-anos','Teatro a partir dos 3 anos'))
        self.assertFalse(update.possible_link('https://example.org/contactos','Oficinas para bebés'))
