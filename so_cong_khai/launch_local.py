"""Mở bản local đã chốt bằng cùng kho dữ liệu, không chạy mã đang được sửa dở."""
from __future__ import annotations

import json
import os
import sys
import subprocess
from pathlib import Path

from . import duong, local_runtime


def selection(program=None, data=None):
    program = Path(program) if program is not None else duong.goc_chuong_trinh()
    data = Path(data) if data is not None else duong.goc_du_lieu()
    manifest = data / 'du-lieu' / 'local-release.json'
    if manifest.exists():
        selected = json.loads(manifest.read_text(encoding='utf-8'))
        target = Path(selected['program_root']).resolve()
        if not (target / 'so_cong_khai' / 'web.py').is_file():
            raise ValueError('Không tìm thấy bản local đã chốt. Cần khôi phục bản phát hành trước khi chạy.')
        if local_runtime.build_id(target / 'so_cong_khai') != selected['build']:
            raise ValueError('Mã của bản local đã thay đổi sau khi chốt. Cần kiểm tra và chốt lại trước khi chạy.')
        program = target
    return program.resolve(), data.resolve()


def main():
    program, data = selection()
    env = dict(os.environ, HGR_DU_LIEU=str(data))
    env['PYTHONPATH'] = str(program)
    args = [sys.executable, '-X', 'utf8', '-m', 'so_cong_khai.web', '--port', str(local_runtime.PORT),
            '--cau-hinh', str(data / 'cau-hinh.json')]
    return subprocess.run(args, cwd=program, env=env, check=False).returncode  # noqa: S603 - fixed Python and argument vector; verified local release, no shell


if __name__ == '__main__':
    raise SystemExit(main())
