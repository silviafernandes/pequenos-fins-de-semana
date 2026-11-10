import copy
import json
import math
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import update
from eligibility import assess, classify, haversine_km, mark_session, set_distance
from adapters import organiser_sessions

NOW=datetime(2026,11,10,10,tzinfo=ZoneInfo('Europe/Lisbon'))
ROOT=Path(__file__).resolve().parents[1]
REGISTRY=json.loads((ROOT/'public/data/venues.json').read_text())

def example():
    e={'id':'verified','date':'2026-11-15','start':'10:00','end':None,'minMonths':12,'maxMonths':36,'venue':'Oficina Josefina','title':'Oficina sensorial','sourceUrl':'https://www.oficinajosefina.com/beb%C3%A9s'}
    return mark_session(e,e['sourceUrl'],NOW,'official-programme')

class GeographyTests(unittest.TestCase):
    def test_exact_ctt_origin_and_venue_points(self):
        self.assertEqual(REGISTRY['origin']['address'],'Rua Quatro Caminhos 134, Senhora da Hora')
        self.assertEqual(REGISTRY['origin']['precision'],'venue')
        event=assess(example(),REGISTRY,NOW)
        self.assertEqual(event['validationStatus'],'verified')
        self.assertTrue(6<event['distanceKm']<7)
        self.assertTrue(event['distanceWithinRadius'])
        self.assertIn('coordinateSourceUrl',event['geo'])

    def test_paredes_excluded_and_unknown_location_never_uses_city_centroid(self):
        event=example();event['venue']='Biblioteca Municipal de Paredes'
        event=assess(event,REGISTRY,NOW)
        self.assertEqual(event['validationStatus'],'excluded')
        self.assertGreater(event['distanceKm'],25)
        for name in ['Porto','Matosinhos','Oficina desconhecida','Casa da Música, outra cidade']:
            event=example();event['venue']=name
            event=assess(event,REGISTRY,NOW)
            self.assertEqual(event['validationStatus'],'pending')
            self.assertNotIn('distanceKm',event)

    def test_radius_boundary_is_checked_before_rounding(self):
        origin={'latitude':0,'longitude':0,'id':'ctt-4-caminhos'}
        for distance,allowed in [(14.99999,True),(15.00001,False)]:
            point={'name':'test','aliases':['test'],'latitude':0,'longitude':math.degrees(distance/6371.0088),'precision':'venue','coordinateSourceUrl':'https://example.org/point'}
            registry={'origin':origin,'radiusKm':15,'venues':{'test':point}}
            event={'venue':'test'};set_distance(event,registry)
            self.assertEqual(event['distanceWithinRadius'],allowed)
        self.assertAlmostEqual(haversine_km(origin,origin),0)

    def test_seed_evidence_missing_stale_or_wrong_fields_stays_pending(self):
        for change in ['missing','stale','wrong-date','wrong-source','future-check']:
            event=example()
            if change=='missing':event.pop('sessionEvidence')
            elif change=='stale':event['sessionEvidence']['checkedAt']=(NOW-timedelta(hours=49)).isoformat()
            elif change=='wrong-date':event['date']='2026-11-22'
            elif change=='wrong-source':event['sessionEvidence']['sourceUrl']='https://aggregator.example/event'
            else:event['sessionEvidence']['checkedAt']=(NOW+timedelta(hours=1)).isoformat()
            self.assertEqual(assess(event,REGISTRY,NOW)['validationStatus'],'pending',change)

    def test_weekday_and_missing_time_stay_pending(self):
        for changes in [{'date':'2026-11-16'},{'start':None},{'minMonths':36},{'date':'2027-01-02'}]:
            event=example();event.update(changes)
            self.assertEqual(assess(event,REGISTRY,NOW)['validationStatus'],'pending')

class OfficialProgrammeTests(unittest.TestCase):
    def test_josefina_dates_and_ages_are_per_workshop(self):
        html=(ROOT/'tests/fixtures/josefina-programme.html').read_text()
        events=organiser_sessions(html,'https://www.oficinajosefina.com/beb%C3%A9s',NOW,update.make_event)
        self.assertEqual(len(events),6)
        painting=[e for e in events if e['title']=='Experimentar Pinturas']
        self.assertEqual([(e['date'],e['minMonths']) for e in painting],[('2026-11-22',9)])
        self.assertEqual(len(classify(events,REGISTRY,NOW)['events']),6)
        # Without the published year, no session is inferred from last year's pattern.
        self.assertEqual(organiser_sessions(html.replace('Bebés 2026','Bebés'),'https://www.oficinajosefina.com/beb%C3%A9s',NOW,update.make_event),[])

    def test_music_keeps_two_explicit_sessions_on_same_date_and_unknown_end(self):
        html=(ROOT/'tests/fixtures/music-programme.html').read_text()
        events=organiser_sessions(html,'https://casadamusica.com/event/som-de-ca-e-de-la/',NOW,update.make_event)
        self.assertEqual(len(events),8)
        self.assertEqual({e['start'] for e in events if e['date']=='2026-11-22'},{'10:00','11:30'})
        self.assertTrue(all(e['end'] is None and e['minMonths']==3 for e in events))
        self.assertEqual(len(classify(events,REGISTRY,NOW)['events']),8)
        self.assertEqual(organiser_sessions(html.replace('dos 3 meses aos 6 anos','para famílias'),'https://casadamusica.com/event/som-de-ca-e-de-la/',NOW,update.make_event),[])

    def test_porto_uses_explicit_festival_year_and_two_listed_times(self):
        url='https://www.bibliotecasdoporto.pt/evento/papi-opus-8-espetaculo/'
        html=(ROOT/'tests/fixtures/porto-papi.html').read_text()
        context=(ROOT/'tests/fixtures/porto-festival.html').read_text()
        events=organiser_sessions(html,url,NOW,update.make_event,context)
        self.assertEqual([(e['date'],e['start'],e['end']) for e in events],[('2026-12-19','10:30','11:15'),('2026-12-19','11:30','12:15')])
        self.assertTrue(all(e['minMonths']==18 for e in events))
        self.assertEqual(organiser_sessions(html,url,NOW,update.make_event),[])
        self.assertEqual(organiser_sessions(html,url,NOW,update.make_event,context.replace('2026','')) ,[])

class PipelineTests(unittest.TestCase):
    def test_shared_programme_sessions_keep_their_own_title_age_and_identity(self):
        html=(ROOT/'tests/fixtures/josefina-programme.html').read_text().replace('22 Nov . 10h-11h','15 Nov . 10h-11h')
        source={'name':'Oficina Josefina','url':'https://www.oficinajosefina.com/beb%C3%A9s','priority':1}
        with tempfile.TemporaryDirectory() as directory:
            data=Path(directory);(data/'events.json').write_text(json.dumps({'events':[]}))
            with patch.object(update,'DATA',data),patch.object(update,'fetch',return_value=(html,None)),patch.object(update.time,'sleep'):
                discoveries,events,history,_,_=update.scan([source],{}, {},NOW)
            concurrent=[e for e in events['events'] if e['date']=='2026-11-15']
            self.assertEqual(len(concurrent),2)
            self.assertEqual(len({e['id'] for e in concurrent}),2)
            self.assertEqual({e['title']:e['minMonths'] for e in concurrent},{'Experimentar Cerâmicas':12,'Experimentar Pinturas':9})
            for lead in discoveries['discoveries']:
                matched=[e for e in events['events'] if (e['title'],e['date'],e['start'])==(lead['title'],lead['date'],lead['start'])]
                self.assertEqual(len(matched),1)
                self.assertEqual(lead['minMonths'],matched[0]['minMonths'])
            (data/'events.json').write_text(json.dumps(events))
            with patch.object(update,'DATA',data),patch.object(update,'fetch',return_value=('<html>Programa retirado</html>',None)),patch.object(update.time,'sleep'):
                _,changed,_,_,_=update.scan([source],discoveries,history,NOW)
            self.assertEqual(changed['events'],[])
            self.assertEqual(len(changed['pendingEvents']),6)

    def test_cancelled_event_is_not_imported(self):
        raw={'name':'Música para bebés 0–3 anos','startDate':'2026-11-15T10:00','location':'Casa da Música Porto','eventStatus':'https://schema.org/EventCancelled'}
        self.assertIsNone(update.make_event(raw,'https://casadamusica.com/event/example','Casa da Música',NOW))

if __name__=='__main__': unittest.main()
