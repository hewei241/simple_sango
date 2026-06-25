#!/usr/bin/env python3
"""
从根目录中国地形 JPG 栅格化生成地图数据。
输出 js/china-terrain-data.js 与 js/jpg-source-config.js
"""
from __future__ import annotations

import json
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    raise SystemExit("需要 Pillow: pip install pillow")

ROOT = Path(__file__).resolve().parent.parent
OUT_JS = ROOT / "js" / "china-terrain-data.js"
OUT_CFG = ROOT / "js" / "jpg-source-config.js"

MAP_W, MAP_H = 120, 90
LON_MIN, LON_MAX = 98.0, 123.5
LAT_MIN, LAT_MAX = 17.5, 42.0

TERRAIN_CHAR = {
    "sea": "s", "plain": "p", "hill": "h", "forest": "f", "mountain": "m",
    "river": "r", "desert": "d", "swamp": "w", "coast": "c",
}


def find_jpg() -> Path:
    for p in ROOT.iterdir():
        if p.suffix.lower() in (".jpg", ".jpeg") and p.is_file():
            return p
    raise FileNotFoundError("根目录未找到 JPG 地形图")


def is_content(r: int, g: int, b: int) -> bool:
    if r > 248 and g > 248 and b > 248:
        return False
    return True


def detect_content_bbox(img: Image.Image) -> tuple[int, int, int, int]:
    w, h = img.size
    min_x, min_y, max_x, max_y = w, h, 0, 0
    for y in range(h):
        for x in range(w):
            r, g, b = img.getpixel((x, y))
            if is_content(r, g, b):
                min_x = min(min_x, x)
                max_x = max(max_x, x)
                min_y = min(min_y, y)
                max_y = max(max_y, y)

    # 裁掉底部图例与白边
    for y in range(max_y, min_y, -1):
        span = max_x - min_x
        white = sum(
            1 for x in range(min_x, max_x)
            if img.getpixel((x, y)) > (248, 248, 248)
        )
        if white < span * 0.88:
            max_y = y
            break

    return min_x, min_y, max_x, max_y


def grid_to_geo(x: int, y: int) -> tuple[float, float]:
    lon = LON_MIN + (x / (MAP_W - 1)) * (LON_MAX - LON_MIN)
    lat = LAT_MAX - (y / (MAP_H - 1)) * (LAT_MAX - LAT_MIN)
    return lon, lat


def classify_rgb(r: int, g: int, b: int, lon: float, lat: float) -> str:
    lum = 0.299 * r + 0.587 * g + 0.114 * b

    # 海域
    if b > 155 and b > r + 25 and b > g + 5:
        return "sea"
    if b > 115 and b > r + 12 and g > 75 and lum > 100:
        return "sea"

    # 浅海 / 海岸
    if b > 95 and g > 95 and b >= r - 5 and lum > 125:
        return "coast"

    # 高山 / 高原（棕紫、深褐）
    if lum < 95 and r < 110 and g < 95:
        return "mountain"
    if r > 70 and g < r - 8 and b < g and lum < 125:
        return "mountain"

    # 沙漠 / 戈壁（西北干旱区黄褐）
    if lon < 108 and lat > 33.5:
        if r > 185 and g > 150 and b < 175 and r > b + 20:
            return "desert"
        if r > 160 and g > 130 and b < 140 and r > g + 5:
            return "desert"

    # 丘陵 / 台地（黄橙）
    if r > 175 and g > 145 and lum > 155:
        return "hill"
    if r > 150 and g > 120 and b < 150:
        return "hill"

    # 森林（深绿）
    if g > r + 12 and g > b + 8 and lum < 135:
        return "forest"

    # 平原（亮绿）
    if g > r + 4 and g > b and lum >= 115:
        return "plain"

    if lum > 205:
        return "plain"
    if lum > 145:
        return "hill"
    return "mountain"


def sample_cell(img: Image.Image, x0: int, y0: int, x1: int, y1: int) -> tuple[int, int, int]:
    region = img.crop((x0, y0, x1, y1))
    pixels = list(region.getdata())
    rs = sum(p[0] for p in pixels)
    gs = sum(p[1] for p in pixels)
    bs = sum(p[2] for p in pixels)
    n = len(pixels) or 1
    return rs // n, gs // n, bs // n


def apply_coast(grid: list[list[str]]) -> None:
    land = {"p", "h", "f", "d", "m", "w"}
    for y in range(MAP_H):
        for x in range(MAP_W):
            if grid[y][x] not in land:
                continue
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if 0 <= nx < MAP_W and 0 <= ny < MAP_H and grid[ny][nx] == "s":
                    grid[y][x] = "c"
                    break


def apply_rivers(grid: list[list[str]], img: Image.Image, bbox: tuple[int, int, int, int]) -> None:
    """在陆地格子上检测 JPG 中的蓝色河流线。"""
    min_x, min_y, max_x, max_y = bbox
    cell_w = (max_x - min_x) / MAP_W
    cell_h = (max_y - min_y) / MAP_H
    candidates = {"p", "h", "f"}

    for y in range(MAP_H):
        for x in range(MAP_W):
            if grid[y][x] not in candidates:
                continue
            x0 = int(min_x + x * cell_w)
            y0 = int(min_y + y * cell_h)
            x1 = int(min_x + (x + 1) * cell_w)
            y1 = int(min_y + (y + 1) * cell_h)
            region = img.crop((x0, y0, x1, y1))
            river_px = 0
            total = 0
            for r, g, b in region.getdata():
                total += 1
                if b > 145 and b > r + 28 and g > 85 and 0.299 * r + 0.587 * g + 0.114 * b > 95:
                    river_px += 1
            if total and river_px / total > 0.14:
                grid[y][x] = "r"


def build_grid(img: Image.Image, bbox: tuple[int, int, int, int]) -> list[list[str]]:
    min_x, min_y, max_x, max_y = bbox
    cell_w = (max_x - min_x) / MAP_W
    cell_h = (max_y - min_y) / MAP_H
    grid: list[list[str]] = []

    for y in range(MAP_H):
        row: list[str] = []
        for x in range(MAP_W):
            x0 = int(min_x + x * cell_w)
            y0 = int(min_y + y * cell_h)
            x1 = max(x0 + 1, int(min_x + (x + 1) * cell_w))
            y1 = max(y0 + 1, int(min_y + (y + 1) * cell_h))
            r, g, b = sample_cell(img, x0, y0, x1, y1)
            lon, lat = grid_to_geo(x, y)
            t = classify_rgb(r, g, b, lon, lat)
            row.append(TERRAIN_CHAR[t])
        grid.append(row)

    apply_coast(grid)
    apply_rivers(grid, img, bbox)
    return grid


def main() -> None:
    jpg = find_jpg()
    print(f"Source: {jpg.name} ({jpg.stat().st_size} bytes)")
    img = Image.open(jpg).convert("RGB")
    print(f"Image size: {img.size[0]} x {img.size[1]}")

    bbox = detect_content_bbox(img)
    print(f"Content bbox: {bbox}")

    grid = build_grid(img, bbox)
    rows = ["".join(r) for r in grid]
    stats: dict[str, int] = {}
    for row in rows:
        for c in row:
            stats[c] = stats.get(c, 0) + 1

    OUT_JS.write_text(
        f"""/**
 * 由根目录 JPG 自动生成（scripts/generate_from_jpg.py）
 * 源图: {jpg.name}
 * 字符: s=海 p=平原 h=丘陵 f=森林 m=山地 r=河 d=沙漠 w=沼泽 c=海岸
 */
const CHINA_TERRAIN_ROWS = {json.dumps(rows, ensure_ascii=False)};

const CHINA_TERRAIN_DECODE = {{
  s: "sea", p: "plain", h: "hill", f: "forest", m: "mountain",
  r: "river", d: "desert", w: "swamp", c: "coast",
}};
""",
        encoding="utf-8",
    )

    OUT_CFG.write_text(
        f"""/**
 * JPG 源图地理映射（scripts/generate_from_jpg.py）
 */
const JPG_SOURCE = {json.dumps(jpg.name, ensure_ascii=False)};
const JPG_MAP_BOUNDS = {{
  pixelMinX: {bbox[0]},
  pixelMinY: {bbox[1]},
  pixelMaxX: {bbox[2]},
  pixelMaxY: {bbox[3]},
  lonMin: {LON_MIN},
  lonMax: {LON_MAX},
  latMin: {LAT_MIN},
  latMax: {LAT_MAX},
}};
""",
        encoding="utf-8",
    )

    print(f"Written {OUT_JS}")
    print(f"Written {OUT_CFG}")
    print("Stats:", stats)


if __name__ == "__main__":
    main()
