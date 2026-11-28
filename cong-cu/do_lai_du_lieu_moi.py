# -*- coding: utf-8 -*-
"""Đo lại trên dữ liệu mới: các luật và công thức đã chốt ngày 24/11/2026 có giữ được kết quả trên giá mà không phép đo nào đã nhìn thấy không.
Cách đo và cách kết luận ghi TRƯỚC ở cong-cu/CHUAN_HOA_DANG_KY.md (phần "Đo lại trên dữ liệu mới"). Không chỉnh gì theo dữ liệu mới.

Đo: tám công thức phiếu; luật bot (bản hiện tại và bản "chờ phá đỉnh/đáy"); bốn biến thể lọc lệnh bằng mô hình (học trên 2015–2021, ngưỡng giữ nguyên);
và tóm tắt nhật ký điểm vào thật. Chỉ đọc tệp nến và tệp nhật ký; không nối MT5; mã của bot chỉ bị bọc tạm trong bộ nhớ. Ghi out/du-lieu-moi.json
(trang Kiến thức đọc tệp này) và out/du-lieu-moi.txt. Nên chạy khoảng mỗi tháng.

    python -X utf8 cong-cu/do_lai_du_lieu_moi.py              # từ mốc 25/11/2026
    python -X utf8 cong-cu/do_lai_du_lieu_moi.py --doi-chieu  # tự kiểm: mốc 01/01/2022 phải ra đúng số phần kiểm đã ghi
"""
import argparse
import importlib.util
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

GOC = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(GOC))

MOC = '2026-11-25T00:00:00+00:00'
MOC_L6 = '2026-11-26T00:00:00+00:00'      # bộ lọc L6 chọn đêm 25/11/2026 khi đã nhìn giá tới chiều hôm đó: chỉ tính tín hiệu từ mốc này
MOC_HL = '2026-11-27T00:00:00+00:00'      # hợp lưu H2 của Elliott chọn tối 26/11/2026 khi đã nhìn giá tới lúc đó: chỉ tính tín hiệu từ mốc này
MOC_DOI_CHIEU = '2022-01-01T00:00:00+00:00'
TOI_THIEU = 30
LAN = 2000
TEN_KET = {'chua_du': 'chưa đủ lệnh', 'co_lai': 'vẫn có lãi', 'lo_ro': 'đang lỗ rõ', 'chua_ro': 'chưa phân định'}


def _nap(ten: str):
    spec = importlib.util.spec_from_file_location(ten, GOC / 'cong-cu' / f'{ten}.py')
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def phan_dinh(r, ky_vong: float | None, toi_thieu: int = TOI_THIEU, lan: int = LAN, hat: int = 0) -> dict:
    """Kết luận cho một nhóm lệnh mới theo luật đã đăng ký: dưới `toi_thieu` lệnh thì 'chua_du'; còn lại dùng khoảng tin cậy 90% (bootstrap) của R
    mỗi lệnh: cận dưới > 0 'co_lai', cận trên < 0 'lo_ro', còn lại 'chua_ro'. 'kem_ky_vong': cận trên thấp hơn mức đã đo ở phần kiểm."""
    r = np.asarray(r, dtype=float)
    n = len(r)
    x = {'n': int(n), 'thang': round(float((r > 0).mean() * 100), 1) if n else None, 'r_tb': round(float(r.mean()), 4) if n else None,
         'tong': round(float(r.sum()), 2), 'ky_vong': ky_vong, 'ci90': None, 'kem_ky_vong': False}
    if n < toi_thieu:
        return dict(x, ket='chua_du')
    g = np.random.default_rng(hat)
    tb = r[g.integers(0, n, (lan, n))].mean(axis=1)
    lo, hi = float(np.quantile(tb, 0.05)), float(np.quantile(tb, 0.95))
    ket = 'co_lai' if lo > 0 else 'lo_ro' if hi < 0 else 'chua_ro'
    return dict(x, ci90=[round(lo, 4), round(hi, 4)], ket=ket, kem_ky_vong=bool(ky_vong is not None and hi < ky_vong))


def tom_nhat_ky(ds: list[dict]) -> dict:
    """Tóm tắt nhật ký điểm vào (đã đánh dấu dòng trùng): theo phương pháp và tổng, chỉ lệnh đã có kết quả thắng hoặc thua."""
    nhom: dict = {}
    for x in ds:
        if x.get('trung_voi') or x.get('tt') not in ('thang', 'thua'):
            continue
        for k in (x.get('ten') or x.get('ma'), 'Tất cả'):
            t = nhom.setdefault(k, {'n': 0, 'thang': 0, 'tong_r': 0.0})
            t['n'] += 1
            t['thang'] += x['tt'] == 'thang'
            t['tong_r'] = round(t['tong_r'] + float(x.get('r') or 0.0), 2)
    return nhom


def _khop(a: dict, b: dict) -> bool:
    return (a['n'], a['thang'], round(a['r_tb'], 4) if a['r_tb'] is not None else None) == (b['n'], b['thang'], round(b['r_tb'], 4) if b['r_tb'] is not None else None)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--doi-chieu', action='store_true', help='mốc 01/01/2022 và so với số phần kiểm đã ghi')
    tham = ap.parse_args()
    tu = pd.Timestamp(MOC_DOI_CHIEU if tham.doi_chieu else MOC)
    t0 = time.time()
    LB = _nap('loc_lenh_bot')
    from so_cong_khai import nhat_ky, phieu, phuong_phap as PP                 # noqa: E402
    cfg = json.loads((GOC / 'cau-hinh.json').read_text(encoding='utf-8'))
    cu = json.loads((GOC / 'out' / 'diem-vao.json').read_text(encoding='utf-8'))
    cu_bot = json.loads((GOC / 'out' / 'diem-vao-bot.json').read_text(encoding='utf-8'))
    cu_loc = json.loads((GOC / 'out' / 'loc-lenh-bot.json').read_text(encoding='utf-8'))
    ctx = LB.nap(cfg)
    nho_ctx: dict = {}
    lay = lambda den: ctx if not den else nho_ctx.setdefault(den, LB.nap(cfg, den))     # noqa: E731
    if tham.doi_chieu:                                                  # tự đối chiếu: mỗi phần cắt nến đúng tới mốc cuối của lần đo đã ghi
        ctx_pp, ctx_bot, ctx_loc = lay(cu.get('den')), lay(cu_bot.get('den')), lay(cu_loc.get('den'))
    else:
        ctx_pp = ctx_bot = ctx_loc = ctx
    DV, D, fr = ctx_pp['DV'], ctx_pp['D'], ctx_pp['fr']
    den = ctx['m1'].index[-1]
    KQ: dict = {'luc': datetime.now(timezone.utc).isoformat(), 'tu': tu.isoformat(), 'den': den.isoformat(), 'so_ngay': max(0, (den - tu).days),
                'doi_chieu': tham.doi_chieu, 'muc': []}
    lech = []

    def them(nhom: str, ten: str, r, ky_vong, cu_kiem=None):
        x = dict(phan_dinh(r, ky_vong), nhom=nhom, ten=ten)
        KQ['muc'].append(x)
        if tham.doi_chieu and cu_kiem is not None and not _khop(x, cu_kiem):
            lech.append((ten, {k: x[k] for k in ('n', 'thang', 'r_tb')}, {k: cu_kiem[k] for k in ('n', 'thang', 'r_tb')}))

    # 1. tám công thức phiếu, NGUYÊN như chốt ngày 24/11/2026 (không có bộ lọc L6 thêm sau đó)
    LX = _nap('loc_xu_huong')
    tep_l6 = GOC / 'out' / 'loc-xu-huong.json'
    cu_l6 = json.loads(tep_l6.read_text(encoding='utf-8')) if tep_l6.exists() else None
    tu_l6 = pd.Timestamp(MOC_DOI_CHIEU if tham.doi_chieu else MOC_L6)
    co_l6 = []
    for ma in PP.DS:
        ct = phieu.CONG_THUC[ma]
        loc = tuple(k for k in ct['loc'] if k not in ('L6', 'H1', 'H2'))          # công thức chốt 24/11/2026, trước L6 và hợp lưu
        th = DV.tin_hieu(ma, fr['M15'], fr['H1'])
        bc = DV.boi_canh(D, th, fr['M15'], fr['H4'])
        bo = np.zeros(len(th), bool)
        for v in loc:
            bo |= bc[v]
        df0 = DV.chay(D, th, ma, vao=ct['vao'], sl=ct['sl'], tp=ct['tp'])
        so = df0['so'].to_numpy()
        moi = np.array([pd.Timestamp(th[k]['t']) >= tu for k in so], dtype=bool) if len(so) else np.zeros(0, bool)
        df = df0[~bo[so] & moi]
        them('Công thức phiếu', PP.DS[ma]['ten'], df.loc[df['khop'], 'r'].to_numpy(), cu['pp'][ma]['cuoi']['kiem']['r_tb'], cu['pp'][ma]['cuoi']['kiem'])
        if 'L6' in ct['loc'] and cu_l6 and ma in cu_l6.get('pp', {}):
            co_l6.append(ma)
    # 1b. bản có L6 (đăng ký 26/11/2026), chỉ tín hiệu từ MOC_L6. Tự đối chiếu: cắt nến đúng tới mốc cuối của lần đo L6.
    ctx_l6 = (lay(cu_l6.get('den')) if tham.doi_chieu else ctx) if co_l6 else None
    for ma in co_l6:
        DVx, Dx, frx = ctx_l6['DV'], ctx_l6['D'], ctx_l6['fr']
        ct = phieu.CONG_THUC[ma]
        th = DVx.tin_hieu(ma, frx['M15'], frx['H1'])
        bc = DVx.boi_canh(Dx, th, frx['M15'], frx['H4'])
        bo = np.zeros(len(th), bool)
        for v in ct['loc']:
            bo |= LX.loc_moi(th, frx)['L6'] if v == 'L6' else bc[v]
        d6 = DVx.chay(Dx, th, ma, vao=ct['vao'], sl=ct['sl'], tp=ct['tp'])
        so = d6['so'].to_numpy()
        moi6 = np.array([pd.Timestamp(th[k]['t']) >= tu_l6 for k in so], dtype=bool) if len(so) else np.zeros(0, bool)
        d6 = d6[~bo[so] & moi6]
        k6 = cu_l6['pp'][ma]['bang']['L6']['kiem']
        them('Công thức phiếu có L6 (từ 26/11/2026)', PP.DS[ma]['ten'], d6.loc[d6['khop'], 'r'].to_numpy(), k6['r_tb'], k6)
    # 1c. bản có hợp lưu H2 (đăng ký 26/11/2026), chỉ tín hiệu từ MOC_HL. Tự đối chiếu: cắt nến đúng tới mốc cuối của lần đo hợp lưu.
    tep_hl = GOC / 'out' / 'hop-luu.json'
    cu_hl = json.loads(tep_hl.read_text(encoding='utf-8')) if tep_hl.exists() else None
    co_hl = [ma for ma in PP.DS if 'H2' in phieu.CONG_THUC[ma]['loc'] and cu_hl and ma in cu_hl.get('pp', {})]
    if co_hl:
        HL = _nap('hop_luu')
        ctx_hl = lay(cu_hl.get('den')) if tham.doi_chieu else ctx
        tu_hl = pd.Timestamp(MOC_DOI_CHIEU if tham.doi_chieu else MOC_HL)
        for ma in co_hl:
            DVx, Dx, frx = ctx_hl['DV'], ctx_hl['D'], ctx_hl['fr']
            ct = phieu.CONG_THUC[ma]
            th = DVx.tin_hieu(ma, frx['M15'], frx['H1'])
            bo = HL.bo_loc(ma, th, frx, DVx.boi_canh(Dx, th, frx['M15'], frx['H4']), ct['loc'], DVx)
            dh = DVx.chay(Dx, th, ma, vao=ct['vao'], sl=ct['sl'], tp=ct['tp'])
            so = dh['so'].to_numpy()
            moi_hl = np.array([pd.Timestamp(th[k]['t']) >= tu_hl for k in so], dtype=bool) if len(so) else np.zeros(0, bool)
            dh = dh[~bo[so] & moi_hl]
            kh = cu_hl['pp'][ma]['bang']['H2']['kiem']
            them('Công thức phiếu có hợp lưu H2 (từ 27/11/2026)', PP.DS[ma]['ten'], dh.loc[dh['khop'], 'r'].to_numpy(), kh['r_tb'], kh)
    # 2. luật bot
    L = LB.lenh_bot(ctx_bot)
    D = ctx_bot['D']
    for ten, vao, goc in (('Luật bot · bản hiện tại (vào ngay)', 'V0', cu_bot['A']['moi']['kiem']),
                          ('Luật bot · chờ phá đỉnh/đáy nến tín hiệu', 'V2', cu_bot['C']['bang']['V2']['kiem'])):
        df = DV.chay(D, L['th_all'], 'bot', vao=vao, tp='TL')
        moi = np.array([pd.Timestamp(L['th_all'][k]['t']) >= tu for k in df['so'].to_numpy()], dtype=bool)
        df = df[moi]
        them('Luật bot', ten, df.loc[df['khop'], 'r'].to_numpy(), goc['r_tb'], goc)
    # 3. lọc lệnh bằng mô hình (học trên 2015–2021 như đã đăng ký)
    if ctx_loc is not ctx_bot:
        L = LB.lenh_bot(ctx_loc)
    H = LB.huan_luyen(L)
    moi = L['t_vao'] >= tu.value
    them('Lọc lệnh bằng mô hình', 'Luật bot không lọc (cùng bộ lệnh với mô hình)', L['r'][moi], cu_loc['khong_loc']['kiem']['r_tb'], cu_loc['khong_loc']['kiem'])
    TEN_BT = {'logistic_50': 'Hồi quy logistic, giữ 50%', 'logistic_30': 'Hồi quy logistic, giữ 30%', 'cay_50': 'Cây tăng cường, giữ 50%', 'cay_30': 'Cây tăng cường, giữ 30%'}
    ten_bt = lambda k, c: TEN_BT[k] + (' (bản được chọn)' if k == c.get('chon') else '')     # noqa: E731
    for k, v in H['bien_the'].items():
        giu = v['mo_hinh'].predict_proba(L['X'][moi])[:, 1] >= v['nguong'] if moi.any() else np.zeros(0, bool)
        them('Lọc lệnh bằng mô hình', ten_bt(k, cu_loc), L['r'][moi][giu], cu_loc['bien_the'][k]['kiem']['r_tb'], cu_loc['bien_the'][k]['kiem'])
    # 3b. bản 2 của mô hình lọc lệnh (thêm bạc, Brent, S&P 500, COT): theo dõi trên dữ liệu mới (đăng ký ngày 25/11/2026)
    tep2 = GOC / 'out' / 'loc-lenh-bot-v2.json'
    if tep2.exists():
        cu_loc2 = json.loads(tep2.read_text(encoding='utf-8'))
        V2 = _nap('loc_lenh_bot_v2')
        ctx_l2 = (nho_ctx.setdefault(cu_loc2['den'], LB.nap(cfg, cu_loc2['den'])) if cu_loc2.get('den') else ctx) if tham.doi_chieu else ctx
        Lb = L if ctx_l2 is ctx_loc else LB.lenh_bot(ctx_l2)
        vh = ctx_l2['m1']['close'].resample('1h').last().dropna()
        vh.index = vh.index + pd.Timedelta('1h')
        cot = json.loads((GOC / 'du-lieu' / 'cot-vang.json').read_text(encoding='utf-8'))['ds']
        Fm = V2.dac_trung_moi(Lb['t_vao'], np.array([s['huong'] == 'MUA' for s in Lb['th']]), vh, cot)
        L2 = dict(Lb, F=pd.concat([Lb['F'], Fm], axis=1))
        L2['X'] = L2['F'].to_numpy(dtype=float)
        H2 = LB.huan_luyen(L2)
        moi2 = L2['t_vao'] >= tu.value
        for k, v in H2['bien_the'].items():
            giu = v['mo_hinh'].predict_proba(L2['X'][moi2])[:, 1] >= v['nguong'] if moi2.any() else np.zeros(0, bool)
            them('Lọc lệnh bằng mô hình, bản 2 (liên thị trường)', ten_bt(k, cu_loc2), L2['r'][moi2][giu], cu_loc2['bien_the'][k]['kiem']['r_tb'],
                 cu_loc2['bien_the'][k]['kiem'])
    # 4. nhật ký thật
    KQ['nhat_ky'] = tom_nhat_ky(nhat_ky.danh_dau_trung(nhat_ky._doc(nhat_ky.tep(cfg))))

    if tham.doi_chieu:
        print(f'TỔNG: mốc 01/01/2022 so với số phần kiểm đã ghi · khớp {len(KQ["muc"]) - len(lech)}/{len(KQ["muc"])} mục · Khác chưa giải thích được: {len(lech)}')
        for x in lech:
            print('  ', x)
        if lech and all(x[0].startswith(('Luật bot', 'Hồi quy', 'Cây')) for x in lech):
            print('Chỉ các mục của luật bot lệch: mã hoặc cấu hình của bot đã đổi sau ngày đo 24/11/2026, nên số đo của bot (diem_vao_bot.py, loc_lenh_bot.py) '
                  'không còn ứng với bot đang chạy. Cần đo lại các phần đó trước khi tin bảng đo lại.')
        sys.exit(1 if lech else 0)
    pham_vi = f"từ {tu:%d/%m/%Y} đến {den:%H:%M %d/%m/%Y} UTC ({KQ['so_ngay']} ngày)" if den > tu else f'chưa có giá mới sau mốc {tu:%d/%m/%Y}'
    dong = [f"ĐO LẠI TRÊN DỮ LIỆU MỚI · {pham_vi} · chạy lúc {datetime.now():%H:%M %d/%m/%Y}",
            'Kết luận theo luật ghi trước: dưới 30 lệnh "chưa đủ lệnh"; còn lại theo khoảng tin cậy 90% của R mỗi lệnh', '']
    nhom = None
    for x in KQ['muc']:
        if x['nhom'] != nhom:
            nhom = x['nhom']
            dong.append(f'── {nhom}')
        so = '—' if not x['n'] else f"{x['n']:4d} lệnh · thắng {x['thang']:5.1f}% · {x['r_tb']:+.3f}R · tổng {x['tong']:+.1f}R"
        dong.append(f"  {x['ten'][:52]:52s} {so:48s} → {TEN_KET[x['ket']]}{' · KÉM KỲ VỌNG RÕ' if x['kem_ky_vong'] else ''} (kỳ vọng {x['ky_vong']:+.3f}R)")
    dong.append('\n── Nhật ký điểm vào (lệnh thật đã có kết quả, không tính dòng ghi trùng)')
    for k, t in sorted(KQ['nhat_ky'].items(), key=lambda kv: (kv[0] != 'Tất cả', -kv[1]['n'])):
        dong.append(f"  {k[:52]:52s} {t['n']:4d} lệnh · thắng {t['thang']:3d} ({t['thang'] / t['n'] * 100:5.1f}%) · tổng {t['tong_r']:+.2f}R")
    txt = '\n'.join(dong).replace('.', ',')
    print(txt)
    (GOC / 'out').mkdir(exist_ok=True)
    (GOC / 'out' / 'du-lieu-moi.json').write_text(json.dumps(KQ, ensure_ascii=False, indent=1), encoding='utf-8')
    (GOC / 'out' / 'du-lieu-moi.txt').write_text(txt + '\n', encoding='utf-8')
    print(f'\nGhi out/du-lieu-moi.json và .txt · {time.time() - t0:.0f} giây')
