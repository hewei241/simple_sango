#!/usr/bin/env python3
"""入口：从地理 API 生成地形（见 generate_from_api.py）"""
import subprocess
import sys
from pathlib import Path

if __name__ == "__main__":
    script = Path(__file__).parent / "generate_from_api.py"
    sys.exit(subprocess.call([sys.executable, str(script)]))
