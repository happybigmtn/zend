#!/usr/bin/env python3
"""
Hermes Adapter CLI

Provides shell-accessible commands for the Hermes adapter.
"""

import sys
from pathlib import Path

# Add service to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from adapter import main

if __name__ == "__main__":
    main()