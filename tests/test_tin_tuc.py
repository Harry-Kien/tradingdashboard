"""Bài kiểm cho tin tức (tin_tuc.py), tâm lý thị trường (tam_ly.py) và trang /tin-tuc. Không gọi mạng thật: hàm tải được thay bằng dữ liệu giả."""
from functools import partial
from http_owner import owner_urlopen
import io
import json
import sys
import tempfile
import threading
import unittest
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from so_cong_khai import tam_ly, tin_tuc, trang, web  # noqa: E402

RSS = b"""<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>x</title>
<item><title><![CDATA[Fed holds rates, Powell signals patience; dollar rises]]></title><link>https://vi-du.com/a</link>
<pubDate>Tue, 24 Nov 2026 16:00:29 GMT</pubDate><description><![CDATA[<p>The U.S. central bank &amp; the <b>greenback</b>.</p>]]></description></item>
<item><title>Gold slips as US yields climb</title><link>https://vi-du.com/b</link><pubDate>Tue, 24 Nov 2026 15:00:00 GMT</pubDate></item>
<item><title>Thieu ngay</title><link>https://vi-du.com/c</link></item>
<item><title>Sai link</title><link>javascript:alert(1)</link><pubDate>Tue, 24 Nov 2026 15:00:00 GMT</pubDate></item>
</channel></rss>"""


class TinTucTest(unittest.TestCase):
    def setUp(self):
        tin_tuc._tt.update(nguon={}, nho=None)

    def test_doc_rss_gan_nhan_va_loc_muc_hong(self):
        ds = tin_tuc.doc_rss(RSS, {'id': 'x', 'ten': 'X', 'loai': 'tin'})
        self.assertEqual([x['link'] for x in ds], ['https://vi-du.com/a', 'https://vi-du.com/b'])      # bỏ mục thiếu giờ và đường dẫn không phải http
        a, b = ds
        self.assertEqual(a['t'], '2026-11-24T16:00:29+00:00')
        self.assertEqual(a['tom_tat'], 'The U.S. central bank & the greenback.')                       # bỏ thẻ HTML
        self.assertIn('USD', a['nhan'])
        self.assertTrue(a['quan_trong'])                                                               # "holds rates"
        self.assertFalse(b['quan_trong'])
        self.assertEqual(b['nhan'], ['USD', 'XAU'])                                                    # "US yields" và "Gold"

    def test_gan_nhan_khong_nham_dai_tu_us(self):
        self.assertNotIn('USD', tin_tuc.gan_nhan('Analysts tell us the euro may rise'))
        self.assertEqual(tin_tuc.gan_nhan('Analysts tell us the euro may rise'), ['EUR'])
        self.assertEqual(tin_tuc.gan_nhan('Bank speech', ['GBP']), ['GBP'])                            # nhãn cố định của nguồn

    def test_tu_choi_xml_co_thuc_the(self):
        bom = b'<?xml version="1.0"?><!DOCTYPE r [<!ENTITY a "aaaa">]><rss><channel><item><title>&a;</title></item></channel></rss>'
        with self.assertRaises(ValueError):
            tin_tuc.doc_rss(bom, {'id': 'x', 'ten': 'X'})

    def test_tai_gop_va_nguon_hong(self):
        with tempfile.TemporaryDirectory() as d:
            cfg = {'tin_tuc': {'tep': 'tin.json', 'nguon': [{'id': 'a', 'ten': 'A', 'url': 'u1'}, {'id': 'b', 'ten': 'B', 'url': 'u2'}]}}

            def tai(u):
                if u == 'u2':
                    raise OSError('mất mạng')
                return RSS
            r = tin_tuc.tai(cfg, Path(d), tai_url=tai, now=datetime(2026, 11, 25, tzinfo=timezone.utc))
            self.assertIsNone(r['nguon']['a']['loi'])
            self.assertIn('mất mạng', r['nguon']['b']['loi'])
            x = tin_tuc.lay(cfg, Path(d))
            self.assertEqual(x['tong'], 2)
            self.assertEqual(len(tin_tuc.lay(cfg, Path(d), nhan='XAU')['ds']), 1)
            self.assertEqual(len(tin_tuc.lay(cfg, Path(d), q='powell')['ds']), 1)
            r = tin_tuc.tai(cfg, Path(d), tai_url=tai, now=datetime(2026, 12, 5, tzinfo=timezone.utc))
            self.assertEqual(tin_tuc.lay(cfg, Path(d))['tong'], 0)                                       # quá 7 ngày thì bỏ


def _dong(ma, ngay, cot: dict, n=30):
    r = ['TEN', ngay.replace('-', '')[2:], ngay, ma] + ['0'] * (n - 4)
    for i, v in cot.items():
        r[i] = str(v)
    return ','.join(r)


class TamLyTest(unittest.TestCase):
    def setUp(self):
        tam_ly._tt.update(loi={}, nho=None)

    def test_doc_va_tom_tat_thu_hang(self):
        t0 = datetime(2026, 1, 6)
        van = '\n'.join(_dong('099741', (t0 + timedelta(weeks=i)).date().isoformat(), {7: 100000, 14: 20000 + 1000 * i, 15: 30000}) for i in range(20))
        van += '\n' + _dong('999999', '2026-01-06', {7: 1})                                           # mã không theo dõi: bỏ
        ds = tam_ly.doc_dong(van, 'tff')
        self.assertEqual(len(ds), 20)
        x = tam_ly.tom_tat(ds)[0]
        self.assertEqual((x['nhan'], x['rong'], x['doi'], x['hang'], x['cuc_doan']), ('EUR', 9000, 1000, 100.0, 'mua'))
        self.assertAlmostEqual(x['pct_oi'], 9.0)
        self.assertEqual(tam_ly.doc_dong(van, 'dis'), [])                                             # EUR thuộc báo cáo TFF, không phải tách nhóm

    def test_cap_nhat_tu_nguon_gia_va_danh_dau_so_cu(self):
        tuan = _dong('099741', '2026-11-17', {7: 1000, 14: 600, 15: 100}) + '\n' + _dong('240741', '2026-03-03', {7: 1000, 14: 100, 15: 600})
        b = io.BytesIO()
        with zipfile.ZipFile(b, 'w') as z:
            z.writestr('F.txt', 'Market_and_Exchange_Names,x\n' + _dong('099741', '2026-11-10', {7: 1000, 14: 500, 15: 100})
                       + '\n' + _dong('240741', '2026-02-24', {7: 1000, 14: 100, 15: 500}))
        zb = b.getvalue()
        goi = []

        def tai(url, *a):
            goi.append(url)
            if 'alternative' in url:
                return json.dumps({'data': [{'value': '25', 'value_classification': 'Extreme Fear', 'timestamp': '1'}]}).encode()
            if url.endswith('.zip'):
                return zb
            return tuan.encode('latin-1') if 'FinFut' in url else b''
        with tempfile.TemporaryDirectory() as d:
            cfg = {'tam_ly': {'tep': 'tl.json'}}
            r = tam_ly.cap_nhat(cfg, Path(d), tai=tai, now=datetime(2026, 11, 25, tzinfo=timezone.utc))
            eur = next(x for x in r['cot'] if x['nhan'] == 'EUR')
            self.assertEqual((eur['rong'], eur['doi'], eur['cu']), (500, 100, False))
            self.assertTrue(next(x for x in r['cot'] if x['nhan'] == 'JAPAN')['cu'])                 # Nikkei ngừng báo cáo: số cũ
            self.assertEqual((r['fng']['gt'], r['fng']['nhan']), (25, 'Sợ hãi tột độ'))
            n = len(goi)
            tam_ly.cap_nhat(cfg, Path(d), tai=tai, now=datetime(2026, 11, 25, 1, tzinfo=timezone.utc))
            self.assertEqual(len(goi), n)                                                             # chưa tới hạn: không tải lại


class TrangTinTucTest(unittest.TestCase):
    def test_trang_va_api(self):
        with tempfile.TemporaryDirectory() as d:
            ch = Path(d) / 'cau-hinh.json'
            ch.write_text(json.dumps({'ten': 'Thử', 'gia': {}, 'tin_tuc': {'tep': str(Path(d) / 'tin.json')}, 'tam_ly': {'tep': str(Path(d) / 'tl.json')}}),
                          encoding='utf-8')
            srv = web.tao_may_chu(str(ch), port=0)
            open_owner = partial(owner_urlopen, root=ch.parent)
            threading.Thread(target=srv.serve_forever, daemon=True).start()
            u = f'http://127.0.0.1:{srv.server_address[1]}'
            try:
                html = open_owner(u + '/tin-tuc').read().decode('utf-8')
                for must in ('Tin tức &amp; tâm lý thị trường', 'aria-current="page">Tin tức', 'id="cot"', 'id="tn"', 'không phải tín hiệu'):
                    self.assertIn(must, html)
                j = json.loads(open_owner(u + '/api/tin-tuc?nhan=USD&q=fed').read())
                self.assertEqual(j['ds'], [])
                self.assertTrue(any(n['k'] == 'XAU' for n in j['nhan']))
                t = json.loads(open_owner(u + '/api/tam-ly').read())
                self.assertEqual(t['cot'], [])
            finally:
                srv.shutdown()
                srv.server_close()
                trang.MIEN_TRU = trang.MIEN_TRU_GOC


if __name__ == '__main__':
    unittest.main()
