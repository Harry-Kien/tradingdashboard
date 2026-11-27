"""Server-only AI adapters. Fixed HTTPS destinations; no SDK, tools or arbitrary URLs.

Model IDs are owner-reviewed, never silently replaced by a cheaper model.
API keys are encrypted at rest with Fernet; the master key is protected by Windows
DPAPI locally, or supplied as HGR_AI_MASTER_KEY by the hosting secret manager.
"""
from __future__ import annotations

import base64
import ctypes
import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

from . import luu_ben

CATALOG = {
    'anthropic': {'ten': 'Anthropic / Claude API', 'env': 'ANTHROPIC_API_KEY',
                  'url': 'https://api.anthropic.com/v1/messages',
                  'models': ['claude-opus-5-5', 'claude-fable-5-2', 'claude-sonnet-5-5'], 'vision': True},
    'openai': {'ten': 'OpenAI', 'env': 'OPENAI_API_KEY', 'url': 'https://api.openai.com/v1/responses',
               'models': ['gpt-6.2-astra', 'gpt-6.2-sol', 'gpt-6.1-terra'], 'vision': True},
    'gemini': {'ten': 'Google Gemini', 'env': 'GEMINI_API_KEY',
               'url': 'https://generativelanguage.googleapis.com/v1beta/openai/chat/completions',
               'models': ['gemini-4-hydrogen', 'gemini-4-neon'], 'vision': True},
    'deepseek': {'ten': 'DeepSeek', 'env': 'DEEPSEEK_API_KEY', 'url': 'https://api.deepseek.com/chat/completions',
                 'models': ['deepseek-v4-pro'], 'vision': False},
    'mistral': {'ten': 'Mistral (model do chủ tài khoản duyệt)', 'env': 'MISTRAL_API_KEY',
                'url': 'https://api.mistral.ai/v1/chat/completions', 'models': [], 'vision': False},
    'xai': {'ten': 'xAI (model do chủ tài khoản duyệt)', 'env': 'XAI_API_KEY',
            'url': 'https://api.x.ai/v1/chat/completions', 'models': [], 'vision': False},
}
MODEL_RE = re.compile(r'[A-Za-z0-9][A-Za-z0-9._:/-]{0,119}')


class ProviderError(ValueError):
    pass


def _dpapi(raw: bytes, decrypt=False) -> bytes:
    from ctypes import wintypes  # Windows-only, imported on demand

    class Blob(ctypes.Structure):
        _fields_ = [('size', wintypes.DWORD), ('data', ctypes.POINTER(ctypes.c_ubyte))]

    buf = ctypes.create_string_buffer(raw)
    src, dst = Blob(len(raw), ctypes.cast(buf, ctypes.POINTER(ctypes.c_ubyte))), Blob()
    fn = ctypes.windll.crypt32.CryptUnprotectData if decrypt else ctypes.windll.crypt32.CryptProtectData
    if not fn(ctypes.byref(src), None, None, None, None, 1, ctypes.byref(dst)):
        raise ProviderError('Không mở được kho khóa của tài khoản Windows này.')
    try:
        return ctypes.string_at(dst.data, dst.size)
    finally:
        ctypes.windll.kernel32.LocalFree(dst.data)


def _fernet(root: Path) -> Fernet:
    master = os.environ.get('HGR_AI_MASTER_KEY', '')
    if not master:
        if os.name != 'nt':
            raise ProviderError('Hosting cần HGR_AI_MASTER_KEY (Fernet) hoặc dùng khóa API qua biến môi trường.')
        p = root / 'du-lieu' / 'ai-master-secret.json'
        if p.exists():
            master = _dpapi(base64.b64decode(json.loads(p.read_text(encoding='utf-8'))['dpapi']), True)
        else:
            master = Fernet.generate_key()
            luu_ben.ghi_json(p, {'dpapi': base64.b64encode(_dpapi(master)).decode('ascii')})
    try:
        return Fernet(master)
    except (ValueError, TypeError) as e:
        raise ProviderError('HGR_AI_MASTER_KEY không phải khóa Fernet hợp lệ.') from e


def save_key(root: Path, provider: str, value: str) -> None:
    if not isinstance(provider, str) or provider not in CATALOG or not isinstance(value, str):
        raise ProviderError('Nhà cung cấp hoặc khóa API không hợp lệ.')
    p = root / 'du-lieu' / f'ai-{provider}-secret.json'
    if not value:
        p.unlink(missing_ok=True)
        return
    if not 12 <= len(value) <= 4096 or any(ord(c) < 33 or ord(c) > 126 for c in value):
        raise ProviderError('Khóa API cần 12–4096 ký tự, không có khoảng trắng.')
    token = _fernet(root).encrypt(value.encode()).decode('ascii')
    luu_ben.ghi_json(p, {'encrypted': token})


def key(root: Path, provider: str) -> str:
    # A saved owner key takes precedence. Clearing it restores environment fallback.
    p = root / 'du-lieu' / f'ai-{provider}-secret.json'
    if p.exists():
        try:
            return _fernet(root).decrypt(json.loads(p.read_text(encoding='utf-8'))['encrypted'].encode()).decode()
        except (InvalidToken, ValueError, KeyError, OSError) as e:
            raise ProviderError('Không giải mã được khóa API; kiểm tra master key hoặc nhập lại khóa.') from e
    return os.environ.get(CATALOG[provider]['env'], '')


def has_key(root: Path, provider: str) -> bool:
    return (root / 'du-lieu' / f'ai-{provider}-secret.json').exists() or bool(os.environ.get(CATALOG[provider]['env']))


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ProviderError('API chuyển hướng bị từ chối để bảo vệ khóa.')


def check(root: Path, cfg: dict) -> dict:
    """Check credentials and model visibility through list-models; no generation tokens."""
    provider = cfg['provider']
    urls = {'openai': 'https://api.openai.com/v1/models', 'anthropic': 'https://api.anthropic.com/v1/models?limit=100',
            'gemini': 'https://generativelanguage.googleapis.com/v1beta/openai/models',
            'deepseek': 'https://api.deepseek.com/models', 'mistral': 'https://api.mistral.ai/v1/models', 'xai': 'https://api.x.ai/v1/models'}
    secret = key(root, provider)
    if not secret:
        raise ProviderError('Chưa có khóa API cho nhà cung cấp này.')
    headers = {'Accept': 'application/json'}
    if provider == 'anthropic':
        headers.update({'x-api-key': secret, 'anthropic-version': '2023-06-01'})
    else:
        headers['Authorization'] = 'Bearer ' + secret
    req = urllib.request.Request(urls[provider], headers=headers)  # noqa: S310 - fixed HTTPS catalog
    try:
        with urllib.request.build_opener(NoRedirect()).open(req, timeout=15) as response:  # noqa: S310
            raw = response.read(1_000_001)
        if len(raw) > 1_000_000:
            raise ProviderError('Danh sách model API quá lớn.')
        data = json.loads(raw)
        models = [m['id'] for m in data.get('data', []) if isinstance(m.get('id'), str)]
    except urllib.error.HTTPError as e:
        raise ProviderError(f'API trả HTTP {e.code}; kiểm tra khóa và quyền truy cập.') from None
    except (OSError, ValueError, TypeError, AttributeError, KeyError) as e:
        if isinstance(e, ProviderError):
            raise
        raise ProviderError('Không kiểm tra được danh sách model; API hoặc kết nối chưa sẵn sàng.') from None
    return {'ok': True, 'provider': provider, 'model': cfg['model'], 'listed': cfg['model'] in models,
            'models': models[:200], 'message': 'Khóa API được chấp nhận. ' + ('Đã thấy model đã chọn.' if cfg['model'] in models else 'Chưa thấy ID đã chọn; có thể cần đúng phiên bản hoặc quyền truy cập.')}


def call(root: Path, cfg: dict, system: str, content: str, image: str | None = None) -> dict:
    provider, model = cfg['provider'], cfg['model']
    spec = CATALOG[provider]
    secret = key(root, provider)
    if not secret:
        raise ProviderError('Chủ tài khoản chưa cấu hình khóa API.')
    headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
    limit = cfg['max_tokens']
    if provider == 'openai':
        parts = [{'type': 'input_text', 'text': content}]
        if image:
            parts.append({'type': 'input_image', 'image_url': image, 'detail': 'high'})
        body = {'model': model, 'instructions': system, 'input': [{'role': 'user', 'content': parts}],
                'max_output_tokens': limit, 'store': False, 'reasoning': {'effort': cfg['effort']},
                'text': {'format': {'type': 'json_object'}}}
    elif provider == 'anthropic':
        parts = [{'type': 'text', 'text': content}]
        if image:
            mime, b64 = image.split(';base64,')
            parts.append({'type': 'image', 'source': {'type': 'base64', 'media_type': mime[5:], 'data': b64}})
        body = {'model': model, 'system': system, 'messages': [{'role': 'user', 'content': parts}],
                'max_tokens': limit, 'output_config': {'effort': cfg['effort']}}
        headers.update({'x-api-key': secret, 'anthropic-version': '2023-06-01'})
    else:
        parts = [{'type': 'text', 'text': content}]
        if image:
            parts.append({'type': 'image_url', 'image_url': {'url': image}})
        body = {'model': model, 'messages': [{'role': 'system', 'content': system}, {'role': 'user', 'content': parts}],
                'max_tokens': limit, 'response_format': {'type': 'json_object'}}
        if provider in ('gemini', 'deepseek'):
            body['reasoning_effort'] = cfg['effort']
    if provider != 'anthropic':
        headers['Authorization'] = 'Bearer ' + secret
    req = urllib.request.Request(spec['url'], data=json.dumps(body, allow_nan=False).encode(), headers=headers, method='POST')  # noqa: S310 - fixed HTTPS catalog
    try:
        # No retry: a timed-out request may have been billed already.
        with urllib.request.build_opener(NoRedirect()).open(req, timeout=cfg['timeout']) as response:  # noqa: S310 - destinations are fixed HTTPS constants
            raw = response.read(2_000_001)
        if len(raw) > 2_000_000:
            raise ProviderError('Câu trả lời API vượt giới hạn.')
        result = json.loads(raw)
    except urllib.error.HTTPError as e:
        # Never return upstream bodies/URLs/headers; they may echo secrets.
        raise ProviderError(f'API trả HTTP {e.code}; kiểm tra quyền model, khóa và hạn mức nhà cung cấp.') from None
    except (OSError, ValueError) as e:
        if isinstance(e, ProviderError):
            raise
        raise ProviderError('API hết thời gian hoặc trả dữ liệu lỗi. Không tự gửi lại để tránh tính phí trùng.') from None
    try:
        usage = result.get('usage') or {}
        if provider == 'openai':
            text = '\n'.join(c.get('text', '') for x in result.get('output', []) for c in x.get('content', []) if c.get('type') == 'output_text')
            done = result.get('status') == 'completed'
        elif provider == 'anthropic':
            text = '\n'.join(x.get('text', '') for x in result.get('content', []) if x.get('type') == 'text')
            done = result.get('stop_reason') == 'end_turn'
        else:
            choices = result.get('choices') or [{}]
            text = (choices[0].get('message') or {}).get('content') or ''
            done = choices[0].get('finish_reason') == 'stop'
        return {'text': text, 'complete': done, 'model': result.get('model', model),
                'input_tokens': usage.get('input_tokens', usage.get('prompt_tokens')),
                'output_tokens': usage.get('output_tokens', usage.get('completion_tokens'))}
    except (AttributeError, TypeError, IndexError) as e:
        raise ProviderError('Cấu trúc phản hồi API không hợp lệ.') from e
