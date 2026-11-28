"""Gói nhẹ không gọi phân tích; cache repo giữ dữ liệu và không che lỗi mạng."""
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

import pandas as pd

from so_cong_khai import da_khung_gia as light, da_khung_realtime as rt
from test_chart_pro import node
from test_da_khung_realtime import page


class Light(unittest.TestCase):
    def test_chi_doc_hai_luot_cua_mot_khung_va_khong_goi_phan_tich(self):
        idx = pd.date_range(datetime(2026, 11, 27, tzinfo=timezone.utc), periods=501, freq='min')
        bars = pd.DataFrame({k: [1.1] * 501 for k in ('open', 'high', 'low', 'close')}, index=idx)
        mt = SimpleNamespace(symbol_info_tick=lambda _: SimpleNamespace(bid=1.1, ask=1.1002, time=100, time_msc=100001))
        with patch.object(light.da_ma, '_mt5', return_value=mt), patch.object(light.da_ma, '_hien', return_value={'EURUSDp': SimpleNamespace(digits=5)}), patch.object(light.da_ma, '_nen', side_effect=[bars.iloc[:-1], bars.iloc[-1:]]) as read, patch.object(light.da_ma, '_boi_canh', side_effect=AssertionError('No analysis')):
            j = light.goi({'gia': {}}, 'EURUSDp', 'M1', 400)
        self.assertEqual([(x.args[2], x.args[3]) for x in read.call_args_list], [('M1', 550), ('M1', 1)])
        self.assertEqual(len(j['candles']), 400)
        self.assertEqual(j['tick_ms'], 100001)
        self.assertEqual(j['ema20'][-1], 1.1)
        self.assertGreater(j['dang_chay'][0], j['candles'][-1][0])

    def test_cache_khong_bi_sua_khi_ghep_tick_va_loi_mang_van_tra_loi(self):
        r = node("let fail=false;globalThis.fetch=async()=>{if(fail)throw Error('offline');return{ok:true,json:async()=>({candles:[[100,1,1,1,1]]})}};" + rt.JS + "(async()=>{await DKRT.load('A','M1');const s=DKRT.snapshot(DKRT.peek('A','M1'),'M1');DKRT.tick(s,[2,3,101000]);await new Promise(r=>setImmediate(r));fail=true;let error=false;try{await DKRT.load('A','M1')}catch(e){error=true}console.log(JSON.stringify({cached:DKRT.peek('A','M1').candles[0][4],error}));})();")
        self.assertEqual(r, {'cached': 1, 'error': True})

    def test_quay_lai_ma_vua_xem_ve_ngay_du_dang_cho_mang(self):
        r = page("const o=DK.O[0],m=o.el.querySelector('.dk-ma');m.value='EURUSDp';m.events.change({target:m});await settle();hold=()=>true;m.value='XAUUSDp';m.events.change({target:m});console.log(JSON.stringify({loading:o.loading,ma:o.ma,c:o.cs.at(-1)[4]}));holds.splice(0).forEach(f=>f());", {'v': 2, 'dongMa': 0})
        self.assertEqual(r, {'loading': True, 'ma': 'XAUUSDp', 'c': 100})
