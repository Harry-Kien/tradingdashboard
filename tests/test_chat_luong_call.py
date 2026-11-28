from datetime import datetime, timedelta, timezone

from so_cong_khai import chat_luong_call as C

NOW = datetime(2026, 11, 27, 6, tzinfo=timezone.utc)
PA = {'huong': 'MUA', 'vao': 3500.2, 'sl': 3480., 'tp': [3510., 3520.]}
FR = {'nguon': 'mt5', 'bid': 3500., 'ask': 3500.2, 'het': NOW}


def test_live_quote_and_valid_levels_pass():
    assert C.kiem(PA, FR, NOW) == []
    assert C.kiem({'huong': 'BAN', 'vao': 3500., 'sl': 3520., 'tp': [3490., 3480.]}, FR, NOW) == []


def test_cache_old_and_future_quotes_are_rejected():
    assert C.kiem(PA, {**FR, 'nguon': 'kho'}, NOW)
    assert C.kiem(PA, {**FR, 'het': NOW - timedelta(seconds=61)}, NOW)
    assert C.kiem(PA, {**FR, 'het': NOW + timedelta(seconds=6)}, NOW)
    assert C.kiem(PA, {**FR, 'het': NOW - timedelta(seconds=59)}, NOW) == []


def test_wide_spread_missing_nan_and_inverted_quote_are_rejected():
    for changes in ({'ask': 3502.}, {'ask': float('nan')}, {'bid': 3501.}, {'bid': None}):
        assert C.kiem(PA, {**FR, **changes}, NOW)
    assert C.kiem(PA, {'nguon': 'mt5', 'het': NOW}, NOW)


def test_invalid_levels_are_rejected_in_both_directions():
    for changes in ({'huong': 'BUY'}, {'sl': 3510.}, {'tp': [3480.]}, {'tp': []}, {'sl': float('inf')}):
        assert C.kiem({**PA, **changes}, FR, NOW)
