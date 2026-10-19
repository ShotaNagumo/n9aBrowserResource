"""Names resolve to explicit master IDs, never picture-book numbers or guesses."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import editor_choices as c
import update_masters as m

MASTER = dict(api_mst_ship=[dict(api_id=9,api_name='吹雪',api_ctype=12,api_sort_id=111,api_sortno=11),
                            dict(api_id=10,api_name='白雪',api_ctype=12,api_sort_id=121),
                            dict(api_id=999,api_name='新艦',api_ctype=150,api_sort_id=9991)],
              api_mst_stype=[dict(api_id=2,api_name='駆逐艦')],api_mst_mission=[dict(api_id=2,api_name='長距離練習航海')],
              api_mst_slotitem=[dict(api_id=14,api_name='ソナー',api_type=[0,7,14,18])],
              api_mst_slotitem_equiptype=[dict(api_id=14,api_name='ソナー類')],private='must not copy')


class ChoiceTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);self.root=Path(temp.name)
        m.atomic(self.root/'data/combat-reference.json',m.encoded(dict(enums=dict(ShipId={'Fubuki':9,'Shirayuki':10},ShipClass={'Fubuki':12},EquipmentId={'Sonar':14}))))

    def cache(self):
        normalized=c.normalize(MASTER)
        m.atomic(self.root/'local/manual-editor/choices.json',m.encoded(dict(schema=1,source=c.SOURCE,fetchedAt='2026-10-19',choices=normalized)))

    def test_normalization_keeps_only_names_and_internal_ids(self):
        data=c.normalize(dict(api_data=MASTER))
        self.assertEqual(data['ships']['9'],'吹雪')
        self.assertNotIn('11',data['ships'])
        text=json.dumps(data)
        self.assertNotIn('private',text);self.assertNotIn('api_sortno',text)
        self.assertEqual(data['categories']['14'],'ソナー類')
        self.assertEqual(data['missions']['2'],'長距離練習航海')

    def test_cached_japanese_names_override_fallback_and_class_id_is_explicit(self):
        self.cache();result=c.load(self.root)
        self.assertTrue(result['status']['cached'])
        self.assertEqual(result['groups']['ships']['9'],'吹雪')
        self.assertTrue(result['groups']['classes']['12'].startswith('吹雪型'))
        self.assertEqual(result['groups']['classes']['150'],'艦型 150 — 新艦')
        self.assertEqual(result['groups']['missions']['0'],'任意の遠征')

    def test_offline_fallback_and_corrupt_cache_do_not_destroy_files(self):
        result=c.load(self.root);self.assertEqual(result['groups']['ships']['9'],'Fubuki')
        self.assertEqual(result['groups']['types']['2'],'駆逐艦')
        path=self.root/'local/manual-editor/choices.json';m.atomic(path,b'bad cache')
        self.assertFalse(c.load(self.root)['status']['cached']);self.assertEqual(path.read_bytes(),b'bad cache')

    def test_download_failure_keeps_last_names(self):
        self.cache();path=self.root/'local/manual-editor/choices.json';before=path.read_bytes()
        with patch.object(c,'build_opener',side_effect=OSError('offline')):
            with self.assertRaises(OSError):c.refresh(self.root)
        self.assertEqual(path.read_bytes(),before)

    def test_empty_or_wrong_public_master_is_rejected(self):
        for value in ({},dict(api_mst_ship=[]),dict(api_mst_ship='bad')):
            with self.assertRaises(ValueError):c.normalize(value)


if __name__=='__main__':unittest.main()
