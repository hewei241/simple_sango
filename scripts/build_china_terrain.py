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

# ── 中国大陆海岸线 + 陆界（经纬度，顺时针）──────────────────
# 参照 Natural Earth 110m 与中国标准地图轮廓简化
CHINA_MAINLAND = [
    # 西北界
    (98.0, 42.0), (99.5, 41.8), (101.0, 41.5), (103.0, 41.8), (105.5, 42.0),
    (108.0, 42.0), (110.5, 41.5), (112.5, 41.0), (114.5, 40.5), (116.5, 40.2),
    # 辽东湾北岸
    (117.8, 40.0), (119.0, 39.8), (120.0, 39.6),
    # 辽东半岛东岸
    (121.0, 39.2), (121.8, 38.8), (122.3, 38.5), (122.7, 38.2), (122.5, 37.9),
    # 辽东半岛南岸 / 渤海东岸
    (122.0, 38.0), (121.5, 38.3), (121.0, 38.8), (120.5, 39.2),
    # 渤海海峡南岸 — 山东半岛北岸
    (119.8, 38.8), (119.2, 38.2), (118.8, 37.8), (118.5, 37.5),
    (119.0, 37.2), (119.8, 37.0), (120.5, 37.0), (121.2, 37.2),
    # 山东半岛东端成山头
    (122.0, 37.3), (122.4, 37.2), (122.5, 37.0), (122.2, 36.8),
    # 山东半岛南岸
    (121.5, 36.5), (120.8, 36.0), (120.0, 35.5), (119.5, 35.0),
    (119.0, 34.5), (119.2, 34.0), (119.8, 33.5),
    # 江苏海岸
    (120.2, 33.0), (120.8, 32.5), (121.2, 32.0), (121.5, 31.5),
    # 长江口 / 上海
    (121.8, 31.2), (122.0, 30.8), (121.8, 30.5),
    # 浙江海岸
    (121.5, 30.0), (121.2, 29.5), (120.8, 29.0), (120.5, 28.5),
    # 福建海岸
    (120.0, 28.0), (119.5, 27.0), (119.0, 26.0), (118.5, 25.0),
    (118.2, 24.5), (117.8, 24.0),
    # 广东海岸
    (117.2, 23.5), (116.5, 23.0), (115.5, 22.8), (114.5, 22.5),
    (113.5, 22.3), (112.5, 22.0), (111.5, 21.8),
    # 广西 / 北部湾
    (110.5, 21.5), (109.5, 21.3), (108.5, 21.5), (107.5, 21.8),
    # 中越边境
    (106.5, 22.2), (105.5, 22.8), (104.5, 23.2), (103.5, 23.5),
    (102.5, 23.8), (101.5, 24.2), (100.5, 24.8), (99.5, 25.5),
    # 西南界
    (98.8, 26.5), (98.5, 27.5), (98.3, 28.5), (98.2, 29.5),
    (98.5, 30.5), (98.8, 31.5), (99.0, 32.5), (98.8, 33.5),
    (98.5, 34.5), (98.3, 35.5), (98.2, 36.5), (98.0, 37.5),
    (98.0, 39.0), (98.0, 40.5), (98.0, 42.0),
]

HAINAN = [
    (108.6, 20.2), (110.5, 20.0), (111.0, 19.5), (110.8, 18.8),
    (110.0, 18.5), (109.0, 18.8), (108.5, 19.5), (108.6, 20.2),
]

# 渤海湾水域（从陆地多边形中扣除）
BOHAI_WATER = [
    (117.5, 39.8), (119.5, 39.5), (120.5, 39.0), (121.0, 38.5),
    (120.5, 38.0), (119.5, 37.8), (118.5, 38.0), (117.8, 38.5),
    (117.5, 39.0), (117.5, 39.8),
]

# 河流路径 [waypoints], width in degrees
RIVERS = [
    ("yellow", [
        (96.0, 35.5), (100.0, 35.8), (103.5, 36.0), (105.5, 37.2), (107.0, 38.5),
        (108.5, 39.5), (110.0, 40.0), (110.5, 39.0), (111.0, 37.5), (112.0, 36.5),
        (113.5, 36.0), (115.0, 35.8), (116.5, 36.2), (117.5, 37.0), (118.5, 37.5),
        (119.5, 37.2), (120.5, 36.5), (121.0, 35.5),
    ], 0.28),
    ("yangtze", [
        (98.0, 31.5), (100.0, 31.0), (102.0, 30.5), (104.0, 30.2), (106.0, 30.5),
        (108.0, 31.0), (109.5, 31.2), (111.0, 30.8), (112.5, 30.5), (114.0, 30.5),
        (115.5, 30.8), (116.5, 31.2), (117.5, 31.8), (118.5, 32.0), (119.5, 32.2),
        (120.5, 32.0), (121.5, 31.8),
    ], 0.32),
    ("wei", [(104.0, 34.8), (106.0, 34.6), (108.0, 34.4), (109.5, 34.3)], 0.18),
    ("han", [
        (106.0, 33.8), (108.0, 33.5), (109.5, 33.0), (111.0, 32.5),
        (112.1, 32.0), (112.8, 31.5), (113.5, 30.8),
    ], 0.20),
    ("huai", [(111.5, 33.5), (114.0, 33.2), (116.5, 33.0), (118.5, 33.2)], 0.18),
    ("pearl", [(112.0, 24.0), (113.0, 23.5), (113.5, 23.0), (114.0, 22.8)], 0.16),
    ("lancang", [(98.5, 28.0), (100.0, 27.5), (101.5, 27.0), (103.0, 26.5)], 0.14),
]

# 山地范围多边形
MOUNTAIN_ZONES = [
    # 青藏高原 / 青南
    [(92, 36), (102, 36), (102, 28), (92, 28)],
    # 横断山
    [(98, 32), (102, 32), (102, 26), (98, 26)],
    # 祁连山
    [(98, 40), (102, 40), (102, 36), (98, 36)],
    # 天山余脉 / 阿尔泰山南麓
    [(98, 42), (104, 42), (104, 40), (98, 40)],
    # 秦岭
    [(104, 34.5), (112, 34.5), (112, 32.5), (104, 32.5)],
    # 大巴山 / 巫山
    [(106, 32.5), (111, 32.5), (111, 30.5), (106, 30.5)],
    # 太行山
    [(112.5, 40.5), (114.5, 40.5), (114.5, 33.5), (112.5, 33.5)],
    # 燕山
    [(114, 41.5), (120, 41.5), (120, 39.5), (114, 39.5)],
    # 大兴安岭
    [(118, 42), (122, 42), (122, 40), (118, 40)],
    # 南岭
    [(108, 26.5), (118, 26.5), (118, 24.0), (108, 24.0)],
    # 武夷山 / 天目山
    [(116, 30.5), (121, 30.5), (121, 27.5), (116, 27.5)],
    # 武陵山 / 雪峰山
    [(108, 30), (112, 30), (112, 27), (108, 27)],
    # 大别山
    [(114.5, 32.5), (116.5, 32.5), (116.5, 30.5), (114.5, 30.5)],
    # 吕梁山
    [(110, 38.5), (112.5, 38.5), (112.5, 36.5), (110, 36.5)],
    # 辽东山地
    [(121, 41), (122.5, 41), (122.5, 39), (121, 39)],
]

DESERT_ZONES = [
    [(98, 42), (108, 42), (108, 37.5), (98, 37.5)],   # 戈壁 / 阿拉善
    [(98, 37.5), (102, 37.5), (102, 35.5), (98, 35.5)],  # 河西走廊西段
    [(102, 39), (106, 39), (106, 37), (102, 37)],     # 河套以北
]

FOREST_ZONES = [
    [(118, 42), (122, 42), (122, 40.5), (118, 40.5)],  # 东北森林
    [(106, 28), (112, 28), (112, 24), (106, 24)],     # 西南林区
    [(116, 31), (121, 31), (121, 28), (116, 28)],     # 东南丘陵林
    [(109, 31), (113, 31), (113, 28.5), (109, 28.5)], # 鄂西山地林
]

SWAMP_ZONES = [
    [(111.5, 29.5), (113.5, 29.5), (113.5, 28.5), (111.5, 28.5)],  # 洞庭湖
    [(115.5, 29.5), (117.5, 29.5), (117.5, 28.5), (115.5, 28.5)],  # 鄱阳湖
    [(119.5, 31.5), (121.0, 31.5), (121.0, 30.5), (119.5, 30.5)],  # 太湖
]

PLAIN_ZONES = [
    [(114, 40), (122, 40), (122, 32), (114, 32)],     # 华北 / 华东平原
    [(103, 31.5), (107.5, 31.5), (107.5, 29.5), (103, 29.5)],  # 四川盆地
    [(107, 35), (111, 35), (111, 33.5), (107, 33.5)],  # 关中平原
    [(111, 31), (116, 31), (116, 29), (111, 29)],     # 江汉平原
]

HILL_ZONES = [
    [(106, 38), (114, 38), (114, 34), (106, 34)],     # 黄土高原
    [(116, 32), (121, 32), (121, 29), (116, 29)],     # 江南丘陵
    [(104, 33), (108, 33), (108, 31), (104, 31)],     # 秦巴丘陵
]


def grid_to_geo(x: int, y: int) -> tuple[float, float]:
    lon = LON_MIN + (x / (MAP_W - 1)) * (LON_MAX - LON_MIN)
    lat = LAT_MAX - (y / (MAP_H - 1)) * (LAT_MAX - LAT_MIN)
    return lon, lat


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


def is_land(lon: float, lat: float) -> bool:
    if point_in_poly(lon, lat, HAINAN):
        return True
    if not point_in_poly(lon, lat, CHINA_MAINLAND):
        return False
    if point_in_poly(lon, lat, BOHAI_WATER):
        return False
    return True


def classify_terrain(lon: float, lat: float) -> str:
    if not is_land(lon, lat):
        return "sea"
    if near_river(lon, lat):
        return "river"
    if in_any_zone(lon, lat, MOUNTAIN_ZONES):
        # 四川盆地
        if 103.0 <= lon <= 107.5 and 29.2 <= lat <= 31.8:
            return "plain"
        # 关中平原
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
    # 默认：东部低地平原，西部山地
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


def build_grid() -> list[list[str]]:
    grid = []
    for y in range(MAP_H):
        row = []
        for x in range(MAP_W):
            lon, lat = grid_to_geo(x, y)
            t = classify_terrain(lon, lat)
            row.append(TERRAIN_CHAR[t])
        grid.append(row)
    apply_coast(grid)
    return grid


def main():
    grid = build_grid()
    rows = ["".join(r) for r in grid]
    stats: dict[str, int] = {}
    for row in rows:
        for c in row:
            stats[c] = stats.get(c, 0) + 1

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
    print(f"Written {out}")
    print("Stats:", stats)


if __name__ == "__main__":
    main()
