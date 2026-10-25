#!/usr/bin/env python3
"""Free PandaScore Fixtures; see sources/pandascore.py for caching and validation."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from sources.pandascore import main

if __name__ == '__main__':
    main('csgo', 'csgo_matches.json', '2025-01-01', Path(__file__).resolve().parent)
