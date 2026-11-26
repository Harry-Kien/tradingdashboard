# -*- coding: utf-8 -*-
"""Lưu hình vẽ của trang Biểu đồ trên máy chủ (26/11/2026), để hình không mất khi đổi máy, đổi trình duyệt hay xóa dữ liệu trình duyệt, và mở trên
điện thoại (cùng webapp) vẫn thấy đúng hình đã vẽ trên máy tính.

Mỗi mã một tệp du-lieu/hinh-ve/<mã>.json: {'ds': danh sách hình như công cụ vẽ lưu, 'ban': số phiên bản tăng dần, 'luc': giờ lưu}.
Trang giữ bản trong trình duyệt (localStorage 'so-ve:<mã>') làm bản dự phòng khi mất kết nối; lớp đồng bộ JS bên dưới đẩy mọi thay đổi lên máy
chủ và nạp bản mới hơn từ máy chủ (thiết bị khác vừa sửa). Hai nơi cùng sửa thì bản lưu sau thắng, như các nền tảng biểu đồ khác.
Bản sao lưu hằng ngày (sao_luu.py) đã gồm cả thư mục du-lieu nên hình vẽ cũng được sao lưu."""
from __future__ import annotations

import json
import re
import threading
import time
from pathlib import Path

from . import telegram_nhom

TOI_DA_HINH = 1000
TOI_DA_BYTE = 400_000
_khoa = threading.Lock()


def _thu_muc(goc: Path | None = None) -> Path:
    return (telegram_nhom._tep('x').parent if goc is None else goc / 'du-lieu') / 'hinh-ve'


def ma_hop_le(ma: str) -> bool:
    return bool(re.fullmatch(r'[A-Za-z0-9._#+\-]{1,40}', ma or '')) and ma not in ('.', '..')


def _tep(ma: str, goc: Path | None = None) -> Path:
    if not ma_hop_le(ma):
        raise ValueError('mã không hợp lệ')
    return _thu_muc(goc) / f'{ma}.json'


def doc(ma: str, goc: Path | None = None) -> dict:
    """{'ds', 'ban', 'luc'}; mã chưa có hình trên máy chủ thì ban là None."""
    try:
        x = json.loads(_tep(ma, goc).read_text(encoding='utf-8'))
        if isinstance(x, dict) and isinstance(x.get('ds'), list):
            return {'ds': x['ds'], 'ban': int(x.get('ban', 0)), 'luc': x.get('luc')}
    except (OSError, ValueError, TypeError):
        pass
    return {'ds': [], 'ban': None, 'luc': None}


def _kiem_ds(ds) -> list:
    if not isinstance(ds, list):
        raise ValueError('dữ liệu hình vẽ không hợp lệ')
    if len(ds) > TOI_DA_HINH:
        raise ValueError(f'quá {TOI_DA_HINH} hình trên một mã')
    for h in ds:
        if not isinstance(h, dict) or not isinstance(h.get('id'), str) or not isinstance(h.get('k'), str):
            raise ValueError('hình vẽ thiếu mã hoặc loại')
        # Hình vẽ giờ được nạp về mọi máy: mã, loại và màu đi vào HTML/CSS của trang (menu chuột phải, thanh công cụ), nên chỉ nhận đúng
        # định dạng, kẻo một bản lưu có chèn thẻ HTML chạy được mã trên mọi trình duyệt mở trang (stored XSS).
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,40}', h['id']) or not re.fullmatch(r'[a-z0-9_]{1,20}', h['k']):
            raise ValueError('mã hoặc loại hình vẽ không hợp lệ')
        if h.get('mau') not in (None, '') and not (isinstance(h['mau'], str) and re.fullmatch(r'#[0-9A-Fa-f]{3,8}', h['mau'])):
            raise ValueError('màu hình vẽ không hợp lệ')
    if len(json.dumps(ds, ensure_ascii=False)) > TOI_DA_BYTE:
        raise ValueError('hình vẽ quá lớn')
    return ds


def luu(ma: str, ds, goc: Path | None = None, now: float | None = None) -> dict:
    """Ghi bản mới; trả {'ban', 'luc'}. Sai thì ValueError."""
    ds = _kiem_ds(ds)
    p = _tep(ma, goc)
    with _khoa:
        cu = doc(ma, goc)
        x = {'ds': ds, 'ban': (cu['ban'] or 0) + 1, 'luc': time.time() if now is None else now}
        p.parent.mkdir(parents=True, exist_ok=True)
        if cu['ds']:                                                         # giữ bản CÒN HÌNH gần nhất (bản rỗng không đè lên nó): lỡ xóa thì khôi phục được
            p.with_suffix('.truoc.json').write_text(json.dumps(cu, ensure_ascii=False), encoding='utf-8')
        tam = p.with_suffix('.tmp')
        tam.write_text(json.dumps(x, ensure_ascii=False), encoding='utf-8')
        tam.replace(p)
    return {'ban': x['ban'], 'luc': x['luc']}


# --------------------------------------------------------------------------- lớp đồng bộ trên trang Biểu đồ
# Không sửa mã vẽ: theo dõi khóa localStorage 'so-ve:<mã>' mà công cụ vẽ ghi sau mỗi thay đổi; khác bản đã đồng bộ thì đẩy lên (gom 0,8 giây);
# đổi mã hoặc mỗi 8 giây thì hỏi máy chủ, có bản mới hơn (thiết bị khác vừa sửa) mà ở đây không đang kéo, đang vẽ thì nạp vào.
JS = r"""
(()=>{const G=window.BDMN;if(!G)return;const H={'Content-Type':'application/json','X-So-Cong-Khai':'1'};
const BAN={},DONG={};let maCu=null,hen=null,dangGui=false,choV=null;
const khoa=g=>'so-ve:'+(g.ma||'XAU'),maCua=g=>g.ma||'XAU',ls=k=>{try{return localStorage.getItem(k)}catch(e){return null}};
async function gui(g){const k=khoa(g),v=ls(k);if(v==null||v===DONG[k]||dangGui)return;
 let n0=0;try{n0=JSON.parse(DONG[k]||'[]').length}catch(e){}                              // chốt an toàn: bản rỗng đè lên từ 5 hình trở lên thì hỏi lại
 const daHoi=window.HVD_DA_HOI===true;window.HVD_DA_HOI=false;                            // nút Xóa tất cả đã hỏi người dùng rồi: không hỏi lần hai
 if(v==='[]'&&n0>=5&&!daHoi&&!confirm('Xóa toàn bộ '+n0+' hình vẽ của mã này trên mọi máy đang dùng webapp?')){try{localStorage.setItem(k,DONG[k])}catch(e){}
  const g2=G();if(khoa(g2)===k){try{g2.VE.ds=JSON.parse(DONG[k]);g2.VE.goc=DONG[k];g2.veTb()}catch(e){}g2.lwPhu()}return}
 dangGui=true;
 try{const r=await fetch('/api/hinh-ve',{method:'POST',headers:H,body:JSON.stringify({ma:maCua(g),ds:JSON.parse(v)})});const j=await r.json();if(j.ok){BAN[k]=j.ban;DONG[k]=v}}catch(e){}
 dangGui=false}
async function nap(g,dau){const k=khoa(g),ma=maCua(g);let j;try{const r=await fetch('/api/hinh-ve?ma='+encodeURIComponent(ma),{cache:'no-store'});if(!r.ok)return;j=await r.json()}catch(e){return}
 const g2=G();if(khoa(g2)!==k)return;                                                     // đã đổi mã trong lúc chờ
 const v=ls(k);
 if(j.ban==null){if(v&&v!=='[]')gui(g2);else DONG[k]=v;return}                           // máy chủ chưa có: đẩy bản của trình duyệt này lên
 if(!dau&&BAN[k]!=null&&j.ban<=BAN[k])return;BAN[k]=j.ban;
 const moi=JSON.stringify(j.ds);if(moi===v){DONG[k]=v;return}
 if(!dau&&v!==DONG[k])return;                                                             // ở đây có thay đổi chưa gửi: bản này sẽ thắng khi gửi
 if(g2.VE.keo||g2.VE.tam)return;
 if(document.querySelector('.venhap,.mnp,.cbv-nen'))return;                              // đang gõ chữ ghi chú, menu chuột phải hay hộp cảnh báo đang mở: để lần sau
 g2.VE.ds=j.ds;g2.VE.goc=moi;g2.VE.chon=null;if(!dau){g2.VE.cu=[];g2.VE.lai=[]}   // bản từ thiết bị khác: hoàn tác không quay về bản cũ của máy này
try{localStorage.setItem(k,moi)}catch(e){}DONG[k]=moi;try{g2.veTb()}catch(e){}g2.lwPhu()}
setInterval(()=>{const g=G();if(!g||window.PHAT_LAI)return;const k=khoa(g);
 if(g.ma!==maCu){maCu=g.ma;nap(g,true);return}
 const v=ls(k);if(v!=null&&DONG[k]!==undefined&&v!==DONG[k]&&v!==choV){choV=v;clearTimeout(hen);hen=setTimeout(()=>{choV=null;gui(G())},800)}},500);   // hẹn lại chỉ khi nội dung đổi
setInterval(()=>{const g=G();if(g&&document.visibilityState==='visible'&&!window.PHAT_LAI)nap(g,false)},8000);
window.HVD={nap:()=>nap(G(),true),gui:()=>gui(G())}})();
"""
