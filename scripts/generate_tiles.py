"""生成 64x64 三国风格地形贴图（CC0，项目自用）"""
from pathlib import Path
import random
import struct
import zlib

try:
    from PIL import Image, ImageDraw
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

SIZE = 64
OUT = Path(__file__).resolve().parent.parent / "assets" / "tiles"
VARIANTS = 3


def _rng(seed):
    r = random.Random(seed)
    return r


def _noise_pixels(seed, base, spread=18):
    r = _rng(seed)
    px = []
    for y in range(SIZE):
        row = []
        for x in range(SIZE):
            n = r.randint(-spread, spread)
            row.append(tuple(max(0, min(255, c + n)) for c in base))
        px.append(row)
    return px


def _save_png(path, pixels):
    w, h = len(pixels[0]), len(pixels)
    raw = b"".join(
        b"\x00" + bytes(pixels[y][x]) for y in range(h) for x in range(w)
    )
    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")
    path.write_bytes(png)


def _save_img(path, pixels):
    if HAS_PIL:
        img = Image.new("RGB", (SIZE, SIZE))
        img.putdata([p for row in pixels for p in row])
        img.save(path)
    else:
        _save_png(path, pixels)


def make_plain(variant):
    r = _rng(100 + variant)
    base = [(142, 176, 82), (130, 168, 74), (152, 184, 88)][variant]
    px = _noise_pixels(1000 + variant, base, 14)
    for _ in range(40):
        x, y = r.randint(2, SIZE - 3), r.randint(2, SIZE - 3)
        c = (max(0, base[0] - 25), max(0, base[1] - 20), max(0, base[2] - 15))
        for dy in range(-1, 2):
            for dx in range(-1, 2):
                if 0 <= x + dx < SIZE and 0 <= y + dy < SIZE:
                    px[y + dy][x + dx] = c
    return px


def make_forest(variant):
    r = _rng(200 + variant)
    base = [(36, 78, 38), (42, 88, 44), (30, 70, 34)][variant]
    px = _noise_pixels(2000 + variant, base, 10)
    for _ in range(14):
        cx, cy = r.randint(6, SIZE - 7), r.randint(6, SIZE - 7)
        rad = r.randint(5, 9)
        shade = (max(0, base[0] - 12), max(0, base[1] - 8), max(0, base[2] - 6))
        for y in range(max(0, cy - rad), min(SIZE, cy + rad + 1)):
            for x in range(max(0, cx - rad), min(SIZE, cx + rad + 1)):
                if (x - cx) ** 2 + (y - cy) ** 2 <= rad * rad:
                    px[y][x] = shade
        trunk = (92, 58, 28)
        for ty in range(cy, min(SIZE, cy + rad + 3)):
            if 0 <= cx < SIZE:
                px[ty][cx] = trunk
    return px


def make_hill(variant):
    r = _rng(300 + variant)
    base = [(118, 138, 72), (108, 128, 66), (128, 148, 78)][variant]
    px = _noise_pixels(3000 + variant, base, 16)
    for _ in range(3):
        cx = r.randint(10, SIZE - 10)
        cy = r.randint(20, SIZE - 8)
        for y in range(SIZE):
            for x in range(SIZE):
                d = ((x - cx) ** 2) / 120 + ((y - cy) ** 2) / 60
                if d < 1:
                    lift = int((1 - d) * 35)
                    px[y][x] = tuple(min(255, c + lift) for c in px[y][x])
    return px


def make_mountain(variant):
    r = _rng(400 + variant)
    base = [(120, 108, 88), (108, 98, 78), (132, 118, 96)][variant]
    px = _noise_pixels(4000 + variant, base, 22)
    peaks = [(SIZE // 2, 8), (18, 22), (46, 18)] if variant == 0 else [(24, 12), (40, 20)] if variant == 1 else [(32, 10), (14, 26), (50, 24)]
    for cx, cy in peaks:
        for y in range(SIZE):
            for x in range(SIZE):
                d = abs(x - cx) + (y - cy) * 1.4
                if d < 18:
                    snow = int(max(0, (18 - d) * 4))
                    rock = (90, 82, 70)
                    if snow > 20:
                        px[y][x] = (min(255, rock[0] + snow), min(255, rock[1] + snow), min(255, rock[2] + snow))
                    else:
                        px[y][x] = rock
    return px


def make_river(variant):
    r = _rng(500 + variant)
    base = (58, 130, 178)
    px = [[base for _ in range(SIZE)] for _ in range(SIZE)]
    phase = variant * 1.2
    for y in range(SIZE):
        for x in range(SIZE):
            w = int(8 * (0.5 + 0.5 * __import__("math").sin(x * 0.25 + phase + y * 0.08)))
            c = (base[0] + w, base[1] + w // 2, min(255, base[2] + w))
            px[y][x] = c
    for _ in range(6):
        y = r.randint(4, SIZE - 5)
        for x in range(SIZE):
            px[y][x] = (min(255, base[0] + 40), min(255, base[1] + 35), 255)
    return px


def make_sea(variant):
    r = _rng(600 + variant)
    base = (28, 72, 108)
    px = [[base for _ in range(SIZE)] for _ in range(SIZE)]
    phase = variant * 0.9
    for y in range(SIZE):
        for x in range(SIZE):
            w = int(6 * (0.5 + 0.5 * __import__("math").sin(x * 0.18 + y * 0.22 + phase)))
            px[y][x] = (base[0] + w, base[1] + w, min(255, base[2] + w + 5))
    for _ in range(4):
        y = r.randint(6, SIZE - 7)
        for x in range(0, SIZE, 2):
            px[y][x] = (min(255, base[0] + 25), min(255, base[1] + 30), min(255, base[2] + 20))
    return px


def make_desert(variant):
    r = _rng(700 + variant)
    base = [(210, 182, 118), (200, 172, 108), (218, 190, 128)][variant]
    px = _noise_pixels(7000 + variant, base, 12)
    for _ in range(5):
        cx = r.randint(8, SIZE - 9)
        for y in range(SIZE):
            for x in range(SIZE):
                d = ((x - cx) ** 2) / 200 + ((y - SIZE + 8) ** 2) / 80
                if d < 1:
                    px[y][x] = tuple(max(0, c - 15) for c in px[y][x])
    return px


def make_swamp(variant):
    r = _rng(800 + variant)
    base = (68, 98, 62)
    px = _noise_pixels(8000 + variant, base, 15)
    for _ in range(25):
        x, y = r.randint(0, SIZE - 1), r.randint(0, SIZE - 1)
        px[y][x] = (48, 78, 98)
    for _ in range(8):
        x, y = r.randint(4, SIZE - 5), r.randint(4, SIZE - 5)
        for dy in range(-2, 3):
            for dx in range(-2, 3):
                if 0 <= x + dx < SIZE and 0 <= y + dy < SIZE:
                    px[y + dy][x + dx] = (52, 88, 52)
    return px


def make_city(variant):
    r = _rng(900 + variant)
    base = (168, 152, 120)
    px = [[base for _ in range(SIZE)] for _ in range(SIZE)]
    wall = (140, 128, 100)
    inner = (180, 168, 138)
    margin = 6
    for y in range(SIZE):
        for x in range(SIZE):
            if x < margin or y < margin or x >= SIZE - margin or y >= SIZE - margin:
                px[y][x] = wall
            elif (x == margin or y == margin or x == SIZE - margin - 1 or y == SIZE - margin - 1) and (x + y) % 4 == 0:
                px[y][x] = (100, 90, 72)
            else:
                px[y][x] = inner
    # 角楼
    for cx, cy in [(margin, margin), (SIZE - margin - 1, margin), (margin, SIZE - margin - 1), (SIZE - margin - 1, SIZE - margin - 1)]:
        for dy in range(-2, 3):
            for dx in range(-2, 3):
                if 0 <= cx + dx < SIZE and 0 <= cy + dy < SIZE:
                    px[cy + dy][cx + dx] = (120, 100, 80)
    # 城中道路
    mid = SIZE // 2
    for i in range(margin + 2, SIZE - margin - 2):
        px[mid][i] = (150, 138, 110)
        px[i][mid] = (150, 138, 110)
    return px


def make_coast(variant):
    r = _rng(950 + variant)
    sand = (194, 178, 128)
    px = [make_plain(variant)[y] for y in range(SIZE)]
    water_line = 42 + variant * 3
    for y in range(SIZE):
        for x in range(SIZE):
            if y > water_line + r.randint(-2, 2):
                px[y][x] = (38, 98, 138)
            elif y > water_line - 8:
                px[y][x] = sand
    return px


GENERATORS = {
    "plain": make_plain,
    "forest": make_forest,
    "hill": make_hill,
    "mountain": make_mountain,
    "river": make_river,
    "sea": make_sea,
    "desert": make_desert,
    "swamp": make_swamp,
    "city": make_city,
    "coast": make_coast,
}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for name, fn in GENERATORS.items():
        for v in range(VARIANTS):
            path = OUT / f"{name}_{v}.png"
            pixels = fn(v)
            _save_img(path, pixels)
            print(f"  {path.name}")
    # 兼容旧文件名（默认 variant 0）
    for name in GENERATORS:
        src = OUT / f"{name}_0.png"
        dst = OUT / f"{name}.png"
        dst.write_bytes(src.read_bytes())
        print(f"  {dst.name} (alias)")


if __name__ == "__main__":
    print("Generating terrain tiles...")
    main()
    print("Done.")
