#!/usr/bin/env python3
"""
根据中国地理轮廓与地形分区，栅格化生成地图地形数据。
输出 js/china-terrain-data.js
"""
from __future__ import annotations
import json
import math
from pathlib import Path

MAP_W, MAP_H = 88, 66
LON_MIN, LON_MAX = 98.0, 123.5
LAT_MIN, LAT_MAX = 17.5, 42.0

TERRAIN_CHAR = {
    "sea": "s", "plain": "p", "hill": "h", "forest": "f", "mountain": "m",
    "river": "r", "desert": "d", "swamp": "w", "coast": "c",
}

# ── 城市参考：经纬度 + 期望地形（与 map-data.js CITIES 一致）──────────
CITY_TERRAIN_REF = [
    ("蓟城", 116.4, 39.9, "plain"),
    ("晋阳", 112.5, 37.9, "hill"),
    ("邺城", 114.5, 36.2, "plain"),
    ("天水", 105.7, 34.6, "hill"),
    ("长安", 108.9, 34.3, "plain"),
    ("洛阳", 112.4, 34.6, "plain"),
    ("陈留", 114.3, 34.8, "plain"),
    ("许昌", 113.8, 34.0, "plain"),
    ("谯县", 115.8, 33.8, "plain"),
    ("下邳", 117.9, 34.3, "plain"),
    ("武都", 104.9, 33.4, "hill"),
    ("汉中", 107.0, 33.1, "plain"),
    ("襄阳", 112.1, 32.0, "plain"),
    ("寿春", 116.8, 32.6, "plain"),
    ("合肥", 117.3, 31.9, "plain"),
    ("建业", 118.8, 32.0, "plain"),
    ("武昌", 114.5, 30.5, "plain"),
    ("江陵", 112.2, 30.3, "plain"),
    ("永安", 109.5, 31.0, "hill"),
    ("成都", 104.1, 30.7, "plain"),
    ("庐江", 117.0, 31.3, "plain"),
    ("会稽", 120.6, 30.0, "plain"),
    ("长沙", 113.0, 28.2, "plain"),
    ("南海", 113.3, 23.1, "plain"),
]

# ── 中国大陆陆界（顺时针，严格沿陆地外缘，不横跨海湾）────────────
CHINA_MAINLAND = [
    # 西北 / 北界
    (98.0, 42.0), (100.0, 41.8), (102.5, 41.5), (105.0, 42.0),
    (108.0, 41.8), (110.5, 41.2), (112.5, 40.8), (114.5, 40.3),
    # 渤海西岸 / 华北北部（山海关一线，不向东横跨海湾）
    (115.8, 40.0), (116.8, 39.6), (117.5, 39.2), (118.0, 38.8),
    # 山东半岛北岸（渤海南岸，自西向东）
    (118.6, 38.2), (119.2, 37.8), (119.8, 37.4), (120.4, 37.1),
    (121.0, 37.0), (121.8, 37.1), (122.3, 37.2),
    # 成山头
    (122.5, 37.0), (122.4, 36.8), (122.0, 36.6),
    # 山东半岛南岸
    (121.2, 36.2), (120.5, 35.8), (119.8, 35.3), (119.2, 34.8),
    (119.0, 34.2), (119.5, 33.6),
    # 江苏 / 长江口
    (120.0, 33.2), (120.6, 32.8), (121.0, 32.3), (121.4, 31.8),
    (121.7, 31.3), (121.9, 30.9), (121.8, 30.5),
    # 浙江
    (121.5, 30.0), (121.2, 29.4), (120.8, 28.8), (120.4, 28.2),
    # 福建
    (120.0, 27.5), (119.5, 26.5), (119.0, 25.5), (118.5, 24.8),
    (118.0, 24.2), (117.5, 23.8),
    # 广东
    (116.8, 23.3), (116.0, 23.0), (115.0, 22.7), (114.0, 22.5),
    (113.0, 22.2), (112.0, 22.0), (111.0, 21.8),
    # 广西 / 北部湾
    (110.0, 21.5), (109.0, 21.3), (108.0, 21.5), (107.0, 21.8),
    # 中越边境
    (106.0, 22.2), (105.0, 22.8), (104.0, 23.2), (103.0, 23.6),
    (102.0, 24.0), (101.0, 24.5), (100.0, 25.0), (99.0, 25.8),
    # 西南界
    (98.8, 26.8), (98.5, 27.8), (98.3, 28.8), (98.2, 29.8),
    (98.4, 30.8), (98.6, 31.8), (98.8, 32.8), (98.6, 33.8),
    (98.4, 34.8), (98.2, 35.8), (98.1, 36.8), (98.0, 38.0),
    (98.0, 40.0), (98.0, 42.0),
]

# 辽东半岛（东缘收紧，避免伸入黄海）
LIAODONG = [
    (120.2, 40.2), (121.0, 40.0), (121.8, 39.6), (122.0, 39.2), (122.1, 38.8),
    (122.1, 38.4), (122.0, 38.0), (121.7, 37.9), (121.2, 38.2), (120.8, 38.6),
    (120.3, 39.0), (120.0, 39.5), (119.8, 40.0), (120.2, 40.2),
]

HAINAN = [
    (108.6, 20.2), (110.5, 20.0), (111.0, 19.5), (110.8, 18.8),
    (110.0, 18.5), (109.0, 18.8), (108.5, 19.5), (108.6, 20.2),
]

# 强制为海的水域（覆盖多边形误差）
SEA_ZONES = [
    # 渤海
    [(117.2, 40.2), (120.0, 40.2), (120.0, 37.8), (117.2, 37.8)],
    # 辽东湾
    [(119.5, 40.5), (120.5, 40.5), (120.5, 39.0), (119.5, 39.0)],
    # 黄海（辽东半岛以东，兜底）
    [(122.15, 40.5), (123.5, 40.5), (123.5, 38.0), (122.15, 38.0)],
    # 黄海（山东半岛以东）
    [(122.5, 37.5), (123.5, 37.5), (123.5, 32.0), (122.5, 32.0)],
    # 东海（大陆架外缘兜底）
    [(122.0, 32.0), (123.5, 32.0), (123.5, 27.0), (122.0, 27.0)],
]

RIVERS = [
    ("yellow", [
        (96.0, 35.5), (100.0, 35.8), (103.5, 36.0), (105.5, 37.2), (107.0, 38.5),
        (108.5, 39.5), (110.0, 40.0), (110.5, 39.0), (111.0, 37.5), (112.0, 36.5),
        (113.5, 36.0), (115.0, 35.8), (116.5, 36.2), (117.5, 37.0), (118.5, 37.5),
        (119.2, 37.2),
    ], 0.26),
    ("yangtze", [
        (98.0, 31.5), (100.0, 31.0), (102.0, 30.5), (104.0, 30.2), (106.0, 30.5),
        (108.0, 31.0), (109.5, 31.2), (111.0, 30.8), (112.5, 30.5), (114.0, 30.5),
        (115.5, 30.8), (116.5, 31.2), (117.5, 31.8), (118.5, 32.0), (119.5, 32.0),
        (120.5, 31.8), (121.2, 31.5),
    ], 0.30),
    ("wei", [(104.0, 34.8), (106.0, 34.6), (108.0, 34.4), (108.9, 34.3)], 0.16),
    ("han", [
        (106.0, 33.8), (108.0, 33.5), (109.5, 33.0), (111.0, 32.5),
        (112.1, 32.0), (112.8, 31.5), (113.5, 30.8),
    ], 0.18),
    ("huai", [(111.5, 33.5), (114.0, 33.2), (116.5, 33.0), (118.5, 33.2)], 0.16),
    ("pearl", [(112.0, 24.0), (113.0, 23.5), (113.5, 23.0), (114.0, 22.8)], 0.14),
    ("lancang", [(98.5, 28.0), (100.0, 27.5), (101.5, 27.0), (103.0, 26.5)], 0.12),
]

MOUNTAIN_ZONES = [
    [(92, 36), (102, 36), (102, 28), (92, 28)],       # 青藏高原东缘
    [(98, 32), (102, 32), (102, 26), (98, 26)],         # 横断山
    [(98, 40), (102, 40), (102, 36), (98, 36)],         # 祁连山
    [(104, 34.5), (112, 34.5), (112, 32.5), (104, 32.5)],  # 秦岭
    [(106, 32.5), (111, 32.5), (111, 30.5), (106, 30.5)],   # 大巴山 / 巫山
    [(112.5, 40.5), (114.5, 40.5), (114.5, 33.5), (112.5, 33.5)],  # 太行山
    [(114, 41.0), (119.5, 41.0), (119.5, 39.5), (114, 39.5)],     # 燕山（不伸入海上）
    [(118, 41.5), (121.0, 41.5), (121.0, 40.0), (118, 40.0)],     # 大兴安岭南麓
    [(108, 26.5), (118, 26.5), (118, 24.0), (108, 24.0)],         # 南岭
    [(116, 30.5), (120.5, 30.5), (120.5, 27.5), (116, 27.5)],     # 武夷 / 天目
    [(108, 30), (112, 30), (112, 27), (108, 27)],                 # 武陵山
    [(114.5, 32.5), (116.5, 32.5), (116.5, 30.5), (114.5, 30.5)], # 大别山
    [(110, 38.5), (112.5, 38.5), (112.5, 36.5), (110, 36.5)],     # 吕梁山
]

DESERT_ZONES = [
    [(98, 42), (106, 42), (106, 37.5), (98, 37.5)],
    [(98, 37.5), (102, 37.5), (102, 35.5), (98, 35.5)],
    [(102, 39), (106, 39), (106, 37), (102, 37)],
]

FOREST_ZONES = [
    [(118, 41.5), (121.0, 41.5), (121.0, 40.0), (118, 40.0)],
    [(106, 28), (112, 28), (112, 24), (106, 24)],
    [(116, 31), (120.5, 31), (120.5, 28), (116, 28)],
    [(109, 31), (113, 31), (113, 28.5), (109, 28.5)],
]

SWAMP_ZONES = [
    [(111.5, 29.5), (113.5, 29.5), (113.5, 28.5), (111.5, 28.5)],
    [(115.5, 29.5), (117.5, 29.5), (117.5, 28.5), (115.5, 28.5)],
    [(119.5, 31.5), (121.0, 31.5), (121.0, 30.5), (119.5, 30.5)],
]

PLAIN_ZONES = [
    [(114, 40), (119.5, 40), (119.5, 32), (114, 32)],   # 华北 / 华东平原（不含海上）
    [(103, 31.5), (107.5, 31.5), (107.5, 29.5), (103, 29.5)],  # 四川盆地
    [(107, 35), (111, 35), (111, 33.5), (107, 33.5)],   # 关中
    [(111, 31), (116, 31), (116, 29), (111, 29)],        # 江汉平原
]

HILL_ZONES = [
    [(106, 38), (114, 38), (114, 34), (106, 34)],        # 黄土高原
    [(116, 32), (120.5, 32), (120.5, 29), (116, 29)],    # 江南丘陵
    [(104, 33), (108, 33), (108, 31), (104, 31)],        # 秦巴
    [(112.5, 37.5), (114.5, 37.5), (114.5, 36.0), (112.5, 36.0)],  # 晋冀丘陵
]


def grid_to_geo(x: int, y: int) -> tuple[float, float]:
    lon = LON_MIN + (x / (MAP_W - 1)) * (LON_MAX - LON_MIN)
    lat = LAT_MAX - (y / (MAP_H - 1)) * (LAT_MAX - LAT_MIN)
    return lon, lat


def geo_to_grid(lon: float, lat: float) -> tuple[int, int]:
    x = round(((lon - LON_MIN) / (LON_MAX - LON_MIN)) * (MAP_W - 1))
    y = round(((LAT_MAX - lat) / (LAT_MAX - LAT_MIN)) * (MAP_H - 1))
    return max(0, min(MAP_W - 1, x)), max(0, min(MAP_H - 1, y))


def point_in_poly(lon: float, lat: float, poly: list[tuple[float, float]]) -> bool:
    inside = False
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        if (y1 > lat) != (y2 > lat):
            xinters = (x2 - x1) * (lat - y1) / (y2 - y1 + 1e-12) + x1
            if lon < xinters:
                inside = not inside
    return inside


def dist_point_segment(px, py, x1, y1, x2, y2) -> float:
    dx, dy = x2 - x1, y2 - y1
    if dx == 0 and dy == 0:
        return math.hypot(px - x1, py - y1)
    t = max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (x1 + t * dx), py - (y1 + t * dy))


def near_river(lon: float, lat: float) -> bool:
    for _, pts, width in RIVERS:
        for i in range(len(pts) - 1):
            d = dist_point_segment(lon, lat, pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1])
            if d < width:
                return True
    return False


def in_any_zone(lon: float, lat: float, zones: list) -> bool:
    return any(point_in_poly(lon, lat, z) for z in zones)


def is_forced_sea(lon: float, lat: float) -> bool:
    return in_any_zone(lon, lat, SEA_ZONES)


def is_land(lon: float, lat: float) -> bool:
    if is_forced_sea(lon, lat):
        return False
    if point_in_poly(lon, lat, HAINAN):
        return True
    if point_in_poly(lon, lat, LIAODONG):
        return True
    if point_in_poly(lon, lat, CHINA_MAINLAND):
        return True
    return False


def classify_terrain(lon: float, lat: float) -> str:
    if not is_land(lon, lat):
        return "sea"
    if near_river(lon, lat):
        return "river"
    if in_any_zone(lon, lat, MOUNTAIN_ZONES):
        if 103.0 <= lon <= 107.5 and 29.2 <= lat <= 31.8:
            return "plain"
        if 107.0 <= lon <= 110.5 and 33.5 <= lat <= 35.2:
            return "plain"
        return "mountain"
    if in_any_zone(lon, lat, DESERT_ZONES):
        return "desert"
    if in_any_zone(lon, lat, SWAMP_ZONES):
        return "swamp"
    if in_any_zone(lon, lat, PLAIN_ZONES):
        return "plain"
    if in_any_zone(lon, lat, FOREST_ZONES):
        return "forest"
    if in_any_zone(lon, lat, HILL_ZONES):
        return "hill"
    if lon >= 110 and lat >= 28:
        return "plain"
    if lon < 104:
        return "mountain"
    return "hill"


def apply_coast(grid: list[list[str]]) -> None:
    for y in range(MAP_H):
        for x in range(MAP_W):
            if grid[y][x] not in ("p", "h", "f", "d"):
                continue
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if 0 <= nx < MAP_W and 0 <= ny < MAP_H and grid[ny][nx] == "s":
                    grid[y][x] = "c"
                    break


def apply_city_terrain_hints(grid: list[list[str]]) -> list[str]:
    """按城市经纬度微调地形，确保城池落在合理地块。"""
    notes = []
    for name, lon, lat, expected in CITY_TERRAIN_REF:
        x, y = geo_to_grid(lon, lat)
        cur = grid[y][x]
        cur_name = {v: k for k, v in TERRAIN_CHAR.items()}[cur]
        on_river = near_river(lon, lat)

        if cur in ("s", "m"):
            grid[y][x] = TERRAIN_CHAR[expected]
            notes.append(f"  {name}: {cur_name} -> {expected}")
        elif expected == "plain" and cur in ("d", "h") and not on_river:
            grid[y][x] = "p"
            notes.append(f"  {name}: {cur_name} -> plain")
        elif expected == "hill" and cur in ("s", "p") and not on_river:
            grid[y][x] = "h"
            notes.append(f"  {name}: {cur_name} -> hill")
    return notes


def build_grid() -> list[list[str]]:
    grid = []
    for y in range(MAP_H):
        row = []
        for x in range(MAP_W):
            lon, lat = grid_to_geo(x, y)
            t = classify_terrain(lon, lat)
            row.append(TERRAIN_CHAR[t])
        grid.append(row)
    apply_city_terrain_hints(grid)
    apply_coast(grid)
    return grid


def validate_cities(grid: list[list[str]]) -> None:
    print("\n城市地形校验:")
    for name, lon, lat, expected in CITY_TERRAIN_REF:
        x, y = geo_to_grid(lon, lat)
        t = grid[y][x]
        t_name = {v: k for k, v in TERRAIN_CHAR.items()}[t]
        ok = t_name in (expected, "river", "coast", "forest", "hill")
        flag = "OK" if ok else "!!"
        print(f"  {flag} {name} ({lon},{lat}) -> grid({x},{y}) {t_name} (期望~{expected})")


def main():
    grid = build_grid()
    rows = ["".join(r) for r in grid]
    stats: dict[str, int] = {}
    for row in rows:
        for c in row:
            stats[c] = stats.get(c, 0) + 1

    # 检查右上海域
    bad = 0
    for y in range(MAP_H):
        for x in range(MAP_W):
            lon, lat = grid_to_geo(x, y)
            if lon > 121.5 and lat > 38 and grid[y][x] != "s":
                bad += 1
    print(f"NE sea land cells (lon>121.5, lat>38): {bad}")

    validate_cities(grid)

    out = Path(__file__).resolve().parent.parent / "js" / "china-terrain-data.js"
    content = f"""/**
 * 自动生成的中国地形栅格（scripts/build_china_terrain.py）
 * 字符: s=海 p=平原 h=丘陵 f=森林 m=山地 r=河 d=沙漠 w=沼泽 c=海岸
 */
const CHINA_TERRAIN_ROWS = {json.dumps(rows, ensure_ascii=False)};

const CHINA_TERRAIN_DECODE = {{
  s: "sea", p: "plain", h: "hill", f: "forest", m: "mountain",
  r: "river", d: "desert", w: "swamp", c: "coast",
}};
"""
    out.write_text(content, encoding="utf-8")
    print(f"\nWritten {out}")
    print("Stats:", stats)


if __name__ == "__main__":
    main()
