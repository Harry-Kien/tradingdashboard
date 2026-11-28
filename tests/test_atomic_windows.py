"""Windows reader giữ handle: việc lưu vẫn nguyên tử và giới hạn thời gian chờ."""
import json
import os
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from so_cong_khai import luu_ben


class AtomicSave(unittest.TestCase):
    def test_sharing_violation_retries_without_changing_existing_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'settings.json'
            p.write_text('{"old":true}', encoding='utf-8')
            replace = os.replace
            calls = []

            def busy(source, target):
                calls.append(1)
                self.assertEqual(json.loads(p.read_text()), {'old': True})
                if len(calls) < 3:
                    e = PermissionError('Windows sharing violation')
                    e.winerror = 32
                    raise e
                return replace(source, target)

            with patch.object(luu_ben.os, 'replace', side_effect=busy), patch.object(luu_ben.time, 'sleep'):
                luu_ben.ghi_json(p, {'new': True})
            self.assertEqual(json.loads(p.read_text()), {'new': True})
            self.assertEqual(len(calls), 3)
            self.assertEqual(list(Path(tmp).glob('*.tmp')), [])

    def test_persistent_access_denied_is_bounded_and_keeps_old_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'settings.json'
            p.write_text('{"old":true}', encoding='utf-8')
            e = PermissionError('Access denied')
            e.winerror = 5
            with patch.object(luu_ben.os, 'replace', side_effect=e) as replace, patch.object(luu_ben.time, 'sleep') as sleep:
                with self.assertRaises(PermissionError):
                    luu_ben.ghi_json(p, {'new': True})
            self.assertEqual(replace.call_count, 6)
            self.assertEqual(sleep.call_count, 5)
            self.assertEqual(json.loads(p.read_text()), {'old': True})
            self.assertEqual(list(Path(tmp).glob('*.tmp')), [])

    def test_other_permission_errors_are_not_retried(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(luu_ben.os, 'replace', side_effect=PermissionError('denied')) as replace, patch.object(luu_ben.time, 'sleep') as sleep:
                with self.assertRaises(PermissionError):
                    luu_ben.ghi_json(Path(tmp) / 'settings.json', {'x': 1})
            self.assertEqual(replace.call_count, 1)
            sleep.assert_not_called()

    @unittest.skipUnless(os.name == 'nt', 'Cần Windows')
    def test_real_windows_reader_can_release_handle_before_atomic_replace(self):
        import ctypes
        from ctypes import wintypes
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
        kernel.CreateFileW.restype = wintypes.HANDLE
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel.CloseHandle.restype = wintypes.BOOL
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'settings.json'
            p.write_text('{"old":true}', encoding='utf-8')
            # GENERIC_READ, FILE_SHARE_READ|WRITE, OPEN_EXISTING; DELETE không được chia sẻ.
            handle = kernel.CreateFileW(str(p), 0x80000000, 3, None, 3, 0x80, None)
            self.assertNotEqual(handle, wintypes.HANDLE(-1).value)
            timer = threading.Timer(.04, lambda: kernel.CloseHandle(handle))
            timer.start()
            try:
                luu_ben.ghi_json(p, {'new': True})
            finally:
                timer.join()
            self.assertEqual(json.loads(p.read_text()), {'new': True})
