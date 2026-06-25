/**
 * 三国大地图 — 基于东汉地理经纬度投影
 * 格子为四方连通；城市坐标由真实经纬度换算后微调至合适地块
 */

const MAP_WIDTH = 88;
const MAP_HEIGHT = 66;
const TILE_SIZE = 32;
const TEXTURE_SIZE = 64;
const TEXTURE_VARIANTS = 3;

const TERRAIN = {
  plain: {
    id: "plain", name: "平原", color: "#8faa5c", moveCost: 1,
    desc: "沃野千里，行军顺畅。",
    texture: "assets/tiles/plain",
  },
  forest: {
    id: "forest", name: "森林", color: "#4a7340", moveCost: 2,
    desc: "密林蔽日，弓兵之利地。",
    texture: "assets/tiles/forest",
  },
  hill: {
    id: "hill", name: "丘陵", color: "#8a9a58", moveCost: 2,
    desc: "起伏缓坡，骑兵稍缓。",
    texture: "assets/tiles/hill",
  },
  mountain: {
    id: "mountain", name: "山地", color: "#8b7355", moveCost: 3,
    desc: "峻岭险隘，难以通行。",
    texture: "assets/tiles/mountain",
  },
  river: {
    id: "river", name: "河流", color: "#5ba4c9", moveCost: 2,
    desc: "需渡河，水军可发挥。",
    texture: "assets/tiles/river",
  },
  sea: {
    id: "sea", name: "海域", color: "#2c5f7a", moveCost: 99,
    desc: "不可通行，需楼船。",
    texture: "assets/tiles/sea",
  },
  desert: {
    id: "desert", name: "沙漠", color: "#c8b070", moveCost: 2,
    desc: "沙海漫漫，补给困难。",
    texture: "assets/tiles/desert",
  },
  swamp: {
    id: "swamp", name: "沼泽", color: "#4a7050", moveCost: 3,
    desc: "泥沼湿地，步兵大耗。",
    texture: "assets/tiles/swamp",
  },
  coast: {
    id: "coast", name: "海岸", color: "#b8a878", moveCost: 1,
    desc: "沙岸临海，可泊船。",
    texture: "assets/tiles/coast",
  },
  city: {
    id: "city", name: "城池", color: "#d4a843", moveCost: 1,
    desc: "城郭坚固，可屯兵据守。",
    texture: "assets/tiles/city",
  },
};

/** 地图覆盖范围（东汉十三州大致边界） */
const GEO = {
  lonMin: 98,
  lonMax: 122,
  latMin: 18,
  latMax: 42,
};

const FACTION = {
  wei: { id: "wei", name: "魏", color: "rgba(58, 95, 150, 0.28)" },
  shu: { id: "shu", name: "蜀", color: "rgba(72, 120, 58, 0.28)" },
  wu: { id: "wu", name: "吴", color: "rgba(160, 58, 58, 0.28)" },
  neutral: { id: "neutral", name: "中立", color: "rgba(90, 82, 72, 0.12)" },
};

/** 州郡标注位置（经纬度） */
const PROVINCE_LABELS = [
  { name: "幽州", lon: 116, lat: 40 },
  { name: "并州", lon: 111, lat: 38.5 },
  { name: "冀州", lon: 115, lat: 37.5 },
  { name: "青州", lon: 118.5, lat: 36.5 },
  { name: "凉州", lon: 101, lat: 37 },
  { name: "司隶", lon: 110, lat: 34.5 },
  { name: "兖州", lon: 116, lat: 35.5 },
  { name: "豫州", lon: 114, lat: 33.5 },
  { name: "徐州", lon: 118, lat: 34.5 },
  { name: "荆州", lon: 112, lat: 30.5 },
  { name: "益州", lon: 104, lat: 30 },
  { name: "扬州", lon: 117, lat: 31 },
  { name: "交州", lon: 108, lat: 23 },
];

/**
 * 城市：经纬度参照《中国历史地图集·秦汉》与谭其骧版东汉全图
 */
const CITIES = {
  jicheng: { name: "蓟城", lon: 116.4, lat: 39.9, desc: "幽州治所，北拒乌桓。", faction: "neutral", region: "幽州" },
  jinyang: { name: "晋阳", lon: 112.5, lat: 37.9, desc: "并州重镇，控扼汾河盆地。", faction: "neutral", region: "并州" },
  ye: { name: "邺城", lon: 114.5, lat: 36.2, desc: "冀州核心，曹操北方基地。", faction: "wei", region: "冀州" },
  tianshui: { name: "天水", lon: 105.7, lat: 34.6, desc: "陇右门户，诸葛亮北伐起点。", faction: "neutral", region: "凉州" },
  changan: { name: "长安", lon: 108.9, lat: 34.3, desc: "关中古都，八水环绕。", faction: "neutral", region: "司隶" },
  luoyang: { name: "洛阳", lon: 112.4, lat: 34.6, desc: "天下之中，汉室旧都。", faction: "wei", region: "司隶" },
  chenliu: { name: "陈留", lon: 114.3, lat: 34.8, desc: "兖州门户，曹操作战起点。", faction: "wei", region: "兖州" },
  xuchang: { name: "许昌", lon: 113.8, lat: 34.0, desc: "曹操迎天子，曹魏根基。", faction: "wei", region: "豫州" },
  qiao: { name: "谯县", lon: 115.8, lat: 33.8, desc: "曹操故里，豫州东部。", faction: "wei", region: "豫州" },
  xiapi: { name: "下邳", lon: 117.9, lat: 34.3, desc: "徐州要冲，吕布据地。", faction: "neutral", region: "徐州" },
  wudu: { name: "武都", lon: 104.9, lat: 33.4, desc: "入蜀要道，蜀魏边境。", faction: "shu", region: "益州" },
  hanzhong: { name: "汉中", lon: 107.0, lat: 33.1, desc: "益州北门户，蜀魏拉锯前线。", faction: "shu", region: "益州" },
  xiangyang: { name: "襄阳", lon: 112.1, lat: 32.0, desc: "汉水与荆州北大门，兵家必争。", faction: "neutral", region: "荆州" },
  shouchun: { name: "寿春", lon: 116.8, lat: 32.6, desc: "淮南重镇，魏吴反复争夺。", faction: "wei", region: "扬州" },
  hefei: { name: "合肥", lon: 117.3, lat: 31.9, desc: "淮南屏障，孙权多次北伐。", faction: "wei", region: "扬州" },
  jianye: { name: "建业", lon: 118.8, lat: 32.0, desc: "东吴都城，据长江天险。", faction: "wu", region: "扬州" },
  wuchang: { name: "武昌", lon: 114.5, lat: 30.5, desc: "江夏重镇，控长江中游。", faction: "wu", region: "荆州" },
  jiangling: { name: "江陵", lon: 112.2, lat: 30.3, desc: "南郡核心，荆州治所。", faction: "neutral", region: "荆州" },
  yongan: { name: "永安", lon: 109.5, lat: 31.0, desc: "三峡东口，蜀吴缓冲。", faction: "shu", region: "益州" },
  chengdu: { name: "成都", lon: 104.1, lat: 30.7, desc: "益州腹地，蜀汉都城。", faction: "shu", region: "益州" },
  lujiang: { name: "庐江", lon: 117.0, lat: 31.3, desc: "江淮之间，吴魏拉锯。", faction: "wu", region: "扬州" },
  huiji: { name: "会稽", lon: 120.6, lat: 30.0, desc: "江东根基，孙策创业之地。", faction: "wu", region: "扬州" },
  changsha: { name: "长沙", lon: 113.0, lat: 28.2, desc: "荆南重镇，孙刘势力交界。", faction: "wu", region: "荆州" },
  nanhai: { name: "南海", lon: 113.3, lat: 23.1, desc: "交州门户，岭南中心。", faction: "wu", region: "交州" },
};

// ── 地理工具 ──────────────────────────────────────────────

function geoToGrid(lon, lat) {
  const x = Math.round(((lon - GEO.lonMin) / (GEO.lonMax - GEO.lonMin)) * (MAP_WIDTH - 1));
  const y = Math.round(((GEO.latMax - lat) / (GEO.latMax - GEO.latMin)) * (MAP_HEIGHT - 1));
  return [Math.max(0, Math.min(MAP_WIDTH - 1, x)), Math.max(0, Math.min(MAP_HEIGHT - 1, y))];
}

function createEmptyMap() {
  const tiles = [];
  for (let y = 0; y < MAP_HEIGHT; y++) {
    const row = [];
    for (let x = 0; x < MAP_WIDTH; x++) {
      row.push({ x, y, terrain: "sea", faction: "neutral", city: null, region: "" });
    }
    tiles.push(row);
  }
  return tiles;
}

function inBounds(x, y) {
  return x >= 0 && x < MAP_WIDTH && y >= 0 && y < MAP_HEIGHT;
}

function setTerrain(tiles, x, y, terrain) {
  if (inBounds(x, y)) tiles[y][x].terrain = terrain;
}

function fillRect(tiles, x1, y1, x2, y2, fn) {
  for (let y = y1; y <= y2; y++) {
    for (let x = x1; x <= x2; x++) {
      if (inBounds(x, y)) fn(tiles[y][x], x, y);
    }
  }
}

function drawGeoLine(tiles, points, terrain, width = 1) {
  for (let i = 0; i < points.length - 1; i++) {
    const [x0, y0] = geoToGrid(points[i][0], points[i][1]);
    const [x1, y1] = geoToGrid(points[i + 1][0], points[i + 1][1]);
    drawLine(tiles, x0, y0, x1, y1, terrain, width);
  }
}

function drawLine(tiles, x0, y0, x1, y1, terrain, width = 1) {
  const dx = Math.abs(x1 - x0);
  const dy = Math.abs(y1 - y0);
  const sx = x0 < x1 ? 1 : -1;
  const sy = y0 < y1 ? 1 : -1;
  let err = dx - dy;
  let x = x0;
  let y = y0;
  const half = Math.floor(width / 2);

  while (true) {
    for (let oy = -half; oy <= half; oy++) {
      for (let ox = -half; ox <= half; ox++) {
        if (ox * ox + oy * oy <= half * half + half) {
          setTerrain(tiles, x + ox, y + oy, terrain);
        }
      }
    }
    if (x === x1 && y === y1) break;
    const e2 = 2 * err;
    if (e2 > -dy) { err -= dy; x += sx; }
    if (e2 < dx) { err += dx; y += sy; }
  }
}

function drawGeoPoly(tiles, points, terrain) {
  const verts = points.map(([lon, lat]) => geoToGrid(lon, lat));
  let minX = MAP_WIDTH, minY = MAP_HEIGHT, maxX = 0, maxY = 0;
  for (const [x, y] of verts) {
    minX = Math.min(minX, x); minY = Math.min(minY, y);
    maxX = Math.max(maxX, x); maxY = Math.max(maxY, y);
  }
  for (let y = minY; y <= maxY; y++) {
    for (let x = minX; x <= maxX; x++) {
      if (pointInPoly(x + 0.5, y + 0.5, verts)) {
        setTerrain(tiles, x, y, terrain);
      }
    }
  }
}

function pointInPoly(x, y, verts) {
  let inside = false;
  for (let i = 0, j = verts.length - 1; i < verts.length; j = i++) {
    const [xi, yi] = verts[i];
    const [xj, yj] = verts[j];
    if ((yi > y) !== (yj > y) && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) {
      inside = !inside;
    }
  }
  return inside;
}

function isPassable(t) {
  return ["plain", "forest", "hill", "coast", "desert", "city"].includes(t.terrain);
}

function snapToLand(tiles, x, y, preferNearRiver = false) {
  if (inBounds(x, y) && isPassable(tiles[y][x])) return [x, y];
  for (let r = 1; r <= 4; r++) {
    let best = null;
    let bestScore = Infinity;
    for (let dy = -r; dy <= r; dy++) {
      for (let dx = -r; dx <= r; dx++) {
        if (Math.abs(dx) !== r && Math.abs(dy) !== r) continue;
        const nx = x + dx, ny = y + dy;
        if (!inBounds(nx, ny) || !isPassable(tiles[ny][nx])) continue;
        let score = r * 10;
        if (preferNearRiver) {
          for (const [ddx, ddy] of [[0,0],[1,0],[-1,0],[0,1],[0,-1]]) {
            const tx = nx + ddx, ty = ny + ddy;
            if (inBounds(tx, ty) && tiles[ty][tx].terrain === "river") score -= 3;
          }
        }
        if (score < bestScore) { bestScore = score; best = [nx, ny]; }
      }
    }
    if (best) return best;
  }
  return [x, y];
}

function placeCity(tiles, cityId) {
  const city = CITIES[cityId];
  if (!city) return;
  let [x, y] = geoToGrid(city.lon, city.lat);
  const nearRiver = ["xiangyang", "jiangling", "wuchang", "jianye", "yongan", "changan"].includes(cityId);
  [x, y] = snapToLand(tiles, x, y, nearRiver);
  tiles[y][x].terrain = "city";
  tiles[y][x].city = cityId;
  tiles[y][x].faction = city.faction;
  tiles[y][x].region = city.region;
}

function assignRegions(tiles) {
  const zones = [
    { name: "幽州", lon: 116, lat: 40, rx: 3.5, ry: 2.5 },
    { name: "并州", lon: 111, lat: 38, rx: 3, ry: 3 },
    { name: "冀州", lon: 115, lat: 37, rx: 3.5, ry: 2.5 },
    { name: "青州", lon: 119, lat: 36.5, rx: 3, ry: 2 },
    { name: "凉州", lon: 101, lat: 37, rx: 4, ry: 3 },
    { name: "司隶", lon: 110, lat: 34.5, rx: 3.5, ry: 2.5 },
    { name: "兖州", lon: 116.5, lat: 35.5, rx: 2.5, ry: 2 },
    { name: "豫州", lon: 114, lat: 33.5, rx: 3, ry: 2.5 },
    { name: "徐州", lon: 118, lat: 34.5, rx: 3, ry: 2 },
    { name: "荆州", lon: 112, lat: 30, rx: 4, ry: 4 },
    { name: "益州", lon: 104, lat: 30, rx: 4.5, ry: 5 },
    { name: "扬州", lon: 118, lat: 31, rx: 4, ry: 3.5 },
    { name: "交州", lon: 108, lat: 23, rx: 5, ry: 3 },
  ];
  for (const z of zones) {
    const [cx, cy] = geoToGrid(z.lon, z.lat);
    const gx = (z.rx / (GEO.lonMax - GEO.lonMin)) * MAP_WIDTH;
    const gy = (z.ry / (GEO.latMax - GEO.latMin)) * MAP_HEIGHT;
    fillRect(tiles, Math.floor(cx - gx), Math.floor(cy - gy), Math.ceil(cx + gx), Math.ceil(cy + gy), (t) => {
      if (!t.region && t.terrain !== "sea") t.region = z.name;
    });
  }
}

function assignFactions(tiles) {
  for (const row of tiles) {
    for (const t of row) {
      if (t.city || t.terrain === "sea" || t.terrain === "mountain") continue;
      const { region } = t;
      if (["冀州", "兖州", "豫州", "司隶"].includes(region)) {
        t.faction = "wei";
      } else if (region === "益州") {
        t.faction = "shu";
      } else if (["扬州", "交州"].includes(region)) {
        t.faction = "wu";
      } else if (region === "荆州") {
        const [, yangtzeY] = geoToGrid(112, 30.5);
        t.faction = t.y >= yangtzeY ? "wu" : "neutral";
      } else if (region === "徐州") {
        t.faction = "wei";
      } else {
        t.faction = "neutral";
      }
    }
  }
}

function applyTerrainOverlays(tiles) {
  // 凉州沙漠
  applyGeoTerrain(tiles, [
    [98, 36], [106, 36], [106, 40], [100, 41], [98, 38],
  ], "desert", ["plain"]);

  // 荆南沼泽
  applyGeoTerrain(tiles, [
    [109, 28], [113, 28], [114, 26], [111, 25], [108, 26],
  ], "swamp", ["plain", "forest"]);

  // 山地边缘丘陵
  for (let y = 0; y < MAP_HEIGHT; y++) {
    for (let x = 0; x < MAP_WIDTH; x++) {
      if (tiles[y][x].terrain !== "plain") continue;
      let nearMountain = false;
      for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
        const nx = x + dx, ny = y + dy;
        if (inBounds(nx, ny) && tiles[ny][nx].terrain === "mountain") {
          nearMountain = true;
          break;
        }
      }
      if (nearMountain && (x + y) % 2 === 0) tiles[y][x].terrain = "hill";
    }
  }

  // 临海海岸
  for (let y = 0; y < MAP_HEIGHT; y++) {
    for (let x = 0; x < MAP_WIDTH; x++) {
      if (!["plain", "hill"].includes(tiles[y][x].terrain)) continue;
      for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
        const nx = x + dx, ny = y + dy;
        if (inBounds(nx, ny) && tiles[ny][nx].terrain === "sea") {
          tiles[y][x].terrain = "coast";
          break;
        }
      }
    }
  }
}

function applyGeoTerrain(tiles, points, terrain, onlyReplace = ["plain"]) {
  const verts = points.map(([lon, lat]) => geoToGrid(lon, lat));
  let minX = MAP_WIDTH, minY = MAP_HEIGHT, maxX = 0, maxY = 0;
  for (const [x, y] of verts) {
    minX = Math.min(minX, x); minY = Math.min(minY, y);
    maxX = Math.max(maxX, x); maxY = Math.max(maxY, y);
  }
  for (let y = minY; y <= maxY; y++) {
    for (let x = minX; x <= maxX; x++) {
      if (pointInPoly(x + 0.5, y + 0.5, verts) && onlyReplace.includes(tiles[y][x].terrain)) {
        tiles[y][x].terrain = terrain;
      }
    }
  }
}

function buildThreeKingdomsMap() {
  const tiles = createEmptyMap();

  // 中国大陆主体轮廓（简化多边形）
  drawGeoPoly(tiles, [
    [98, 42], [105, 42], [112, 41], [118, 40], [122, 38],
    [122, 32], [121, 28], [119, 24], [115, 20], [110, 18],
    [105, 19], [100, 22], [98, 28], [98, 36],
  ], "plain");

  // 山东半岛
  drawGeoPoly(tiles, [
    [117.5, 37.5], [120, 37], [121.5, 36], [121, 35], [118, 35.5], [117, 36.5],
  ], "plain");

  // 辽东半岛
  drawGeoPoly(tiles, [
    [120, 40.5], [122, 40], [122, 38.5], [120, 39], [119, 40],
  ], "plain");

  // 燕山
  drawGeoLine(tiles, [[114, 41], [117, 40.5], [120, 39.5]], "mountain", 3);
  // 太行山
  drawGeoLine(tiles, [[110, 40], [111, 37], [112, 34], [113, 32]], "mountain", 3);
  // 秦岭
  drawGeoLine(tiles, [[104, 34], [108, 34], [112, 33.5], [116, 33]], "mountain", 4);
  // 大巴山
  drawGeoLine(tiles, [[106, 33], [109, 32], [111, 31.5]], "mountain", 3);
  // 武陵山
  drawGeoLine(tiles, [[108, 30], [111, 29.5], [113, 29]], "mountain", 2);
  // 南岭
  drawGeoLine(tiles, [[108, 26], [112, 25.5], [116, 25], [118, 26]], "mountain", 3);
  // 武夷山 / 天目山
  drawGeoLine(tiles, [[116, 28], [118, 29], [120, 30]], "mountain", 2);
  // 横断山 / 邛崃山
  drawGeoLine(tiles, [[99, 32], [101, 30], [103, 28]], "mountain", 3);

  // 巴蜀盆地内部平野
  drawGeoPoly(tiles, [
    [103, 31.5], [106, 32], [108, 31], [107, 29], [104, 29], [102, 30],
  ], "plain");

  // 长江中下游平原、华北平原标记为平
  fillRect(tiles, 0, 0, MAP_WIDTH - 1, MAP_HEIGHT - 1, (t) => {
    if (t.terrain === "sea") return;
    if (t.terrain === "plain") return;
    // 保留已有山地
  });

  // 森林：荆襄、江南丘陵（不覆盖山河）
  const forestPolys = [
    [[109, 31], [113, 31], [115, 29], [113, 27], [109, 28]],
    [[116, 31], [120, 31], [121, 29], [118, 28], [116, 29]],
  ];
  for (const poly of forestPolys) {
    const verts = poly.map(([lon, lat]) => geoToGrid(lon, lat));
    let minX = MAP_WIDTH, minY = MAP_HEIGHT, maxX = 0, maxY = 0;
    for (const [x, y] of verts) {
      minX = Math.min(minX, x); minY = Math.min(minY, y);
      maxX = Math.max(maxX, x); maxY = Math.max(maxY, y);
    }
    for (let y = minY; y <= maxY; y++) {
      for (let x = minX; x <= maxX; x++) {
        if (pointInPoly(x + 0.5, y + 0.5, verts) && tiles[y][x].terrain === "plain") {
          tiles[y][x].terrain = "forest";
        }
      }
    }
  }

  // 黄河（含河套北弯）
  drawGeoLine(tiles, [
    [103, 36], [105, 37.5], [107, 38], [110, 37],
    [112, 36], [114, 35.5], [116, 36], [118, 37.5],
    [119, 37], [120, 35.5], [121, 34.5],
  ], "river", 2);

  // 渭河
  drawGeoLine(tiles, [[104, 34.8], [106, 34.5], [108.9, 34.3]], "river", 2);

  // 汉水
  drawGeoLine(tiles, [
    [106.5, 33.5], [109, 33], [111, 32.5], [112.1, 32.0],
    [112.5, 31.2], [113.5, 30.5],
  ], "river", 2);

  // 长江
  drawGeoLine(tiles, [
    [99, 31], [102, 30.5], [104, 30.2], [106, 30.5],
    [109.5, 31], [112, 30.5], [114.5, 30.5], [116.5, 31.5],
    [118.5, 32], [121, 32],
  ], "river", 3);

  // 淮河
  drawGeoLine(tiles, [[112, 33.5], [115, 33], [117, 33], [119, 33.5]], "river", 2);

  assignRegions(tiles);

  // 按经纬度放置全部城池
  for (const id of Object.keys(CITIES)) {
    placeCity(tiles, id);
  }

  assignFactions(tiles);

  applyTerrainOverlays(tiles);

  // 州郡标注格坐标
  const provinceLabels = PROVINCE_LABELS.map((p) => {
    const [x, y] = geoToGrid(p.lon, p.lat);
    return { name: p.name, x, y };
  });

  return {
    width: MAP_WIDTH,
    height: MAP_HEIGHT,
    tileSize: TILE_SIZE,
    tiles,
    terrain: TERRAIN,
    faction: FACTION,
    cities: CITIES,
    provinceLabels,
    geo: GEO,
    textureSize: TEXTURE_SIZE,
    textureVariants: TEXTURE_VARIANTS,
  };
}

const MAP_DATA = buildThreeKingdomsMap();
