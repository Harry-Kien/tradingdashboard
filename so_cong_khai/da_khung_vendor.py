"""Repo quick-lru 7.1.0, MIT; giữ nguyên mã nguồn, chỉ bọc export cho script cổ điển."""
from . import duong

_source = (duong.goc_chuong_trinh() / 'tinh/quick-lru-7.1.0/index.js').read_text(encoding='utf-8')
if not _source.startswith('export default class QuickLRU'):
    raise RuntimeError('Invalid bundled quick-lru source')
JS = '/* quick-lru 7.1.0 | MIT | Sindre Sorhus | license: tinh/quick-lru-7.1.0/license */\n' + _source.replace('export default class QuickLRU', 'window.DKQuickLRU = class QuickLRU', 1)
