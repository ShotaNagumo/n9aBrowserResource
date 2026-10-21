"""Offline contract and recovery tests; tiny synthetic Wiki tables, no network."""
import copy
import json
import sys
import tempfile
import unittest
from urllib.error import HTTPError
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import update_masters as m
import wiki_readers as w

URL='https://wikiwiki.jp/kancolle/test'
MISSION='<table><tr><th>ID</th><th>任務名</th><th>内容</th></tr><tr><td>D2</td><td>遠征任務</td><td>遠征を3回成功させよう！</td></tr></table>'
ENEMY='<table><tr><th>No.</th><th>艦級</th><th>艦種</th><th>Lv</th><th>耐久</th><th>搭載</th></tr><tr><td>1501</td><td>イ級</td><td>駆逐艦</td><td>1</td><td>30</td><td>18</td></tr><tr><td>1502</td><td>ロ級</td><td>駆逐艦</td><td>1</td><td>??</td><td>0</td></tr></table>'


class UpdateTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)/'repo';self.work=self.root/'local/update'
        (self.root/'data').mkdir(parents=True);(self.root/'definitions').mkdir();self.work.mkdir(parents=True)
        values={'quest-catalog.json':dict(schema=1,quests={'301':dict(name='遠征任務',description='古い説明',period=1,tasks=[dict(kind='mission',missionIds=[0],target=3)],legacyCounterKeys=['old-key'],legacyDefinitionHash='0'*64)},fallbacks={},mapAliases=[],arrivalMaps=[]),
                'recurring-quests.json':{},'ship-growth.json':[[9,40,40,89,20,20,49]],
                'enemy-ship-hp.json':dict(schema=1,source={},hp={'1501':20}),
                'enemy-aircraft-slots.json':{'1501':[0,0,0,0,0]}}
        for name,value in values.items():m.atomic(self.root/'data'/name,m.encoded(value))

    def source(self,kind='quests'):return dict(key='test',kind=kind,url=URL)
    def plan(self,text=MISSION,kind='quests'):
        raw=text.encode();m.atomic(self.work/'pages/test.html',raw)
        m.atomic(self.work/'pages/test.json',m.encoded(dict(url=URL,sha256=m.digest(raw),fetchedAt='2026-10-19T00:00:00+00:00')))
        m.plan(dict(sources=[self.source(kind)]),self.work,self.root)
        return m.load(self.work/'review.json')

    def test_reviewed_text_is_not_a_counter_and_daily_window_is_validated(self):
        q=dict(name='装備準備',description='説明',period=4,tasks=[],conditionsText='指定装備と資材を所持する。')
        m.validate_quest(q,None)
        self.assertEqual(q['tasks'],[])
        q['counterPeriod']=1
        m.validate_quest(q,None)
        q['counterPeriod']=4
        with self.assertRaises(ValueError):m.validate_quest(q,None)
        q.pop('counterPeriod');q['conditionsText']=' '
        with self.assertRaises(ValueError):m.validate_quest(q,None)

    def test_apply_preserves_existing_crlf_without_reformatting_unchanged_lines(self):
        target=self.root/'data/quest-catalog.json'
        target.write_bytes(target.read_bytes().replace(b'\n',b'\r\n'))
        data=self.plan();data['proposals'][0]['approved']=True
        m.atomic(self.work/'review.json',m.encoded(data))
        m.apply(self.work/'review.json',self.work,self.root)
        raw=target.read_bytes()
        self.assertIn(b'\r\n',raw)
        self.assertNotIn(b'\n',raw.replace(b'\r\n',b''))

    def test_marriage_and_seasonal_wiki_codes_are_not_dropped(self):
        text='<table><tr><td>WF01</td><td>式の準備</td><td>廃棄2回</td></tr><tr><td>2610B1</td><td>期間限定</td><td>条件</td></tr><tr><td>B1</td><td>継続セル</td><td>~</td></tr></table>'
        records,_=w.parse(text,self.source())
        self.assertEqual([r['wikiId'] for r in records],['WF01','2610B1'])
        self.assertTrue(all('id' not in r for r in records))

    def test_spans_and_english_stat_table(self):
        rows,_=w.read_tables('<table><tr><td rowspan="2">x</td><td colspan="2">y</td></tr><tr><td>1</td><td>2</td></tr></table>')
        self.assertEqual(rows[0],[['x','y','y'],['x','1','2']])
        records,_=w.parse('<table><tr><td>Evasion</td><td>40 / 89</td><td>ASW</td><td>20 / 49</td></tr></table>',dict(kind='friendly',shipId=9,name='吹雪'))
        self.assertEqual(records[0]['evasion'],[40,40,89]);self.assertEqual(records[0]['asw'],[20,20,49])

    def test_enemy_id_and_hp_but_never_infer_slot_counts_from_total(self):
        rows,_=w.parse(ENEMY,self.source('enemies'))
        self.assertEqual(rows[0]['id'],1501);self.assertEqual(rows[0]['hp'],30)
        self.assertNotIn('slots',rows[0]);self.assertIsNone(rows[1]['hp'])

    def test_quest_candidates_match_name_and_keep_migration_metadata(self):
        data=self.plan();p=data['proposals'][0]
        self.assertEqual(p['id'],301);self.assertFalse(p['approved'])
        self.assertEqual(p['after']['native']['tasks'][0]['event'],'mission')
        p['approved']=True;updated,_=m.prepare(data,self.root)
        q=updated['quest-catalog.json']['quests']['301']
        self.assertEqual(q['legacyCounterKeys'],['old-key']);self.assertEqual(q['legacyDefinitionHash'],'0'*64)

    def test_new_wiki_number_does_not_become_game_id(self):
        data=self.plan(MISSION.replace('遠征任務','新規任務').replace('D2','D999'))
        p=data['proposals'][0];self.assertIsNone(p['id']);p['approved']=True
        with self.assertRaises(ValueError):m.prepare(data,self.root)
        p['id']=99991;updated,_=m.prepare(data,self.root)
        self.assertIn('99991',updated['quest-catalog.json']['quests'])
        self.assertEqual(updated['recurring-quests.json']['99991']['period'],4)

    def test_known_sinking_trigger_and_unknown_condition_rejected(self):
        counter=w.draft_counter('敵補給艦を3隻撃沈せよ！')
        self.assertEqual(counter['tasks'][0]['event'],'sink');self.assertEqual(counter['tasks'][0]['ids'],[15])
        q=dict(name='任務',period=4,tasks=[])
        native=dict(name='任務',period=4,tasks=counter['tasks'])
        m.validate_quest(q,native)
        minimal=dict(name='任務',period=4,tasks=[dict(event='mission',target=3)])
        m.validate_quest(q,minimal)
        self.assertEqual(minimal['tasks'][0],dict(event='mission',target=3,ids=[],rank='E',materialTypes=[],required=0))
        native['tasks'][0]['event']='newGameSystem'
        with self.assertRaises(ValueError):m.validate_quest(q,native)
        q['formation']=dict(op='execute',command='unsafe')
        with self.assertRaises(ValueError):m.validate_quest(q,None)

    def test_two_counter_formats_and_unsupported_formation_gating_are_rejected(self):
        q=dict(name='任務',period=4,tasks=[dict(kind='practice',rank='S',target=1)])
        native=dict(name='任務',period=4,tasks=[dict(event='mission',target=3)])
        with self.assertRaises(ValueError):m.validate_quest(q,native)
        q['tasks']=[];q['formation']=dict(op='count',min=1,selector=dict(op='type',values=[2]))
        with self.assertRaises(ValueError):m.validate_quest(q,native)

    def test_enemy_slots_require_five_explicit_counts(self):
        data=self.plan(ENEMY,'enemies');p=data['proposals'][0];p['approved']=True
        p['after']['slots']=[18]
        with self.assertRaises(ValueError):m.prepare(data,self.root)
        p['after']['slots']=[0,0,18,0,0]
        result,_=m.prepare(data,self.root)
        self.assertEqual(result['enemy-aircraft-slots.json']['1501'],[0,0,18,0,0])

    def test_approval_is_required_and_manifest_is_never_changed(self):
        data=self.plan();before=m.baseline(self.root)
        m.apply(self.work/'review.json',self.work,self.root)
        self.assertEqual(m.baseline(self.root),before)
        data['proposals'][0]['approved']=True;m.atomic(self.work/'review.json',m.encoded(data))
        m.apply(self.work/'review.json',self.work,self.root)
        self.assertNotEqual(m.baseline(self.root),before)
        self.assertFalse((self.root/'manifest.json').exists())
        self.assertTrue((self.root/'definitions/master-update-provenance.json').is_file())

    def test_changed_baseline_and_modified_migration_key_are_rejected(self):
        data=self.plan();data['proposals'][0]['approved']=True
        data['proposals'][0]['after']['quest']['legacyDefinitionHash']='1'*64
        with self.assertRaises(ValueError):m.prepare(data,self.root)
        m.atomic(self.root/'data/ship-growth.json',m.encoded([]))
        with self.assertRaises(ValueError):m.prepare(data,self.root)

    def test_repeated_candidate_id_rejected_and_unknown_hp_does_not_erase(self):
        data=self.plan(ENEMY,'enemies');p=data['proposals'][0];p['approved']=True
        self.assertEqual(len(data['proposals']),1)
        data['proposals'].append(copy.deepcopy(p))
        with self.assertRaises(ValueError):m.prepare(data,self.root)

    def test_partial_write_failure_rolls_back_and_crash_can_recover(self):
        data=self.plan();data['proposals'][0]['approved']=True;m.atomic(self.work/'review.json',m.encoded(data))
        before=m.baseline(self.root);real=m.atomic;failed=False
        def fail_once(path,raw):
            nonlocal failed
            if path==self.root/'data/recurring-quests.json' and not failed:failed=True;raise OSError('test failure')
            return real(path,raw)
        with patch.object(m,'atomic',side_effect=fail_once):
            with self.assertRaises(OSError):m.apply(self.work/'review.json',self.work,self.root)
        self.assertEqual(m.baseline(self.root),before)
        def crash(path,raw):
            if path==self.root/'data/recurring-quests.json':raise KeyboardInterrupt()
            return real(path,raw)
        with patch.object(m,'atomic',side_effect=crash):
            with self.assertRaises(KeyboardInterrupt):m.apply(self.work/'review.json',self.work,self.root)
        self.assertTrue((self.work/'journal.json').exists())
        m.restore(self.work,self.root);self.assertEqual(m.baseline(self.root),before)

    def test_failed_fetch_will_not_reuse_old_page_for_a_new_plan(self):
        self.plan()
        with patch.object(m.Fetcher,'allowed',return_value=False):m.fetch(dict(sources=[self.source()]),self.work,True)
        m.plan(dict(sources=[self.source()]),self.work,self.root)
        self.assertEqual(m.load(self.work/'review.json')['proposals'],[])

    def test_rate_limit_stops_remaining_requests_to_the_same_host(self):
        second=dict(self.source(),key='second')
        with patch.object(m.Fetcher,'allowed',return_value=True),patch.object(m.Fetcher,'get',side_effect=HTTPError(URL,429,'rate limited',{},None)) as get:
            failed=m.fetch(dict(sources=[self.source(),second]),self.work,True)
        self.assertEqual(get.call_count,1)
        self.assertEqual(failed,2)

    def test_unknown_host_is_rejected_and_saved_page_can_be_imported(self):
        with self.assertRaises(ValueError):m.url('https://example.com/test')
        with self.assertRaises(ValueError):m.url('http://wikiwiki.jp/kancolle/test')
        page=self.work/'saved.html';page.write_text(MISSION,encoding='utf-8')
        m.fetch(dict(sources=[self.source()]),self.work,imported=('test',page))
        self.assertTrue(m.load(self.work/'fetch-report.json')['sources'][0]['ok'])

    def test_discover_ships_uses_master_id_not_picture_number(self):
        m.atomic(self.work/'discovered-pages.json',m.encoded([dict(name='新艦',url=URL)]))
        m.atomic(self.work/'master.json',m.encoded(dict(api_mst_ship=[dict(api_id=999,api_name='新艦')],private='must not copy')))
        m.discover_ships(dict(schema=1,sources=[]),self.work,self.work/'master.json',self.root)
        output=m.load(self.work/'ship-sources.json')
        self.assertEqual(output['sources'][0]['shipId'],999);self.assertNotIn('private',json.dumps(output))


if __name__=='__main__':unittest.main()
