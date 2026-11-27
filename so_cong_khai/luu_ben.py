"""Ghi JSON nguyên tử: chỉ thay bản đang dùng sau khi đã flush/fsync tệp mới."""
import json
import os
import tempfile
from pathlib import Path


def ghi_json(p: Path, value) -> None:
    raw = json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(',', ':')).encode('utf-8')
    p.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=p.stem + '-', suffix='.tmp', dir=p.parent)
    try:
        with os.fdopen(fd, 'wb') as f:
            f.write(raw)
            f.flush()
            os.fsync(f.fileno())
        os.replace(name, p)
    finally:
        Path(name).unlink(missing_ok=True)
