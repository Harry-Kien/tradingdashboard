"""Owner-controlled local MCP access; no provider API calls or public network listener."""
from __future__ import annotations

import hashlib
import hmac
import io
import json
import re
import secrets
import sys
import time
from pathlib import Path
from urllib.parse import urlencode

from . import ai_chart, ai_providers, ai_store, da_ma, loi_nghiep_vu, luu_ben


def token(root: Path, create=False, rotate=False) -> str:
    p = root / 'du-lieu' / 'mcp-access-secret.json'
    if p.exists() and not rotate:
        try:
            return ai_providers._fernet(root).decrypt(json.loads(p.read_text(encoding='utf-8'))['encrypted'].encode()).decode()
        except Exception as e:
            raise ValueError('Không mở được khóa MCP cục bộ; chủ tài khoản cần tạo lại kết nối.') from e
    if not create:
        return ''
    value = secrets.token_urlsafe(32)
    luu_ben.ghi_json(p, {'encrypted': ai_providers._fernet(root).encrypt(value.encode()).decode()})
    return value


def authorize(cfg: dict, root: Path, header: str) -> bool:
    expected = token(root) if (cfg.get('mcp') or {}).get('bat') is True else ''
    return bool(expected and isinstance(header, str) and hmac.compare_digest(header, 'Bearer ' + expected))


def configs(cfg: dict, config_path: Path, port: int) -> dict:
    root = Path(__file__).resolve().parent.parent
    args = [str(root / 'so_cong_khai' / 'mcp_boot.py'), '--cau-hinh', str(config_path.resolve()), '--port', str(port)]
    return {'enabled': (cfg.get('mcp') or {}).get('bat') is True, 'port': port,
            'claude': {'mcpServers': {'harry-market': {'command': sys.executable, 'args': args}}},
            'codex': {'mcp_servers': {'harry_market': {'command': sys.executable, 'args': args, 'startup_timeout_sec': 20, 'tool_timeout_sec': 60}}},
            'transport': 'stdio', 'remote_ready': False, 'subscription_backend': False,
            'message': 'AI gọi công cụ trong ứng dụng đã kết nối, theo quyền và hạn mức của ứng dụng đó. MCP không biến gói cá nhân thành API website.'}


def pinned(root: Path, ident: str, now=None) -> dict:
    if not isinstance(ident, str) or not re.fullmatch(r'MCP-[a-f0-9]{24}', ident):
        raise ValueError('Mã ảnh chụp MCP không hợp lệ.')
    try:
        data = json.loads((root / 'out' / 'mcp' / (ident + '.json')).read_text(encoding='utf-8'))
    except (OSError, ValueError) as e:
        raise ValueError('Không tìm thấy ảnh chụp MCP.') from e
    if (time.time() if now is None else now) >= data['expires_at']:
        raise ValueError('Ảnh chụp MCP đã hết hiệu lực. Chụp lại để phân tích hiện tại.')
    return data


def capture(cfg: dict, root: Path, ma: str, tf: str) -> dict:
    ma = ma or da_ma.ma_vang(cfg)
    ai_chart.clean({'ma': ma, 'tf': tf, 'mode': 'entry'})
    settings = ai_store.settings(root)
    snap = ai_chart.snapshot(cfg, ma, tf, settings['quote_max_age'])
    options = ai_chart.candidates(snap, settings)
    directions = {}
    for frame, ind in snap['frames'].items():
        price, fast, slow = ind['close'], ind['ema20'], ind['ema50']
        directions[frame] = 'unknown' if fast is None or slow is None else 'up' if price > fast > slow else 'down' if price < fast < slow else 'mixed'
    trend = set(directions.values())
    regime = 'aligned_up' if trend == {'up'} else 'aligned_down' if trend == {'down'} else 'mixed_or_range'
    result = {'snapshot': snap, 'candidates': options, 'regime': regime, 'timeframe_direction': directions,
              'expires_at': snap['captured_at'] + settings['quote_max_age'], 'generated_by': 'deterministic_market_code',
              'news_status': 'unknown', 'execution': 'reference_only',
              'instructions': 'Chỉ phân tích forex/CFD/crypto. Dẫn mã snapshot và thời gian; dùng mức giá trong candidates. Đứng ngoài khi thiếu dữ liệu hoặc xung đột. Không coi đây là xác suất sinh lời.'}
    result['snapshot_id'] = 'MCP-' + hashlib.sha256(json.dumps(result, sort_keys=True, allow_nan=False).encode()).hexdigest()[:24]
    folder = root / 'out' / 'mcp'
    folder.mkdir(parents=True, exist_ok=True)
    luu_ben.ghi_json(folder / (result['snapshot_id'] + '.json'), result)
    for old in sorted(folder.glob('MCP-*.json'), key=lambda p: p.stat().st_mtime)[:-60]:
        try:
            old.unlink(missing_ok=True)
        except OSError:
            pass
    return result


def chart_image(data: dict) -> bytes:
    """Render a numeric snapshot as a chart-only PNG, not a screenshot of the user's desktop."""
    from PIL import Image, ImageDraw  # noqa: PLC0415 - optional local chart renderer
    cs = data['snapshot']['candles'][-80:]
    w, h, left, top, bottom = 1200, 660, 40, 65, 605
    image = Image.new('RGB', (w, h), '#0b111b')
    draw = ImageDraw.Draw(image)
    lo, hi = min(c[3] for c in cs), max(c[2] for c in cs)
    span = max(hi - lo, .000001)
    lo, hi = lo - span * .06, hi + span * .06
    y = lambda p: int(bottom - (p - lo) / (hi - lo) * (bottom - top))
    step = (w - left - 105) / max(1, len(cs))
    for i in range(6):
        p = lo + (hi - lo) * i / 5
        draw.line((left, y(p), w - 95, y(p)), fill='#223044')
        draw.text((w - 90, y(p) - 5), f'{p:.{data["snapshot"]["digits"]}f}', fill='#acbed4')
    for i, c in enumerate(cs):
        x = int(left + (i + .5) * step)
        color = '#24c68b' if c[4] >= c[1] else '#fa6674'
        draw.line((x, y(c[2]), x, y(c[3])), fill=color)
        draw.rectangle((x - max(1, int(step * .3)), min(y(c[1]), y(c[4])), x + max(1, int(step * .3)), max(y(c[1]), y(c[4])) + 1), fill=color)
    draw.text((left, 20), f'{data["snapshot"]["symbol"]} / {data["snapshot"]["timeframe"]} | closed candles | {data["snapshot_id"]}', fill='#edf3ff')
    draw.text((left, 630), 'MT5 snapshot; reference analysis only. News not verified. Running candle excluded.', fill='#acbed4')
    out = io.BytesIO()
    image.save(out, format='PNG')
    return out.getvalue()


def route(root: Path, cfg: dict, name: str, arguments: dict):
    from . import mcp_may_chu  # noqa: PLC0415 - keep the stdio bridge lightweight
    error = mcp_may_chu.validate_arguments(name, arguments)
    if error:
        raise ValueError(error)
    if name == 'phan_tich_realtime':
        return capture(cfg, root, arguments.get('ma', ''), arguments.get('tf', 'M15'))
    if name in ('doc_realtime', 'anh_realtime'):
        data = pinned(root, arguments['snapshot_id'])
        return chart_image(data) if name == 'anh_realtime' else data
    if name in ('doc_anh_chup', 'dieu_kien_phuong_phap'):
        output = Path(cfg.get('thu_muc_ra', 'out'))
        output = output if output.is_absolute() else root / output
        snap = loi_nghiep_vu.lay(arguments['snapshot_id'], output)
        if snap is None or not -5 <= loi_nghiep_vu.tuoi_giay(snap) <= 120:
            raise ValueError('Ảnh chụp bằng chứng đã cũ hoặc không tồn tại; cần chụp lại.')
    if name == 'chot_anh_chup':
        capture(cfg, root, arguments.get('ma', ''), arguments.get('tf', 'M15'))
    _, _, _, path, query = mcp_may_chu.CONG_CU[name]
    return path + ('?' + urlencode(query(arguments)) if query(arguments) else '')
