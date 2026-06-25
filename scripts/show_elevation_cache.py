#!/usr/bin/env python3
"""Print cached elevation point count for 240x180 grid."""
import json
from pathlib import Path

cache = Path(__file__).resolve().parent.parent / "data" / "elevation_land_240x180.json"
if cache.exists():
    n = len(json.loads(cache.read_text(encoding="utf-8")).get("points", []))
    print(f"Cached elevation points: {n}")
else:
    print("Cached elevation points: 0")
