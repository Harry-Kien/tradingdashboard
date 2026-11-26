"""Bài kiểm: dựng sổ giả trong thư mục tạm, đọc lại và so số. Chạy: python -m unittest discover -s tests -v"""
import json
import sqlite3
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from so_cong_khai import doc_so, tong_hop, trang  # noqa: E402
from so_cong_khai.__main__ import gom, main  # noqa: E402


def _bot_db(path: Path) -> None:
    con = sqlite3.connect(path)
    con.executescript("""
        CREATE TABLE signals(id TEXT PRIMARY KEY, body TEXT NOT NULL, state TEXT NOT NULL, closed INTEGER NOT NULL,
                             opened TEXT NOT NULL, bar_key TEXT NOT NULL);
        CREATE TABLE outbox(seq INTEGER PRIMARY KEY AUTOINCREMENT, key TEXT UNIQUE NOT NULL, text TEXT NOT NULL,
                            reply_to_key TEXT, status TEXT NOT NULL, message_id INTEGER, error TEXT, created TEXT NOT NULL);""")

    def sig(sid, call, opened, next_tp, closed, keys, status='sent'):
        body = {'id': sid, 'call': call, 'side': 'SELL', 'entry': 3860.4, 'sl': 3880.0, 'ladder': 'R', 'opened': opened,
                'tps': [3850.0, 3840.0, 3830.0]}
        con.execute('INSERT INTO signals VALUES(?,?,?,?,?,?)',
                    (sid, json.dumps(body), json.dumps({'stop': 3880.0, 'next_tp': next_tp, 'closed': closed, 'last_seen': None}),
                     int(closed), opened, sid))
        for k in [f'signal:{sid}'] + [f'{sid}:{x}' for x in keys]:
            con.execute('INSERT INTO outbox(key,text,status,created) VALUES(?,?,?,?)', (k, '', status, opened))

    sig('A1', 1, '2026-11-16T10:00:00+00:00', 3, True, ['TP1', 'TP2', 'TP3', 'DONE'])      # đủ TP
    sig('A2', 2, '2026-11-17T10:00:00+00:00', 0, True, ['SL'])                                # SL trắng
    sig('A3', 3, '2026-11-18T10:00:00+00:00', 1, True, ['TP1', 'SL'])                         # TP1 rồi SL
    sig('A4', 4, '2026-11-19T10:00:00+00:00', 0, False, [])                                   # đang mở, chưa có TP
    sig('A5', 0, '2026-11-19T11:00:00+00:00', 0, True, ['SL'])                                # không đánh số: bỏ
    sig('A6', 5, '2026-11-19T12:00:00+00:00', 0, True, ['SL'], status='failed')               # bài gốc không lên: bỏ
    sig('A7', 6, '2026-11-24T10:00:00+00:00', 2, False, ['TP1', 'TP2'])                       # tuần sau
    con.commit()
    con.close()


# Dạng cột gọn (EA M). Vốn: 100 → 130 → 110 → 160; sụt lớn nhất 20 từ đỉnh 130.
EA_CSV = """time_server,event,equity,detail
2026.11.14 14:09:17,init,100.00,v1.001 lots=0.01 tp=100 sl=75
2026.11.16 20:00:00,sell,100.00,lots=0.01 price=3860.00 sl=3935.00 tp=3760.00
2026.11.17 03:00:00,trail,120.00,sl 3935.00 -> 3850.00
2026.11.17 05:00:00,closed,130.00,trail pnl=30.00
2026.11.18 10:00:00,sell,130.00,lots=0.01 price=3820.00 sl=3895.00 tp=3720.00
2026.11.18 20:00:00,sell,130.00,reentry lots=0.02 price=3800.00 sl=3875.00 tp=3700.00
2026.11.19 01:00:00,closed,110.00,sl pnl=-20.00
2026.11.20 09:00:00,sell,160.00,lots=0.02 price=3700.00 sl=3775.00 tp=3600.00
"""

# Dạng cột đầy đủ (EA E, I, BB).
EA_DAY_DU = """time_server,event,bid,ask,spread_usd,atr,reason,lots,sl,tp,retcode,equity,lock,req_price,fill_price
2026.11.16 07:00:00,init,4000,4000.2,0.2,0,version=0.4.9 lock=0,0.00,0.00,0.00,0,50000.00,0,0.00,0.00
2026.11.16 08:00:00,sell,3975,3975.2,0.2,10,E n=40 trend=-1,0.03,4030.50,0.00,0,50010.00,0,3975.00,3974.92
2026.11.17 01:35:11,closed,3990,3990.2,0.2,10,sl net=-80.39,0.03,0.00,0.00,0,49900.00,0,0.00,0.00
2026.11.18 04:00:00,buy,3788,3788.2,0.2,10,E n=40 trend=1,0.02,3753.50,0.00,0,49950.00,0,3788.10,3788.06
2026.11.18 06:00:00,balance,0,0,0,0,deposit_or_withdrawal=100.00,0.00,0.00,0.00,0,50050.00,0,0.00,0.00
"""


def _chain(recs):
    prev = '0' * 8
    for i, r in enumerate(recs, 1):
        r.update(stt=i, hash_truoc=prev, hash=f'h{i:07d}')
        prev = r['hash']
    return '\n'.join(json.dumps(r, ensure_ascii=False) for r in recs) + '\n'


class SoTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)
        _bot_db(self.d / 'bot.db')
        (self.d / 'EA_M_1_events.csv').write_text(EA_CSV, encoding='utf-8')
        (self.d / 'EA_E_1_events.csv').write_text(EA_DAY_DU, encoding='utf-8')
        (self.d / 'xh.jsonl').write_text(_chain([
            {'loai': 'tin_hieu', 'nen_dong_utc': '2026-11-16T17:00:00+00:00', 'huong': 'BAN', 'gia_vao': 3863.79, 'sl': 3883.79, 'tp': 3858.79},
            {'loai': 'ket_qua', 'tin_hieu_stt': 1, 'ket_thuc': 'tp', 'usd': 5.0, 't_dong': '2026-11-16T17:48:00+00:00'},
            {'loai': 'tin_hieu', 'nen_dong_utc': '2026-11-17T07:15:00+00:00', 'huong': 'MUA', 'gia_vao': 3877.42, 'sl': 3857.42, 'tp': 3882.42},
            {'loai': 'ket_qua', 'tin_hieu_stt': 3, 'ket_thuc': 'sl', 'usd': -20.0, 't_dong': '2026-11-17T09:00:00+00:00'},
            {'loai': 'tin_hieu', 'nen_dong_utc': '2026-11-20T16:15:00+00:00', 'huong': 'BAN', 'gia_vao': 3555.53, 'sl': 3575.53, 'tp': 3550.53},
        ]), encoding='utf-8')
        dd = [{'loai': 'goi', 'tra_loi_goc': json.dumps({'hanh_dong': 'MUA'})},
              {'loai': 'ket_qua', 'trang_thai': 'da_dong', 'gia_khop': 3691.86, 't_khop': '2026-11-19T15:45:53+00:00',
               't_dong': '2026-11-19T15:57:00+00:00', 'ket_thuc': 'sl', 'r': -1.02},
              {'loai': 'goi', 'tra_loi_goc': json.dumps({'hanh_dong': 'DUNG_NGOAI'})}]
        recs = [json.loads(x) for x in _chain(dd).splitlines()]
        recs[1]['goi_hash'] = recs[0]['hash']
        (self.d / 'dd.jsonl').write_text('\n'.join(json.dumps(r) for r in recs) + '\n', encoding='utf-8')
        self.cfg = {'ten': 'Thử', 'bot_db': str(self.d / 'bot.db'),
                    'tai_khoan': [{'ten': 'Demo nhỏ', 'ea': [{'ten': 'EA M', 'tep': str(self.d / 'EA_M_*_events.csv')}]},
                                  {'ten': 'Demo lớn', 'ea': [{'ten': 'EA E', 'tep': str(self.d / 'EA_E_*_events.csv')}]}],
                    'bong_xu_huong': str(self.d / 'xh.jsonl'), 'bong_dinh_day': str(self.d / 'dd.jsonl'), 'thu_muc_ra': str(self.d / 'out')}
        self.w = tong_hop.tuan_theo_ma('2026-W47')

    def tearDown(self):
        self.tmp.cleanup()

    # ---- bot
    def test_bot_chi_dem_lenh_da_len_nhom(self):
        calls = doc_so.doc_bot(str(self.d / 'bot.db'))
        self.assertEqual([c['call'] for c in calls], [1, 2, 3, 4, 6])
        self.assertEqual([c['exit'] for c in calls], ['DONE', 'SL', 'SL', None, None])
        s = tong_hop.tom_bot(calls)
        self.assertEqual((s['n'], s['closed'], s['open'], s['decided']), (5, 3, 2, 4))
        self.assertEqual((s['tp1'], s['sl0'], s['full'], s['levels']), (3, 1, 1, [3, 2, 1]))
        self.assertFalse(s['enough'])

    def test_bot_theo_tuan(self):
        s = tong_hop.tom_bot(doc_so.doc_bot(str(self.d / 'bot.db')), *self.w)
        self.assertEqual((s['n'], s['closed'], s['tp1'], s['sl0']), (4, 3, 2, 1))

    def test_bot_mo_chi_doc(self):
        con = sqlite3.connect('file:' + (self.d / 'bot.db').as_posix() + '?mode=ro', uri=True)
        with self.assertRaises(sqlite3.OperationalError):
            con.execute('DELETE FROM signals')
        con.close()

    # ---- EA
    def test_ea_dang_gon(self):
        ea = doc_so.doc_ea(str(self.d / 'EA_M_*_events.csv'))
        self.assertEqual(ea['version'], 'v1.001')
        self.assertEqual([(t['side'], t['lots'], t['pnl'], t['reason']) for t in ea['trades']],
                         [('SELL', 0.01, 30.0, 'trail'), ('SELL', 0.02, -20.0, 'sl')])
        self.assertEqual(ea['open']['entry'], 3700.0)
        self.assertEqual([o['entry'] for o in ea['orphans']], [3820.0])      # lệnh vào không có dòng đóng: không được nuốt mất
        self.assertEqual((ea['first_equity'], ea['last_equity'], len(ea['curve'])), (100.0, 160.0, 8))

    def test_ea_dang_day_du(self):
        ea = doc_so.doc_ea(str(self.d / 'EA_E_*_events.csv'))
        self.assertEqual(ea['version'], '0.4.9')
        self.assertEqual([(t['side'], t['lots'], t['entry'], t['pnl'], t['reason']) for t in ea['trades']],
                         [('SELL', 0.03, 3974.92, -80.39, 'sl')])
        self.assertEqual((ea['open']['side'], ea['open']['entry'], ea['open']['sl']), ('BUY', 3788.06, 3753.5))
        self.assertEqual([d[1] for d in ea['deposits']], [100.0])

    def test_chi_so_tai_khoan(self):
        s = tong_hop.tom_tai_khoan([('EA M', doc_so.doc_ea(str(self.d / 'EA_M_*_events.csv')))])
        self.assertEqual((s['n'], s['win'], s['loss']), (2, 1, 1))
        self.assertEqual((s['gross_profit'], s['gross_loss'], s['pnl']), (30.0, -20.0, 10.0))
        self.assertAlmostEqual(s['profit_factor'], 1.5)
        self.assertAlmostEqual(s['max_dd'], 20.0)                       # đỉnh 130 → 110
        self.assertAlmostEqual(s['max_dd_pct'], 20 / 130)
        self.assertAlmostEqual(s['recovery'], 0.5)
        self.assertAlmostEqual(s['avg_hold_h'], 7.0)                    # 9 giờ và 5 giờ
        self.assertEqual((s['sell'], s['buy']), ((2, 10.0), (0, 0)))
        self.assertEqual([round(v, 2) for _, v in s['daily']], [30.0, -20.0])
        self.assertAlmostEqual(s['unexplained'], 50.0)                  # vốn +60, lệnh đã đóng +10
        self.assertEqual((len(s['opens']), len(s['orphans']), s['per_ea'][0]['entries']), (1, 1, 4))

    def test_nap_rut_khong_tinh_la_sut_von(self):
        ea = doc_so.doc_ea(str(self.d / 'EA_E_*_events.csv'))
        ea['curve'] += [(ea['curve'][-1][0].replace(hour=9), 50030.0)]          # sau lần nạp: 50.050 → 50.030
        s = tong_hop.tom_tai_khoan([('EA E', ea)])
        self.assertEqual((s['first_equity'], s['last_equity']), (50050.0, 50030.0))
        self.assertAlmostEqual(s['max_dd'], 20.0)                               # không phải 110 (50.010 → 49.900 trước lần nạp)
        self.assertEqual((s['before']['min'], s['before']['max']), (49900.0, 50010.0))
        self.assertIn('tính từ lần nạp/rút tiền demo gần nhất', trang._khoi_tai_khoan({'id': 'x', 'ten': 'Demo', 'loi': [], 'tom': s}))

    def test_chua_co_lenh_thua_thi_khong_bia_he_so(self):
        ea = doc_so.doc_ea(str(self.d / 'EA_M_*_events.csv'))
        ea['trades'] = ea['trades'][:1]
        s = tong_hop.tom_tai_khoan([('EA M', ea)])
        self.assertIsNone(s['profit_factor'])
        acc = {'id': 'tk-1', 'ten': 'Demo', 'loi': [], 'tom': s}
        self.assertIn('Chưa có lệnh thua nào đã đóng', trang._khoi_tai_khoan(acc))

    def test_nhieu_ea_chung_tai_khoan(self):
        s = tong_hop.tom_tai_khoan([('EA M', doc_so.doc_ea(str(self.d / 'EA_M_*_events.csv'))),
                                    ('EA E', doc_so.doc_ea(str(self.d / 'EA_E_*_events.csv')))])
        self.assertEqual([t['ea'] for t in s['rows']], ['EA E', 'EA M', 'EA M'])     # xếp theo giờ đóng: 01:35, 05:00 ngày 17, rồi ngày 19
        self.assertEqual([p['ten'] for p in s['per_ea']], ['EA M', 'EA E'])
        self.assertEqual(len(s['opens']), 2)

    # ---- chạy bóng
    def test_xu_huong(self):
        sx = doc_so.doc_bong_xu_huong(str(self.d / 'xh.jsonl'))
        self.assertTrue(sx['chain_ok'])
        s = tong_hop.tom_xu_huong(sx)
        self.assertEqual((s['n'], s['closed'], s['win'], s['loss'], s['usd']), (3, 2, 1, 1, -15.0))
        self.assertEqual([v for _, v in s['curve']], [5.0, -15.0])
        self.assertEqual(sx['rows'][1]['side'], 'BUY')

    def test_chuoi_dut_bi_bat(self):
        lines = (self.d / 'xh.jsonl').read_text(encoding='utf-8').splitlines()
        del lines[1]
        (self.d / 'xh.jsonl').write_text('\n'.join(lines) + '\n', encoding='utf-8')
        self.assertFalse(doc_so.doc_bong_xu_huong(str(self.d / 'xh.jsonl'))['chain_ok'])

    def test_dinh_day(self):
        sd = doc_so.doc_bong_dinh_day(str(self.d / 'dd.jsonl'))
        self.assertEqual((len(sd['rows']), sd['rows'][0]['side'], sd['n_candles']), (1, 'BUY', 2))
        self.assertAlmostEqual(tong_hop.tom_dinh_day(sd)['r'], -1.02)

    def test_tuan(self):
        start, end = tong_hop.tuan_chua(datetime(2026, 11, 22, 16, 59, tzinfo=timezone.utc))     # 23:59 Chủ nhật giờ VN
        self.assertEqual((start.isoformat(), (end - start).days), ('2026-11-16T00:00:00+07:00', 7))
        self.assertEqual(tong_hop.tuan_chua(datetime(2026, 11, 22, 17, 0, tzinfo=timezone.utc))[0].day, 23)
        self.assertEqual(self.w[0], start)

    # ---- trang
    def test_trang_va_bai_tuan(self):
        html = trang.trang_html('Thử', datetime(2026, 11, 20, tzinfo=timezone.utc), gom(self.cfg))
        for must in ('TÍN HIỆU', 'DEMO', 'CHẠY BÓNG', 'Không có tài khoản tiền thật', 'chạm SL', 'liền mạch', '+50,00',
                     '1 lệnh vào không có dòng đóng', 'Đường vốn demo', 'Hệ số lợi nhuận', 'class="ln"', 'class="dn gain"',
                     'Mới có 2 lệnh đã đóng', 'lãi lỗ đang treo', 'id="tk-2"', 'EA E 0.4.9'):
            self.assertIn(must, html)
        self.assertNotIn('nan', html.lower().replace('nhanh', ''))
        bai = trang.bai_tuan('Thử', self.w[0], gom(self.cfg, *self.w))
        self.assertIn('TỔNG KẾT TUẦN 47 (16/11–22/11/2026)', bai)
        self.assertIn('gọi 4 lệnh, đã đóng 3', bai)
        self.assertIn('Demo nhỏ (EA M, tài khoản DEMO): đóng 2 lệnh, thắng 1, thua 1, tổng +10,00 USD demo; đang mở 1 lệnh.', bai)
        self.assertIn('không phải kết quả tiền thật', bai)

    def test_so_tai_khoan_khong_len_trang(self):
        (self.d / 'EA_M_1_events.csv').rename(self.d / 'EA_M_XAUUSDp_20261114_98765432_events.csv')
        self.cfg['tai_khoan'][0]['ea'][0]['tep'] = str(self.d / 'EA_M_XAUUSDp_*_events.csv')
        self.assertNotIn('98765432', trang.trang_html('Thử', datetime.now(timezone.utc), gom(self.cfg)))

    def test_nguon_hong_khong_lam_hong_trang(self):
        self.cfg['bot_db'] = str(self.d / 'khong-co.db')
        self.cfg['tai_khoan'][0]['ea'][0]['tep'] = str(self.d / 'khong-co-*.csv')
        d = gom(self.cfg)
        self.assertNotIn('bot', d)
        self.assertIsNone(d['tai_khoan'][0]['tom'])
        self.assertEqual(d['tai_khoan'][0]['loi'][0][0], 'EA M')
        html = trang.trang_html('Thử', datetime.now(timezone.utc), d)
        self.assertIn('Không đọc được', html)
        self.assertIn('Demo lớn', html)

    def test_chay_ca_chuong_trinh(self):
        cfgp = self.d / 'c.json'
        cfgp.write_text(json.dumps(self.cfg), encoding='utf-8')
        self.assertEqual(main(['--cau-hinh', str(cfgp), '--tuan', '2026-W47']), 0)
        self.assertTrue((self.d / 'out' / 'index.html').exists())
        self.assertTrue((self.d / 'out' / 'tong-ket-tuan-2026-W47.txt').exists())
        data = json.loads((self.d / 'out' / 'so-cong-khai.json').read_text(encoding='utf-8'))
        self.assertNotIn('curve', data['tat_ca']['tai_khoan'][0]['tom'])


if __name__ == '__main__':
    unittest.main()
