"""Manual editor contracts and loopback HTTP boundary, using synthetic masters."""
import copy
import json
import sys
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import master_editor as gui
import update_masters as m


class ManualEditorTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)/'repo'; self.editor = gui.Editor(self.root)
        values = {'quest-catalog.json':dict(schema=1,quests={'301':dict(name='既存任務',description='説明',period=4,tasks=[dict(kind='practice',rank='S',target=3)],legacyCounterKeys=['key'],legacyDefinitionHash='0'*64)},fallbacks={},mapAliases=[],arrivalMaps=[]),
                  'recurring-quests.json':{}, 'ship-growth.json':[[9,40,40,89,20,20,49]],
                  'enemy-ship-hp.json':dict(schema=1,source={},hp={'1501':20}), 'enemy-aircraft-slots.json':{'1501':[0,0,0,0,0]}}
        for name, value in values.items(): m.atomic(self.root/'data'/name, m.encoded(value))

    def payload(self, kind='quest', ident=99991):
        after = dict(quest=dict(name='新規任務',description='全条件を確認',period=4,tasks=[dict(kind='mission',missionIds=[0],target=3)]),native=None)
        if kind == 'friendly': after = dict(growth=[ident,10,10,50,0,9999,9999])
        if kind == 'enemy': after = dict(hp=80,slots=[18,18,0,0,0])
        return dict(kind=kind,id=ident,name='手動艦名',mode='new',revision=self.editor.bootstrap()['revision'],after=after,note='確認済み')

    def save(self, payload):
        p = self.editor.preview(payload); self.editor.save(p['token']); return p

    def test_preview_never_writes_and_confirmed_save_adds_both_data_and_manual_provenance(self):
        before = m.baseline(self.root); payload = self.payload()
        preview = self.editor.preview(payload)
        self.assertEqual(before, m.baseline(self.root)); self.assertIn('新規任務', preview['diff'])
        self.editor.save(preview['token'])
        self.assertEqual(m.load(self.root/'data/quest-catalog.json')['quests']['99991']['tasks'][0]['target'],3)
        proof = m.load(self.root/'definitions/master-update-provenance.json')['records'][0]
        self.assertEqual(proof['source'],dict(kind='manual',note='確認済み'))
        self.assertFalse((self.root/'manifest.json').exists())
        with self.assertRaises(ValueError): self.editor.save(preview['token'])

    def test_explicit_untracked_and_native_counters(self):
        payload = self.payload(); payload['after']['quest']['tasks']=[]
        with self.assertRaises(ValueError): self.editor.preview(payload)
        payload['tracking']='none'; self.save(payload)
        payload=self.payload(ident=99992); payload['after']['quest']['tasks']=[]
        payload['after']['native']=dict(name='撃沈任務',period=4,tasks=[dict(event='sink',target=3,ids=[15])])
        self.save(payload)
        native=m.load(self.root/'data/recurring-quests.json')['99992']
        self.assertEqual(native['tasks'][0]['rank'],'E')

    def test_existing_quest_metadata_is_preserved_and_id_cannot_be_changed(self):
        record=self.editor.record('quest',301)
        payload=dict(record,mode='edit',originalId=301,note='');payload['after']['quest']['description']='更新'
        self.save(payload)
        q=m.load(self.root/'data/quest-catalog.json')['quests']['301']
        self.assertEqual(q['legacyCounterKeys'],['key'])
        payload=dict(self.editor.record('quest',301),mode='edit',originalId=301,note='')
        payload['after']['quest']['legacyDefinitionHash']='1'*64
        with self.assertRaises(ValueError):self.editor.preview(payload)
        payload['id']=302
        with self.assertRaises(ValueError):self.editor.preview(payload)

    def test_new_mode_cannot_overwrite_an_existing_id(self):
        with self.assertRaises(ValueError):self.editor.preview(self.payload(ident=301))
        payload=self.payload();payload['after']['quest']['formation']=dict(op='execute',code='bad')
        with self.assertRaises(ValueError):self.editor.preview(payload)

    def test_friendly_growth_and_name_memo_round_trip(self):
        path=self.root/'data/ship-growth.json';rows=m.load(path);rows.append([1501,0,9999,9999,0,9999,9999]);m.atomic(path,m.encoded(rows))
        self.assertNotIn(1501,[r['id'] for r in self.editor.bootstrap()['lists']['friendly']])
        self.save(self.payload('friendly',999))
        record=self.editor.record('friendly',999)
        self.assertEqual(record['name'],'手動艦名')
        self.assertEqual(record['after']['growth'],[999,10,10,50,0,9999,9999])
        self.assertTrue(any(r[0]==1501 for r in m.load(path)))
        payload=self.payload('friendly',998);payload['after']['growth']=[998,10,9,50,0,9999,9999]
        with self.assertRaises(ValueError):self.editor.preview(payload)

    def test_enemy_slot_validation_and_no_erasure_of_existing_values(self):
        self.save(self.payload('enemy',2501))
        self.assertEqual(self.editor.record('enemy',2501)['after']['slots'],[18,18,0,0,0])
        payload=dict(self.editor.record('enemy',1501),mode='edit',originalId=1501,note='');payload['after']['hp']=None
        with self.assertRaises(ValueError):self.editor.preview(payload)
        payload=self.payload('enemy',2502);payload['after']['slots']=[18]
        with self.assertRaises(ValueError):self.editor.preview(payload)

    def test_stale_preview_or_changed_provenance_cannot_overwrite(self):
        preview=self.editor.preview(self.payload())
        self.save(self.payload('friendly',999))
        with self.assertRaises(ValueError):self.editor.save(preview['token'])
        preview=self.editor.preview(self.payload())
        path=self.root/'definitions/master-update-provenance.json';proof=m.load(path);proof['records'].append(dict(kind='friendly',id=998))
        m.atomic(path,m.encoded(proof))
        with self.assertRaises(ValueError):self.editor.save(preview['token'])

    def test_partial_failure_rolls_back_and_interruption_is_recoverable(self):
        before=m.baseline(self.root);real=m.atomic
        def failing(path, raw):
            if path==self.root/'definitions/master-update-provenance.json':raise OSError('test failure')
            real(path,raw)
        p=self.editor.preview(self.payload())
        with patch.object(m,'atomic',side_effect=failing):
            with self.assertRaises(OSError):self.editor.save(p['token'])
        self.assertEqual(before,m.baseline(self.root))
        def crash(path,raw):
            if path==self.root/'definitions/master-update-provenance.json':raise KeyboardInterrupt()
            real(path,raw)
        p=self.editor.preview(self.payload())
        with patch.object(m,'atomic',side_effect=crash):
            with self.assertRaises(KeyboardInterrupt):self.editor.save(p['token'])
        self.assertTrue(self.editor.bootstrap()['pending']);self.editor.recover()
        self.assertEqual(before,m.baseline(self.root))

    def test_machine_local_paths_are_not_saved_in_public_data(self):
        payload=self.payload();payload['note']='file:'+'//private/secret'
        with self.assertRaises(ValueError):self.editor.preview(payload)

    def test_name_memo_can_be_updated_without_changing_growth(self):
        payload=dict(self.editor.record('friendly',9),mode='edit',originalId=9,note='',name='吹雪')
        before=m.baseline(self.root);self.save(payload)
        self.assertEqual(m.baseline(self.root),before)
        self.assertEqual(self.editor.record('friendly',9)['name'],'吹雪')

    def test_http_requires_session_token_and_same_origin_and_serves_only_known_assets(self):
        server=ThreadingHTTPServer(('127.0.0.1',0),gui.handler(self.editor,'test-token'))
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        self.addCleanup(server.server_close);self.addCleanup(server.shutdown)
        base=f'http://127.0.0.1:{server.server_port}'
        def get(path,headers={}):
            return urlopen(Request(base+path,headers=headers),timeout=5)
        with get('/') as response:self.assertIn(b'test-token',response.read())
        with self.assertRaises(HTTPError) as error:get('/api/bootstrap')
        self.assertEqual(error.exception.code,403)
        with self.assertRaises(HTTPError) as error:get('/api/bootstrap',{'X-Editor-Token':'test-token','Origin':'https://example.com'})
        self.assertEqual(error.exception.code,403)
        with self.assertRaises(HTTPError) as error:get('/api/bootstrap',{'X-Editor-Token':'test-token','Host':'example.com'})
        self.assertEqual(error.exception.code,403)
        with get('/api/bootstrap',{'X-Editor-Token':'test-token'}) as response:
            self.assertEqual(json.load(response)['lists']['quest'][0]['id'],301)
        with self.assertRaises(HTTPError) as error:get('/../data/quest-catalog.json')
        self.assertEqual(error.exception.code,404)


if __name__=='__main__':unittest.main()
