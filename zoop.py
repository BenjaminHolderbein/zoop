#!/usr/bin/env python3
"""Zero-install launcher for zoop.

Lets the Claude Code skill (and you) run the tool straight from a checkout
without `pip install`:

    python zoop.py list
    python zoop.py send --to "MacBook Pro" ./report.pdf
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from zoop.cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
