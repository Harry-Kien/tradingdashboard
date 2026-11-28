"""Publishing code must not publish the owner's runtime data or credentials."""
import importlib.util
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location('public_export',Path(__file__).resolve().parents[1]/'cong-cu/kiem_tra_ban_cong_khai.py')
M=importlib.util.module_from_spec(spec);spec.loader.exec_module(M)


class PublicExport(unittest.TestCase):
    def test_private_data_is_blocked_but_synthetic_demo_is_allowed(self):
        for path in ('cau-hinh.json','out/report.json','du-lieu/auth.sqlite3','backup/drawings.db','.env','old/key.jsonl'):
            self.assertEqual(M.inspect(path,b'{}'),'private_runtime_file')
        self.assertIsNone(M.inspect('docs/du-lieu/demo.json',b'{"synthetic":true}'))

    def test_tokens_are_detected_without_echoing_their_value(self):
        token=('gh'+'p_')+'a'*30
        self.assertEqual(M.inspect('example.py',token.encode()),'credential_pattern')

    def test_config_marker_variants_are_detected(self):
        marker='C:'+chr(92)+'private'+chr(92)+'rules'
        self.assertEqual(M.inspect('readme.md',marker.replace(chr(92),'/').encode(),{marker}),'private_config_marker')


if __name__=='__main__':unittest.main()
