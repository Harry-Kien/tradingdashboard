"""Transactional settings, account entitlements and AI usage reservations (SQLite).

The browser never supplies its identity, entitlement, provider, budget or prompt.
BEGIN IMMEDIATE serializes reservations across threads and server processes.
"""
from __future__ import annotations

import json
import math
import re
import secrets
import sqlite3
from contextlib import closing, contextmanager
from datetime import datetime, timezone
from pathlib import Path

from . import ai_providers as providers

DEFAULT = {'enabled': False, 'provider': 'anthropic', 'model': 'claude-opus-5-5',
           'approved_models': ['claude-opus-5-5', 'claude-fable-5-2', 'claude-sonnet-5-5'],
           'effort': 'high', 'vision': True, 'free_questions': 5, 'daily_questions': 20,
           'daily_budget_usd': 10.0, 'monthly_budget_usd': 100.0, 'timeout': 75,
           'max_tokens': 4096, 'input_usd_million': 20.0, 'output_usd_million': 100.0,
           'quote_max_age': 30, 'min_rr': 1.5, 'prompt_note': '',
           'plans': {'pro': {'label': 'Pro', 'questions': 200, 'price_vnd': 299000},
                     'premium': {'label': 'Premium', 'questions': 600, 'price_vnd': 699000}}}


class StoreError(ValueError):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


@contextmanager
def db(root: Path):
    p = root / 'du-lieu' / 'ai-platform.sqlite3'
    p.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(p, timeout=10, isolation_level=None)
    con.row_factory = sqlite3.Row
    try:
        con.executescript('''
        CREATE TABLE IF NOT EXISTS settings (id INTEGER PRIMARY KEY CHECK(id=1), body TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS grants (uid TEXT PRIMARY KEY, plan TEXT NOT NULL, expires REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS requests (id TEXT PRIMARY KEY, uid TEXT NOT NULL, created REAL NOT NULL,
            state TEXT NOT NULL, charge REAL NOT NULL, counted INTEGER NOT NULL, response TEXT);
        CREATE INDEX IF NOT EXISTS request_user ON requests(uid,created);
        ''')
        con.execute('BEGIN IMMEDIATE')
        yield con
        con.commit()
    except BaseException:
        con.rollback()
        raise
    finally:
        con.close()


def settings(root: Path, con=None) -> dict:
    if con is None:
        with db(root) as c:
            return settings(root, c)
    r = con.execute('SELECT body FROM settings WHERE id=1').fetchone()
    return {**DEFAULT, **(json.loads(r['body']) if r else {})}


def validate(value: dict) -> dict:
    if not isinstance(value, dict) or set(value) != set(DEFAULT):
        raise StoreError('Cấu hình AI thiếu mục hoặc có mục không được phép.')
    d = dict(value)
    for k in ('enabled', 'vision'):
        if type(d[k]) is not bool:
            raise StoreError(f'{k}: cần bật/tắt.')
    if not isinstance(d['provider'], str) or d['provider'] not in providers.CATALOG:
        raise StoreError('Nhà cung cấp không được hỗ trợ.')
    models = d['approved_models']
    if not isinstance(models, list) or not 1 <= len(models) <= 20 or any(not isinstance(m, str) or not providers.MODEL_RE.fullmatch(m) for m in models):
        raise StoreError('Danh sách model được duyệt không hợp lệ.')
    if not isinstance(d['model'], str) or d['model'] not in models:
        raise StoreError('Model phải nằm trong danh sách do chủ tài khoản duyệt.')
    if not isinstance(d['effort'], str) or d['effort'] not in ('low', 'medium', 'high'):
        raise StoreError('Mức suy luận không hợp lệ.')
    for k, lo, hi, integer in [('free_questions', 0, 1000, True), ('daily_questions', 1, 10000, True),
                              ('daily_budget_usd', .1, 10000, False), ('monthly_budget_usd', .1, 100000, False),
                              ('timeout', 15, 120, True), ('max_tokens', 2048, 16384, True),
                              ('input_usd_million', .01, 1000, False), ('output_usd_million', .01, 2000, False),
                              ('quote_max_age', 5, 120, True), ('min_rr', 1, 10, False)]:
        v = d[k]
        if type(v) not in (int, float) or not math.isfinite(v) or not lo <= v <= hi or (integer and int(v) != v):
            raise StoreError(f'{k}: cần số {"nguyên " if integer else ""}từ {lo} đến {hi}.')
        d[k] = int(v) if integer else float(v)
    if not isinstance(d['prompt_note'], str) or len(d['prompt_note']) > 3000:
        raise StoreError('Hướng dẫn bổ sung tối đa 3000 ký tự.')
    plans = d['plans']
    if not isinstance(plans, dict) or not 1 <= len(plans) <= 8:
        raise StoreError('Cần 1–8 gói sử dụng.')
    for name, p in plans.items():
        if not re.fullmatch(r'[a-z][a-z0-9_-]{1,30}', name) or not isinstance(p, dict) or set(p) != {'label', 'questions', 'price_vnd'}:
            raise StoreError('Gói không hợp lệ.')
        if not isinstance(p['label'], str) or not 1 <= len(p['label']) <= 40:
            raise StoreError('Tên gói cần 1–40 ký tự.')
        for k, lo, hi in [('questions', 1, 100000), ('price_vnd', 0, 100000000)]:
            if type(p[k]) is not int or not lo <= p[k] <= hi:
                raise StoreError('Lượt hoặc giá gói không hợp lệ.')
    return d


def save(root: Path, value: dict) -> None:
    value = validate(value)
    with db(root) as con:
        con.execute('INSERT OR REPLACE INTO settings VALUES (1,?)', (json.dumps(value, ensure_ascii=False),))


def grant(root: Path, uid: str, plan: str, expires: float) -> None:
    if not isinstance(uid, str) or not re.fullmatch(r'[a-f0-9]{32}', uid):
        raise StoreError('Tài khoản không hợp lệ.')
    with db(root) as con:
        if plan == 'free':
            con.execute('DELETE FROM grants WHERE uid=?', (uid,))
        elif isinstance(plan, str) and plan in settings(root, con)['plans'] and type(expires) in (float, int) and math.isfinite(expires) and 0 < expires < 253402300799:
            con.execute('INSERT OR REPLACE INTO grants VALUES (?,?,?)', (uid, plan, expires))
        else:
            raise StoreError('Gói hoặc ngày hết hạn không hợp lệ.')


def _account(con, cfg: dict, user: dict, now: float) -> dict:
    # A process killed during an upstream request cannot know whether the API billed.
    # Refund the customer's question after the timeout window; retain the cost hold,
    # and cache a failure so replaying that request ID never sends another API call.
    uncertain = json.dumps({'ok': False, 'chan': ['Lượt trước bị gián đoạn. Đã hoàn lượt hỏi; ngân sách API được giữ để đối soát.']}, ensure_ascii=False)
    con.execute("UPDATE requests SET state='uncertain',counted=0,response=? WHERE state='pending' AND created<?", (uncertain, now - 180))
    r = con.execute('SELECT * FROM grants WHERE uid=? AND expires>?', (user['id'], now)).fetchone()
    plan = r['plan'] if r and r['plan'] in cfg['plans'] else 'free'
    start = datetime.fromtimestamp(now, timezone.utc).strftime('%Y-%m-01T00:00:00+00:00')
    month = datetime.fromisoformat(start).timestamp()
    # Free allowance is lifetime; paid allowance is a UTC calendar month. Renewing does not reset usage.
    used = con.execute('SELECT COUNT(*) FROM requests WHERE uid=? AND counted=1 AND created>=?',
                       (user['id'], month if plan != 'free' else 0)).fetchone()[0]
    limit = cfg['plans'][plan]['questions'] if plan != 'free' else cfg['free_questions']
    if user.get('chu'):
        limit = 1000000000
    return {'plan': 'owner' if user.get('chu') else plan, 'used': used, 'limit': limit,
            'remaining': max(0, limit - used), 'expires': r['expires'] if r else None}


def status(root: Path, user: dict | None, now: float | None = None) -> dict:
    now = datetime.now(timezone.utc).timestamp() if now is None else now
    with db(root) as con:
        cfg = settings(root, con)
        account = _account(con, cfg, user, now) if user else None
    reasons = []
    if not user:
        reasons.append('Đăng nhập tài khoản biểu đồ để sử dụng AI.')
    if not cfg['enabled']:
        reasons.append('Chủ tài khoản chưa bật dịch vụ AI.')
    if not providers.has_key(root, cfg['provider']):
        reasons.append('Chủ tài khoản chưa cấu hình khóa API.')
    if account and not account['remaining']:
        reasons.append('Đã hết lượt sử dụng. Liên hệ chủ tài khoản để nâng gói.')
    return {'ok': True, 'chan': reasons, 'account': account, 'provider': cfg['provider'], 'model': cfg['model'],
            'vision': cfg['vision'] and providers.CATALOG[cfg['provider']]['vision'],
            'quote_max_age': cfg['quote_max_age'], 'plans': cfg['plans'], 'billing': 'manual',
            'owner': bool(user and user.get('chu')),
            'capabilities': {'read_only': True, 'order_execution': False, 'fine_tuned_here': False,
                             'free_rules': True, 'rules_need_login': True, 'rules_need_owner': True}}


def reserve(root: Path, user: dict, request_id: str, charge: float, now: float) -> tuple[dict | None, dict]:
    if not isinstance(request_id, str) or not re.fullmatch(r'[a-f0-9]{32}', request_id):
        raise StoreError('Thiếu mã yêu cầu chống gửi trùng.')
    with db(root) as con:
        cfg = settings(root, con)
        old = con.execute('SELECT * FROM requests WHERE id=?', (request_id,)).fetchone()
        if old:
            if old['uid'] != user['id']:
                raise StoreError('Mã yêu cầu đã được sử dụng.', 409)
            if old['response']:
                return json.loads(old['response']), cfg
            raise StoreError('Yêu cầu này đang xử lý hoặc cần kiểm tra sau sự cố; không gửi lại.', 409)
        if not cfg['enabled']:
            raise StoreError('Dịch vụ AI đang tắt.', 403)
        a = _account(con, cfg, user, now)
        if not a['remaining']:
            raise StoreError('Đã hết lượt sử dụng. Liên hệ chủ tài khoản để nâng gói.', 429)
        pending = con.execute("SELECT uid FROM requests WHERE state='pending' AND created>?", (now - 180,)).fetchall()
        if any(r['uid'] == user['id'] for r in pending) or len(pending) >= 3:
            raise StoreError('AI đang xử lý yêu cầu; vui lòng chờ.', 429)
        last = con.execute('SELECT MAX(created) FROM requests WHERE uid=?', (user['id'],)).fetchone()[0]
        if last and now - last < 5:
            raise StoreError('Chờ 5 giây trước lượt tiếp theo.', 429)
        day = int((now + 7 * 3600) // 86400) * 86400 - 7 * 3600  # reset day Asia/Saigon
        count = con.execute('SELECT COUNT(*) FROM requests WHERE uid=? AND counted=1 AND created>=?', (user['id'], day)).fetchone()[0]
        if count >= cfg['daily_questions']:
            raise StoreError('Đã đạt giới hạn lượt hỏi trong ngày.', 429)
        month = datetime.fromtimestamp(now, timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0).timestamp()
        for start, cap in ((day, cfg['daily_budget_usd']), (month, cfg['monthly_budget_usd'])):
            used = con.execute('SELECT COALESCE(SUM(charge),0) FROM requests WHERE created>=?', (start,)).fetchone()[0]
            if used + charge > cap:
                raise StoreError('Ngân sách AI đang hết; chủ tài khoản cần điều chỉnh.', 429)
        con.execute('INSERT INTO requests VALUES (?,?,?,?,?,?,NULL)', (request_id, user['id'], now, 'pending', charge, 1))
        return None, cfg


def finish(root: Path, request_id: str, response: dict, charge: float, success: bool, user: dict, now: float) -> None:
    with db(root) as con:
        con.execute('UPDATE requests SET state=?,charge=?,counted=? WHERE id=?',
                    ('done' if success else 'failed', charge, int(success), request_id))
        response['account'] = _account(con, settings(root, con), user, now)
        con.execute('UPDATE requests SET response=? WHERE id=?', (json.dumps(response, ensure_ascii=False, allow_nan=False), request_id))


def admin(root: Path) -> dict:
    with db(root) as con:
        cfg = settings(root, con)
        usage = [dict(r) for r in con.execute('SELECT uid,COUNT(*) requests,SUM(counted) used,ROUND(SUM(charge),4) reserved_usd FROM requests GROUP BY uid')]
        grants = [dict(r) for r in con.execute('SELECT * FROM grants')]
    return {'ok': True, 'settings': cfg, 'providers': {k: {a: b for a, b in v.items() if a != 'url'} for k, v in providers.CATALOG.items()},
            'keys': {k: providers.has_key(root, k) for k in providers.CATALOG}, 'usage': usage, 'grants': grants}


def new_id() -> str:
    return secrets.token_hex(16)


def backup_bytes(path: Path) -> bytes:
    """Consistent SQLite image for the existing ZIP backup, including in-flight writes."""
    with closing(sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True, timeout=5)) as src, closing(sqlite3.connect(':memory:')) as dst:
        src.backup(dst)
        return dst.serialize()
