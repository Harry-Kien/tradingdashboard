# -*- coding: utf-8 -*-
"""Đồng bộ "Mẫu của tôi" và chỉ báo yêu thích của bảng Chỉ báo (bieu_do_chi_bao.py) lên máy chủ (26/11/2026), để mọi trình duyệt, máy tính và
điện thoại mở cùng webapp có cùng mẫu. Bộ chỉ báo đang bật (S.ds) vẫn theo từng máy, vì màn hình điện thoại và máy tính thường cần khác nhau.

Lưu ở du-lieu/mau-chi-bao.json: {'mau': {tên: [chỉ báo…]}, 'sao': [mã chỉ báo…], 'ban': số phiên bản, 'luc': giờ lưu}. Bản còn mẫu gần nhất được giữ ở
mau-chi-bao.truoc.json. Dữ liệu này đi vào HTML của bảng chỉ báo trên mọi máy, nên chỉ nhận đúng định dạng: tên mẫu không có ký tự HTML, mã chỉ báo
chữ thường, giá trị là số hữu hạn, chữ ngắn hoặc mã màu."""
from __future__ import annotations

import json
import math
import re
import threading
import time
from pathlib import Path

from . import telegram_nhom

TOI_DA_MAU = 50
TOI_DA_BYTE = 120_000
_khoa = threading.Lock()


def _tep(goc: Path | None = None, truoc: bool = False) -> Path:
    d = telegram_nhom._tep('x').parent if goc is None else goc / 'du-lieu'
    return d / ('mau-chi-bao.truoc.json' if truoc else 'mau-chi-bao.json')


def doc(goc: Path | None = None) -> dict:
    try:
        x = json.loads(_tep(goc).read_text(encoding='utf-8'))
        if isinstance(x, dict) and isinstance(x.get('mau'), dict):
            return {'mau': x['mau'], 'sao': x.get('sao') or [], 'ban': int(x.get('ban', 0)), 'luc': x.get('luc')}
    except (OSError, ValueError, TypeError):
        pass
    return {'mau': {}, 'sao': [], 'ban': None, 'luc': None}


_MA = re.compile(r'[a-z0-9_]{1,30}')
_KHOA = re.compile(r'[A-Za-z0-9_]{1,30}')
_TEN = re.compile(r'[^<>"&\'`\\]{1,40}')
_CHU = re.compile(r'[A-Za-z0-9_.#%+\- ]{0,40}')


def _gia_tri(v, sau: int = 0):
    if isinstance(v, bool) or v is None:
        return v
    if isinstance(v, (int, float)):
        if not math.isfinite(v):
            raise ValueError('số không hợp lệ')
        return v
    if isinstance(v, str):
        if not _CHU.fullmatch(v):
            raise ValueError('chữ không hợp lệ')
        return v
    if isinstance(v, dict) and sau < 2:
        return {_ten_ts(k): _gia_tri(x, sau + 1) for k, x in v.items()}
    if isinstance(v, list) and sau < 2 and len(v) <= 20:
        return [_gia_tri(x, sau + 1) for x in v]
    raise ValueError('giá trị không hợp lệ')


def _ten_ts(k) -> str:
    if not isinstance(k, str) or not _KHOA.fullmatch(k):
        raise ValueError('tên thông số không hợp lệ')
    return k


def kiem(mau, sao) -> tuple[dict, list]:
    """Chuẩn hóa và kiểm dữ liệu gửi lên; sai thì ValueError."""
    if not isinstance(mau, dict) or len(mau) > TOI_DA_MAU:
        raise ValueError('danh sách mẫu không hợp lệ')
    ra = {}
    for ten, ds in mau.items():
        if not isinstance(ten, str) or not _TEN.fullmatch(ten) or not ten.strip():
            raise ValueError('tên mẫu không hợp lệ')
        if not isinstance(ds, list) or len(ds) > 60:                       # thư viện có 41 chỉ báo; chừa chỗ cho nhiều bản cùng loại
            raise ValueError('mẫu không hợp lệ')
        mot = []
        for x in ds:
            if not isinstance(x, dict) or not isinstance(x.get('k'), str) or not _MA.fullmatch(x['k']):
                raise ValueError('chỉ báo trong mẫu không hợp lệ')
            mot.append({_ten_ts(k): _gia_tri(v) for k, v in x.items()})
        ra[ten] = mot
    if not isinstance(sao, list) or len(sao) > 100 or not all(isinstance(k, str) and _MA.fullmatch(k) for k in sao):
        raise ValueError('danh sách yêu thích không hợp lệ')
    if len(json.dumps(ra, ensure_ascii=False)) > TOI_DA_BYTE:
        raise ValueError('mẫu quá lớn')
    return ra, list(sao)


def luu(mau, sao, goc: Path | None = None, now: float | None = None) -> dict:
    mau, sao = kiem(mau, sao)
    with _khoa:
        cu = doc(goc)
        x = {'mau': mau, 'sao': sao, 'ban': (cu['ban'] or 0) + 1, 'luc': time.time() if now is None else now}
        p = _tep(goc)
        p.parent.mkdir(parents=True, exist_ok=True)
        if cu['mau']:                                                        # giữ bản còn mẫu gần nhất; bản rỗng không đè lên nó
            _tep(goc, truoc=True).write_text(json.dumps(cu, ensure_ascii=False), encoding='utf-8')
        tam = p.with_suffix('.tmp')
        tam.write_text(json.dumps(x, ensure_ascii=False), encoding='utf-8')
        tam.replace(p)
    return {'ban': x['ban'], 'luc': x['luc']}


# --------------------------------------------------------------------------- lớp đồng bộ trên trang Biểu đồ
# Theo dõi phần {mau, sao} trong localStorage 'so-cbcn1' (bảng Chỉ báo ghi sau mỗi thay đổi); khác bản đã đồng bộ thì đẩy lên (gom 0,8 giây).
# Lúc mở trang và mỗi 10 giây hỏi máy chủ; bản mới hơn (máy khác vừa lưu mẫu) thì nạp qua CBCN.dongBo, giữ nguyên bộ đang bật của máy này.
JS = r"""
(()=>{const K='so-cbcn1',H={'Content-Type':'application/json','X-So-Cong-Khai':'1'};let BAN=null,DONG,choV=null,hen=null,dangGui=false,dau=true;
const doc=()=>{try{const s=JSON.parse(localStorage.getItem(K)||'{}');return{mau:s.mau||{},sao:s.sao||['ema','rsi','macd','bb']}}catch(e){return{mau:{},sao:[]}}};
const chu=x=>JSON.stringify({mau:x.mau,sao:x.sao});
function ap(x){const C=window.CBCN;if(C&&typeof C.dongBo==='function')C.dongBo(x);
 else try{const s=JSON.parse(localStorage.getItem(K)||'{}');s.mau=x.mau;s.sao=x.sao;localStorage.setItem(K,JSON.stringify(s))}catch(e){}   // chưa có móc: lần mở trang sau mới thấy
 DONG=chu(doc())}
async function gui(){const x=doc(),v=chu(x);if(v===DONG||dangGui)return;
 let n0=0;try{n0=Object.keys(JSON.parse(DONG||'{}').mau||{}).length}catch(e){}
 if(!Object.keys(x.mau).length&&n0>=3&&!confirm('Xóa toàn bộ '+n0+' mẫu chỉ báo trên mọi máy đang dùng webapp?')){ap(JSON.parse(DONG));return}
 dangGui=true;try{const r=await fetch('/api/mau-chi-bao',{method:'POST',headers:H,body:JSON.stringify(x)});const j=await r.json();if(j.ok){BAN=j.ban;DONG=v}}catch(e){}dangGui=false}
async function nap(){let j;try{const r=await fetch('/api/mau-chi-bao',{cache:'no-store'});if(!r.ok)return;j=await r.json()}catch(e){return}
 const loc=doc(),v=chu(loc);
 if(j.ban==null){if(Object.keys(loc.mau).length){DONG=chu({mau:{},sao:loc.sao});gui()}else DONG=v;dau=false;return}   // máy chủ chưa có: đẩy mẫu của máy này lên
 if(!dau&&BAN!=null&&j.ban<=BAN)return;BAN=j.ban;const moi=chu(j);
 if(moi===v){DONG=v;dau=false;return}
 if(!dau&&v!==DONG)return;                                                               // máy này còn thay đổi chưa gửi: bản này sẽ thắng khi gửi
 if(document.querySelector('.cbcn-nen:not([hidden]) input:focus'))return;                // đang gõ tên mẫu: để lần sau
 dau=false;ap({mau:j.mau,sao:j.sao})}
setInterval(()=>{if(DONG===undefined||window.PHAT_LAI)return;const v=chu(doc());if(v!==DONG&&v!==choV){choV=v;clearTimeout(hen);hen=setTimeout(()=>{choV=null;gui()},800)}},500);
nap();setInterval(()=>{if(document.visibilityState==='visible')nap()},10000);
window.MCB={nap,gui}})();
"""
