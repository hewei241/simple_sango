#!/usr/bin/env python3
"""
从根目录中国地形 JPG 栅格化生成地图数据（备选生成方式）。
主生成方式见 scripts/generate_from_api.py（经纬度 + 地理 API）。
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
DATA_DIR = ROOT / "data"
OUT_JS = ROOT / "js" / "china-terrain-data.js"
OUT_CFG = ROOT / "js" / "jpg-source-config.js"

MAP_W, MAP_H = 240, 180
LON_MIN, LON_MAX = 98.0, 123.5
LAT_MIN, LAT_MAX = 17.5, 42.0
COAST_BUFFER_CELLS = 2

TERRAIN_CHAR = {
    "sea": "s", "plain": "p", "hill": "h", "forest": "f", "mountain": "m",
    "river": "r", "desert": "d", "swamp": "w", "coast": "c",
}


def find_jpg() -> Path:
    for p in ROOT.iterdir():
        if p.suffix.lower() in (".jpg", ".jpeg") and p.is_file():
            return p
    raise FileNotFoundError("根目录未找到 JPG 地形图")


def load_china_geometry() -> dict:
    cache = DATA_DIR / "china_boundary.json"
    if not cache.exists():
        raise FileNotFoundError(f"缺少国界数据: {cache}")
    data = json.loads(cache.read_text(encoding="utf-8"))
    for feat in data.get("features", []):
        if feat.get("properties", {}).get("adcode") == 100000:
            return feat["geometry"]
    return data["features"][0]["geometry"]


def point_in_ring(lon: float, lat: float, ring: list) -> bool:
    inside = False
    n = len(ring)
    for i in range(n):
        x1, y1 = ring[i]
        x2, y2 = ring[(i + 1) % n]
        if (y1 > lat) != (y2 > lat):
            xinters = (x2 - x1) * (lat - y1) / (y2 - y1 + 1e-12) + x1
            if lon < xinters:
                inside = not inside
    return inside


def point_in_geojson(lon: float, lat: float, geometry: dict) -> bool:
    gtype = geometry["type"]
    coords = geometry["coordinates"]
    if gtype == "Polygon":
        polys = [coords]
    elif gtype == "MultiPolygon":
        polys = coords
    else:
        return False
    for poly in polys:
        if point_in_ring(lon, lat, poly[0]):
            in_hole = any(point_in_ring(lon, lat, hole) for hole in poly[1:])
            if not in_hole:
                return True
    return False


def is_content(r: int, g: int, b: int) -> bool:
    if r > 248 and g > 248 and b > 248:
        return False
    return True


def is_river_pixel(r: int, g: int, b: int) -> bool:
    lum = 0.299 * r + 0.587 * g + 0.114 * b
    return b > 140 and b > r + 26 and g > 80 and lum > 90


def is_water_pixel(r: int, g: int, b: int) -> bool:
    lum = 0.299 * r + 0.587 * g + 0.114 * b
    if b > 155 and b > r + 25 and b > g + 5:
        return True
    if b > 115 and b > r + 12 and g > 75 and lum > 100:
        return True
    if b > 95 and g > 95 and b >= r - 5 and lum > 125:
        return True
    return False


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


def classify_land_rgb(r: int, g: int, b: int, lon: float, lat: float) -> str:
    """国界内陆地：只识别地形，不把陆地误判为海。"""
    lum = 0.299 * r + 0.587 * g + 0.114 * b

    if lum < 92 and r < 108 and g < 92:
        return "mountain"
    if r > 68 and g < r - 7 and b < g and lum < 122:
        return "mountain"

    if lon < 108 and lat > 33.5:
        if r > 182 and g > 148 and b < 172 and r > b + 18:
            return "desert"
        if r > 158 and g > 128 and b < 138 and r > g + 4:
            return "desert"

    if r > 172 and g > 142 and lum > 152:
        return "hill"
    if r > 148 and g > 118 and b < 148:
        return "hill"

    if g > r + 10 and g > b + 6 and lum < 138:
        return "forest"

    if g > r + 3 and g > b and lum >= 112:
        return "plain"

    if lum > 202:
        return "plain"
    if lum > 142:
        return "hill"
    return "mountain"


def classify_coast_zone_rgb(r: int, g: int, b: int) -> str:
    """海岸带：区分浅海、海岸与近岸陆地。"""
    if is_water_pixel(r, g, b):
        lum = 0.299 * r + 0.587 * g + 0.114 * b
        if b > 95 and g > 95 and b >= r - 5 and lum > 125:
            return "coast"
        return "sea"
    return classify_land_rgb(r, g, b, 110.0, 30.0)


def build_detail_mask(china_geom: dict) -> set[tuple[int, int]]:
    """有内容区域 = 国界内陆地 + 海岸缓冲带（用于细化，不扩张远海）。"""
    land: set[tuple[int, int]] = set()
    for y in range(MAP_H):
        for x in range(MAP_W):
            lon, lat = grid_to_geo(x, y)
            if point_in_geojson(lon, lat, china_geom):
                land.add((x, y))

    detail = set(land)
    for x, y in land:
        for dy in range(-COAST_BUFFER_CELLS, COAST_BUFFER_CELLS + 1):
            for dx in range(-COAST_BUFFER_CELLS, COAST_BUFFER_CELLS + 1):
                nx, ny = x + dx, y + dy
                if 0 <= nx < MAP_W and 0 <= ny < MAP_H:
                    detail.add((nx, ny))

    return detail


def accumulate_cell_stats(region: Image.Image) -> tuple[list, list, list, list, list]:
    w, h = region.size
    px = region.load()
    rs = [[0] * MAP_W for _ in range(MAP_H)]
    gs = [[0] * MAP_W for _ in range(MAP_H)]
    bs = [[0] * MAP_W for _ in range(MAP_H)]
    counts = [[0] * MAP_W for _ in range(MAP_H)]
    rivers = [[0] * MAP_W for _ in range(MAP_H)]
    waters = [[0] * MAP_W for _ in range(MAP_H)]

    for py in range(h):
        gy = min(MAP_H - 1, int(py * MAP_H / h))
        for px_x in range(w):
            gx = min(MAP_W - 1, int(px_x * MAP_W / w))
            r, g, b = px[px_x, py]
            counts[gy][gx] += 1
            rs[gy][gx] += r
            gs[gy][gx] += g
            bs[gy][gx] += b
            if is_river_pixel(r, g, b):
                rivers[gy][gx] += 1
            if is_water_pixel(r, g, b):
                waters[gy][gx] += 1

    return rs, gs, bs, counts, rivers, waters


def apply_coast(grid: list[list[str]], land_cells: set[tuple[int, int]]) -> None:
    land_chars = {"p", "h", "f", "d", "m", "w"}
    for x, y in land_cells:
        if grid[y][x] not in land_chars:
            continue
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < MAP_W and 0 <= ny < MAP_H and grid[ny][nx] == "s":
                grid[y][x] = "c"
                break


def build_grid(
    img: Image.Image,
    bbox: tuple[int, int, int, int],
    china_geom: dict,
) -> list[list[str]]:
    min_x, min_y, max_x, max_y = bbox
    region = img.crop((min_x, min_y, max_x, max_y))
    rs, gs, bs, counts, rivers, waters = accumulate_cell_stats(region)

    land_cells: set[tuple[int, int]] = set()
    for y in range(MAP_H):
        for x in range(MAP_W):
            lon, lat = grid_to_geo(x, y)
            if point_in_geojson(lon, lat, china_geom):
                land_cells.add((x, y))

    detail_cells = build_detail_mask(china_geom)
    coast_zone = detail_cells - land_cells

    grid: list[list[str]] = []
    candidates = {"p", "h", "f"}
    river_ratio = 0.09
    water_ratio_sea = 0.55

    for y in range(MAP_H):
        row: list[str] = []
        for x in range(MAP_W):
            if (x, y) not in detail_cells:
                row.append("s")
                continue

            n = counts[y][x] or 1
            r, g, b = rs[y][x] // n, gs[y][x] // n, bs[y][x] // n
            lon, lat = grid_to_geo(x, y)
            water_frac = waters[y][x] / n

            if (x, y) in land_cells:
                if water_frac > water_ratio_sea:
                    ch = "s"
                elif water_frac > 0.25:
                    ch = "c"
                else:
                    t = classify_land_rgb(r, g, b, lon, lat)
                    ch = TERRAIN_CHAR[t]
                    if ch in candidates and rivers[y][x] / n > river_ratio:
                        ch = "r"
            else:
                t = classify_coast_zone_rgb(r, g, b)
                ch = TERRAIN_CHAR[t]

            row.append(ch)
        grid.append(row)

    apply_coast(grid, land_cells)
    return grid


def main() -> None:
    jpg = find_jpg()
    print(f"Source: {jpg.name} ({jpg.stat().st_size} bytes)")
    img = Image.open(jpg).convert("RGB")
    print(f"Image size: {img.size[0]} x {img.size[1]}")
    print(f"Grid: {MAP_W} x {MAP_H}")

    china_geom = load_china_geometry()
    bbox = detect_content_bbox(img)
    print(f"Content bbox: {bbox}")

    grid = build_grid(img, bbox, china_geom)
    rows = ["".join(r) for r in grid]
    stats: dict[str, int] = {}
    for row in rows:
        for c in row:
            stats[c] = stats.get(c, 0) + 1

    detail = len(build_detail_mask(china_geom))
    print(f"Detail cells (land+coast buffer): {detail} / {MAP_W * MAP_H}")

    OUT_JS.write_text(
        f"""/**
 * 由根目录 JPG 自动生成（scripts/generate_from_jpg.py）
 * 源图: {jpg.name} · 栅格 {MAP_W}×{MAP_H}
 * 仅细化陆地/海岸带，远海统一为海洋
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
