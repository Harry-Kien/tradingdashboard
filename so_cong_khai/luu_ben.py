"""Ghi JSON nguyên tử: chỉ thay bản đang dùng sau khi đã flush/fsync tệp mới."""
import json
import os
import tempfile
import time
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
        # Windows: một luồng/tiến trình đang đọc hoặc trình quét tệp có thể
        # giữ handle không chia sẻ DELETE. Giữ tệp cũ nguyên vẹn và thử lại
        # phép thay nguyên tử; không mở đích để ghi đè trực tiếp.
        for attempt in range(6):
            try:
                os.replace(name, p)
                break
            except PermissionError as e:
                if getattr(e, 'winerror', None) not in (5, 32, 33) or attempt == 5:
                    raise
                time.sleep(.01 * 2 ** attempt)
    finally:
        Path(name).unlink(missing_ok=True)
