"""Checks for unsupported numeric claims in chart prose, including small FX prices.

This is an output quality gate, not a proof that natural language is correct.
Prices and order actions remain outside the language model's authority.
"""
from __future__ import annotations

import math
import re
import unicodedata
from datetime import datetime, timedelta, timezone

NUMBER = re.compile(r'(?<![\w.,])[-+]?\d+(?:[.,]\d+)*(?![\w.,])')
METRIC = re.compile(r'(?:EMA|SMA|RSI|ATR|MACD|ADX)\s*$', re.I)
CLAIM = re.compile(r'\b(?:ty le thang|xac suat (?:thang|sinh loi|co lai|loi nhuan)|win\s*rate|probability of (?:profit|winning)|'
                   r'guaranteed (?:profit|return|win)|risk[- ]free profit|sure win|chac chan (?:thang|co lai)|'
                   r'cam ket (?:loi nhuan|sinh loi)|loi nhuan (?:cao nhat|bao dam|dam bao))\b', re.I)
REFUSAL = re.compile(r'\b(?:khong(?: the)?(?: (?:uoc luong|xac dinh|dua ra|xac minh|kiem chung|bao dam|dam bao|hua))?|'
                     r'khong co(?: du lieu| bang chung)?(?: ve| cho)?|chua(?: co)?(?: du lieu| bang chung)?(?: ve| cho)?|'
                     r'cannot(?: estimate| determine| verify| guarantee| promise)?|no evidence (?:of|for)|'
                     r'not (?:a |an )?(?:verified|established|guaranteed)?|unverified|unproven)\s*$', re.I)


def _fold(text: str) -> str:
    return ''.join(c for c in unicodedata.normalize('NFKD', text.lower().replace('đ', 'd')) if not unicodedata.combining(c))


def _numbers(value, result: list[float]) -> None:
    if type(value) in (int, float) and math.isfinite(value):
        result.append(float(value))
    elif isinstance(value, dict):
        for item in value.values():
            _numbers(item, result)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _numbers(item, result)


def _parse(value: str) -> float:
    # Handle both 3.650,25 and 3,650.25, plus ordinary decimals.
    if value.lstrip('+-').startswith(('0.', '0,')):
        value = value.replace(',', '.')
    elif re.fullmatch(r'[-+]?\d{1,3}(\.\d{3})+(,\d+)?', value):
        value = value.replace('.', '').replace(',', '.')
    elif re.fullmatch(r'[-+]?\d{1,3}(,\d{3})+(\.\d+)?', value):
        value = value.replace(',', '')
    else:
        value = value.replace(',', '.')
    return float(value)


def check(texts: list[str], evidence: dict) -> None:
    allowed: list[float] = []
    _numbers(evidence, allowed)
    for key in ('captured_at', 'quote_at'):
        stamp = evidence.get(key)
        if type(stamp) in (int, float) and math.isfinite(stamp):
            for zone in (timezone.utc, timezone(timedelta(hours=7))):
                dt = datetime.fromtimestamp(stamp, zone)
                allowed.extend((dt.year, dt.month, dt.day, dt.hour, dt.minute))
    for text in texts:
        folded = _fold(text)
        for claim in CLAIM.finditer(folded):
            # An explicit refusal without a quoted percentage is useful, not a promise.
            if not REFUSAL.search(folded[max(0,claim.start()-90):claim.start()]) or re.search(r'\d\s*%', text):
                raise ValueError('AI đưa ra tuyên bố hiệu suất chưa được kiểm chứng.')
        for match in NUMBER.finditer(text):
            token = match.group()
            value = _parse(token)
            prefix = text[max(0, match.start()-8):match.start()]
            if METRIC.search(prefix) and value.is_integer() and 0 < value <= 1000:
                continue
            suffix = _fold(text[match.end():match.end()+24])
            if re.fullmatch(r'\+?\d{1,2}', token) and 0 <= value <= 30 and re.match(r'\s*(?:nen|bars?|candles?|khung|frames?|lan|times?)\b', suffix):
                continue
            if value in (0, 30, 50, 70, 100) and 'rsi' in text[max(0, match.start()-32):match.start()].lower():
                continue
            digits = evidence.get('digits', 8)
            tolerance = .5*10**-digits if type(digits) is int and 0 <= digits <= 10 else 1e-8
            if not any(abs(value-v) <= max(tolerance+1e-10, abs(v)*1e-8) for v in allowed):
                raise ValueError('AI diễn giải số liệu ngoài ảnh chụp máy chủ.')
