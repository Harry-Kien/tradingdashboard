# -*- coding: utf-8 -*-
"""Webapp giữ cổng độc quyền và tự đứng dậy (27/11/2026).

Lỗi đã gặp: (1) http.server bật SO_REUSEADDR, trên Windows hai webapp mở được cùng cổng 8765 → vòng Telegram, nhật ký chạy đôi;
(2) một phiên dừng webapp để khởi động lại mà bản mới không lên → webapp tắt hẳn cho tới khi có người để ý."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from so_cong_khai import web  # noqa: E402

GOC = Path(__file__).resolve().parent.parent


class CongDocQuyen(unittest.TestCase):
    def test_ban_thu_hai_khong_mo_duoc_cong(self):
        a = web.tao_may_chu(str(GOC / 'cau-hinh.mau.json'), port=0)
        try:
            with self.assertRaises(OSError):
                web.tao_may_chu(str(GOC / 'cau-hinh.mau.json'), port=a.server_address[1])
        finally:
            a.server_close()
        b = web.tao_may_chu(str(GOC / 'cau-hinh.mau.json'), port=a.server_address[1])     # đóng rồi thì mở lại được ngay
        b.server_close()

    def test_mo_cong_truoc_khi_bat_vong_nen(self):
        """Bản thứ hai phải chết ở bước mở cổng, trước khi vòng Telegram hay nhật ký kịp chạy."""
        s = (GOC / 'so_cong_khai' / 'web.py').read_text(encoding='utf-8')
        main = s[s.index('def khoi_dong('):]                                # main gọi khoi_dong; thứ tự mở cổng và bật vòng nằm ở đó
        self.assertLess(main.index('srv = tao_may_chu('), main.index('.start()'))
        self.assertIn('srv = khoi_dong(', s[s.index('def main('):])

    @unittest.skipUnless((GOC / 'TU_CHAY_WEBAPP.bat').is_file(), 'Bản chia sẻ không có trình tự khởi động lại riêng của bản app')
    def test_tep_tu_chay_tu_dung_day_va_khong_chay_trung(self):
        t = (GOC / 'TU_CHAY_WEBAPP.bat').read_text(encoding='utf-8')
        lap = t[t.index(':lap'):]
        self.assertLess(lap.index('LISTENING'), lap.index('python -X utf8 -m so_cong_khai.launch_local'))   # mỗi vòng đều xem cổng trước
        self.assertIn('if %ERRORLEVEL% EQU 0 exit /b 0', lap)                                      # thoát bình thường thì không chạy lại
        self.assertNotIn('if not errorlevel 1', lap)                                               # mã -1 (bị dừng bằng Stop-Process) phải chạy lại
        self.assertIn('goto lap', lap)


if __name__ == '__main__':
    unittest.main()
