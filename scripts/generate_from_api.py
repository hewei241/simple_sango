#!/usr/bin/env python3
"""
从公开地理 API 生成中国地形栅格：
  - 国界/海岸线：阿里云 DataV GeoJSON
  - 海拔：Open-Meteo Elevation API (Copernicus DEM 90m)
  - 河流：Natural Earth 50m 矢量（GitHub 镜像）
输出 js/china-terrain-data.js
"""
from __future__ import annotations
import json
import math
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
OUT_JS = ROOT / "js" / "china-terrain-data.js"

MAP_W, MAP_H = 120, 90
LON_MIN, LON_MAX = 98.0, 123.5
LAT_MIN, LAT_MAX = 17.5, 42.0

CHINA_GEOJSON_URL = "https://geo.datav.aliyun.com/areas_v3/bound/100000.json"
RIVERS_GEOJSON_URL = (
    "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/"
    "master/geojson/ne_50m_rivers_lake_centerlines.geojson"
)
ELEVATION_API = "https://api.open-meteo.com/v1/elevation"

TERRAIN_CHAR = {
    "sea": "s", "plain": "p", "hill": "h", "forest": "f", "mountain": "m",
    "river": "r", "desert": "d", "swamp": "w", "coast": "c",
}


def fetch_json(url: str, cache: Path) -> dict | list:
    cache.parent.mkdir(parents=True, exist_ok=True)
    if cache.exists():
        print(f"  cache: {cache.name}")
        return json.loads(cache.read_text(encoding="utf-8"))
    print(f"  download: {url}")
    req = urllib.request.Request(url, headers={"User-Agent": "simple-sango/1.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    cache.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return data


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


def load_china_geometry() -> dict:
    data = fetch_json(CHINA_GEOJSON_URL, DATA_DIR / "china_boundary.json")
    for feat in data["features"]:
        if feat.get("properties", {}).get("adcode") == 100000:
            return feat["geometry"]
    return data["features"][0]["geometry"]


def extract_linestrings(geojson: dict) -> list[list[tuple[float, float]]]:
    lines = []
    for feat in geojson.get("features", []):
        geom = feat["geometry"]
        gtype = geom["type"]
        coords = geom["coordinates"]
        if gtype == "LineString":
            lines.append([(p[0], p[1]) for p in coords])
        elif gtype == "MultiLineString":
            for part in coords:
                lines.append([(p[0], p[1]) for p in part])
    return lines


def dist_point_segment(px, py, x1, y1, x2, y2) -> float:
    dx, dy = x2 - x1, y2 - y1
    if dx == 0 and dy == 0:
        return math.hypot(px - x1, py - y1)
    t = max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (x1 + t * dx), py - (y1 + t * dy))


def grid_to_geo(x: int, y: int) -> tuple[float, float]:
    lon = LON_MIN + (x / (MAP_W - 1)) * (LON_MAX - LON_MIN)
    lat = LAT_MAX - (y / (MAP_H - 1)) * (LAT_MAX - LAT_MIN)
    return lon, lat


def fetch_elevations_land(
    land_points: list[tuple[int, int, float, float]],
) -> dict[tuple[int, int], float]:
    """仅对陆地点批量查询海拔，支持断点缓存。"""
    cache_file = DATA_DIR / f"elevation_land_{MAP_W}x{MAP_H}.json"
    result: dict[tuple[int, int], float] = {}

    if cache_file.exists():
        cached = json.loads(cache_file.read_text(encoding="utf-8"))
        for item in cached.get("points", []):
            result[(item["x"], item["y"])] = item["elev"]
        print(f"  cache loaded: {len(result)}/{len(land_points)}")

    pending = [(x, y, lon, lat) for x, y, lon, lat in land_points if (x, y) not in result]
    if not pending:
        return result

    batch_size = 50
    total_batches = (len(pending) + batch_size - 1) // batch_size
    print(f"  fetching elevation: {len(pending)} land cells, {total_batches} batches...")

    for i in range(0, len(pending), batch_size):
        batch = pending[i : i + batch_size]
        lats = ",".join(f"{lat:.4f}" for _, _, lon, lat in batch)
        lons = ",".join(f"{lon:.4f}" for _, _, lon, lat in batch)
        params = urllib.parse.urlencode({"latitude": lats, "longitude": lons})
        url = f"{ELEVATION_API}?{params}"
        req = urllib.request.Request(url, headers={"User-Agent": "simple-sango/1.0"})

        for attempt in range(5):
            try:
                with urllib.request.urlopen(req, timeout=45) as resp:
                    elevs = json.loads(resp.read().decode("utf-8"))["elevation"]
                for (x, y, _, _), elev in zip(batch, elevs):
                    result[(x, y)] = elev
                # 增量写入缓存
                cache_file.write_text(
                    json.dumps({
                        "points": [{"x": x, "y": y, "elev": e} for (x, y), e in result.items()]
                    }, ensure_ascii=False),
                    encoding="utf-8",
                )
                break
            except urllib.error.HTTPError as e:
                wait = 3 * (attempt + 1)
                print(f"    HTTP {e.code}, wait {wait}s (retry {attempt + 1})")
                time.sleep(wait)
            except Exception as e:
                wait = 2 * (attempt + 1)
                print(f"    error: {e}, wait {wait}s")
                time.sleep(wait)
        else:
            raise RuntimeError(f"elevation fetch failed at batch {i // batch_size}")

        done = min(i + batch_size, len(pending))
        print(f"    {done}/{len(pending)}")
        time.sleep(0.8)

    return result


def near_river(lon: float, lat: float, river_lines: list, width: float = 0.18) -> bool:
    for line in river_lines:
        for i in range(len(line) - 1):
            x1, y1 = line[i]
            x2, y2 = line[i + 1]
            if max(x1, x2) < lon - width or min(x1, x2) > lon + width:
                continue
            if max(y1, y2) < lat - width or min(y1, y2) > lat + width:
                continue
            if dist_point_segment(lon, lat, x1, y1, x2, y2) < width:
                return True
    return False


def classify(lon: float, lat: float, elev: float, is_land: bool, river_lines: list) -> str:
    if not is_land:
        return "sea"
    if near_river(lon, lat, river_lines):
        return "river"

    # 沙漠：西北干旱区（低海拔荒漠）
    if lon < 106 and lat > 35.5 and elev < 1800:
        if lon < 103 or (lat > 37.5 and elev < 1400):
            return "desert"
    if lon < 102 and 34 < lat < 37 and elev < 1600:
        return "desert"

    # 沼泽：低海拔湖盆
    if elev < 50 and 28.5 < lat < 30 and 111 < lon < 118:
        return "swamp"

    # 按真实海拔分级
    if elev < 200:
        return "plain"
    if elev < 500:
        return "hill"
    if elev < 1200:
        if lon > 110 and 25 < lat < 35:
            return "forest"
        return "hill"
    if elev < 2500:
        return "mountain"
    return "mountain"


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


def build_grid(china_geom: dict, river_lines: list) -> list[list[str]]:
    land_points: list[tuple[int, int, float, float]] = []
    for y in range(MAP_H):
        for x in range(MAP_W):
            lon, lat = grid_to_geo(x, y)
            if point_in_geojson(lon, lat, china_geom):
                land_points.append((x, y, lon, lat))

    print(f"  land cells: {len(land_points)} / {MAP_W * MAP_H}")
    elev_map = fetch_elevations_land(land_points)

    grid: list[list[str]] = []
    for y in range(MAP_H):
        row = []
        for x in range(MAP_W):
            lon, lat = grid_to_geo(x, y)
            is_land = (x, y) in elev_map
            elev = elev_map.get((x, y), -999.0)
            t = classify(lon, lat, elev, is_land, river_lines)
            row.append(TERRAIN_CHAR[t])
        grid.append(row)

    apply_coast(grid)
    return grid


def main():
    print("=== Generate terrain from geographic APIs ===")
    print("1) China boundary (Aliyun DataV)")
    china_geom = load_china_geometry()

    print("2) Rivers (Natural Earth 50m)")
    rivers_data = fetch_json(RIVERS_GEOJSON_URL, DATA_DIR / "rivers_50m.json")
    river_lines = extract_linestrings(rivers_data)
    # 只保留与中国范围相交的河段
    river_lines = [
        line for line in river_lines
        if any(LON_MIN - 1 <= p[0] <= LON_MAX + 1 and LAT_MIN - 1 <= p[1] <= LAT_MAX + 1 for p in line)
    ]
    print(f"  river segments in bbox: {len(river_lines)}")

    print("3) Elevation + classify")
    grid = build_grid(china_geom, river_lines)

    rows = ["".join(r) for r in grid]
    stats: dict[str, int] = {}
    for row in rows:
        for c in row:
            stats[c] = stats.get(c, 0) + 1

    OUT_JS.write_text(
        f"""/**
 * 地理 API 自动生成（scripts/generate_from_api.py）
 * 国界: geo.datav.aliyun.com | 海拔: open-meteo.com | 河流: Natural Earth 50m
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
    print(f"\nWritten {OUT_JS}")
    print("Stats:", stats)


if __name__ == "__main__":
    main()
