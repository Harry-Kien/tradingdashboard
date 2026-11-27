"""Absolute-path entrypoint for Claude Desktop, Codex and other local MCP clients."""
import sys
from pathlib import Path

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from so_cong_khai.mcp_may_chu import main  # noqa: E402

if __name__ == '__main__':
    raise SystemExit(main())
