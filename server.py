"""Repository-level entrypoint for the TVFinance MCP server."""

import sys
from importlib import import_module
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parent / "src"
source_root = str(SOURCE_ROOT)
if source_root in sys.path:
    sys.path.remove(source_root)
sys.path.insert(0, source_root)

mcp = import_module("tvfinance.mcp").create_server()
