"""Bản local chuẩn và khóa một tiến trình nền cho mỗi kho cấu hình."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path

PORT = 8769


def build_id(root=None):
    root = Path(root) if root is not None else Path(__file__).resolve().parent
    digest = hashlib.sha256()
    for path in sorted(root.rglob('*.py')):
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(path.read_bytes().replace(b'\r\n', b'\n'))
    return 'local-' + digest.hexdigest()[:16]


class InstanceLock:
    """Khóa hệ điều hành tự nhả khi tiến trình chết; tệp còn lại không phải khóa treo."""

    def __init__(self, config):
        self.path = Path(config).resolve().parent / 'du-lieu' / 'local-runtime.lock'
        self.handle = None

    def acquire(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        handle = self.path.open('a+b')
        try:
            handle.seek(0, os.SEEK_END)
            if handle.tell() == 0:
                handle.write(b'0')
                handle.flush()
            handle.seek(0)
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as e:
            handle.close()
            raise OSError('Đã có một webapp đầy đủ đang chạy cho kho dữ liệu này. Mở bản local hiện có thay vì chạy thêm.') from e
        self.handle = handle
        return self

    def release(self):
        if self.handle is not None:
            self.handle.close()
            self.handle = None
