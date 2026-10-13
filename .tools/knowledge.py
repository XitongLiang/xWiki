#!/usr/bin/env python3
"""Compatibility entry point for the xWiki knowledge CLI."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from xwiki_tools.cli import main

raise SystemExit(main())
