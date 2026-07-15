/**
 * 地图渲染器 — 纯地形模式
 */
class MapRenderer {
  constructor(canvas, mapData) {
    this.canvas = canvas;
    this.ctx = canvas.getContext("2d");
    this.map = mapData;
    this.terrainOnly = mapData.terrainOnly !== false;
    this.scale = 1;
    this.offsetX = 0;
    this.offsetY = 0;
    this.hoveredTile = null;
    this.selectedTile = null;
    this.texturesReady = false;
    this.jpgImage = null;
    this.jpgBounds = null;
    this.viewMode = "grid"; // grid = 识别地形色块, jpg = 原图对照
    this.axisPadLeft = 40;
    this.axisPadBottom = 28;

    this._resize();
    window.addEventListener("resize", () => this._resize());
  }

  setTexturesReady(ready) {
    this.texturesReady = ready && !this.terrainOnly;
    this.draw();
  }

  setJpgSource(img, bounds) {
    this.jpgImage = img;
    this.jpgBounds = bounds;
    this.draw();
  }

  setViewMode(mode) {
    if (mode !== "grid" && mode !== "jpg") return;
    this.viewMode = mode;
    this.draw();
  }

  _jpgCellRect(x, y) {
    const b = this.jpgBounds;
    const w = b.pixelMaxX - b.pixelMinX;
    const h = b.pixelMaxY - b.pixelMinY;
    const cellW = w / this.map.width;
    const cellH = h / this.map.height;
    return {
      sx: b.pixelMinX + x * cellW,
      sy: b.pixelMinY + y * cellH,
      sw: cellW,
      sh: cellH,
    };
  }

  _resize() {
    const parent = this.canvas.parentElement;
    const dpr = window.devicePixelRatio || 1;
    this.canvas.width = parent.clientWidth * dpr;
    this.canvas.height = parent.clientHeight * dpr;
    this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    this.displayWidth = parent.clientWidth;
    this.displayHeight = parent.clientHeight;
    this._fitToView();
    this.draw();
  }

  _fitToView() {
    const mapW = this.map.width * this.map.tileSize;
    const mapH = this.map.height * this.map.tileSize;
    const padTop = 12;
    const padRight = 12;
    const availW = this.displayWidth - this.axisPadLeft - padRight;
    const availH = this.displayHeight - this.axisPadBottom - padTop;
    const scaleX = availW / mapW;
    const scaleY = availH / mapH;
    this.scale = Math.min(scaleX, scaleY, 2.5);
    this.offsetX = this.axisPadLeft + (availW - mapW * this.scale) / 2;
    this.offsetY = padTop + (availH - mapH * this.scale) / 2;
  }

  _axisStep(ts) {
    const minGap = 42;
    const raw = Math.max(1, Math.ceil(minGap / ts));
    for (const n of [1, 2, 5, 10, 15, 20, 25, 30, 50]) {
      if (n >= raw) return n;
    }
    return 50;
  }

  _axisLabels(max, step) {
    const labels = [];
    for (let i = 0; i < max; i += step) labels.push(i);
    if (labels[labels.length - 1] !== max - 1) labels.push(max - 1);
    return labels;
  }

  _drawAxes(ts) {
    const { ctx, map } = this;
    const mapW = map.width * ts;
    const mapH = map.height * ts;
    const xStep = this._axisStep(ts);
    const yStep = this._axisStep(ts);

    ctx.save();
    ctx.font = "11px Microsoft YaHei, PingFang SC, sans-serif";

    ctx.strokeStyle = "rgba(201, 162, 39, 0.4)";
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(this.offsetX, this.offsetY + mapH);
    ctx.lineTo(this.offsetX + mapW, this.offsetY + mapH);
    ctx.moveTo(this.offsetX, this.offsetY);
    ctx.lineTo(this.offsetX, this.offsetY + mapH);
    ctx.stroke();

    ctx.fillStyle = "#a89878";
    ctx.textAlign = "center";
    ctx.textBaseline = "top";
    for (const x of this._axisLabels(map.width, xStep)) {
      const cx = this.offsetX + x * ts + ts / 2;
      if (cx < this.axisPadLeft - 8 || cx > this.displayWidth + 8) continue;
      const ty = this.offsetY + mapH + 4;
      if (ty + 10 > this.displayHeight) continue;
      ctx.fillText(String(x), cx, ty);
    }

    ctx.textAlign = "right";
    ctx.textBaseline = "middle";
    for (const y of this._axisLabels(map.height, yStep)) {
      const cy = this.offsetY + y * ts + ts / 2;
      if (cy < -ts || cy > this.displayHeight + ts) continue;
      ctx.fillText(String(y), this.axisPadLeft - 6, cy);
    }

    ctx.fillStyle = "#c9a227";
    ctx.font = "10px Microsoft YaHei, PingFang SC, sans-serif";
    ctx.textAlign = "left";
    ctx.textBaseline = "top";
    ctx.fillText("纵坐标 Y", 4, 6);
    ctx.textAlign = "center";
    ctx.textBaseline = "top";
    const titleX = Math.min(
      this.offsetX + mapW / 2,
      this.displayWidth - 40,
    );
    ctx.fillText("横坐标 X", titleX, this.offsetY + mapH + 16);

    ctx.restore();
  }

  _drawCellCoords(px, py, ts, x, y) {
    if (this.viewMode !== "grid" || ts < 16) return;
    const { ctx } = this;
    const fontSize = Math.max(8, Math.min(11, ts * 0.28));
    ctx.font = `${fontSize}px Microsoft YaHei, PingFang SC, sans-serif`;
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillStyle = "rgba(0, 0, 0, 0.62)";
    ctx.fillText(`${x},${y}`, px + ts / 2, py + ts / 2);
  }

  screenToTile(sx, sy) {
    const x = Math.floor((sx - this.offsetX) / (this.map.tileSize * this.scale));
    const y = Math.floor((sy - this.offsetY) / (this.map.tileSize * this.scale));
    if (x < 0 || y < 0 || x >= this.map.width || y >= this.map.height) return null;
    return this.map.tiles[y][x];
  }

  setHoveredTile(tile) {
    const ax = this.hoveredTile?.x;
    const ay = this.hoveredTile?.y;
    const bx = tile?.x;
    const by = tile?.y;
    if (ax === bx && ay === by) return;
    this.hoveredTile = tile;
    this.draw();
  }

  setSelectedTile(tile) {
    this.selectedTile = tile;
    this.draw();
  }

  pan(dx, dy) {
    this.offsetX += dx;
    this.offsetY += dy;
    this.draw();
  }

  zoom(delta, anchorX, anchorY) {
    const oldScale = this.scale;
    const factor = delta > 0 ? 1.12 : 0.89;
    this.scale = Math.min(Math.max(this.scale * factor, 0.35), 5);
    const wx = (anchorX - this.offsetX) / oldScale;
    const wy = (anchorY - this.offsetY) / oldScale;
    this.offsetX = anchorX - wx * this.scale;
    this.offsetY = anchorY - wy * this.scale;
    this.draw();
  }

  _terrainColor(tile, x, y) {
    const base = this.map.terrain[tile.terrain].color;
    if (this.terrainOnly) {
      const hash = ((x * 13 + y * 29) % 5) - 2;
      const r = parseInt(base.slice(1, 3), 16);
      const g = parseInt(base.slice(3, 5), 16);
      const b = parseInt(base.slice(5, 7), 16);
      const a = (c) => Math.max(0, Math.min(255, c + hash * 2));
      return `rgb(${a(r)},${a(g)},${a(b)})`;
    }
    return base;
  }

  _drawTile(px, py, ts, tile, x, y) {
    const { ctx } = this;

    if (this.viewMode === "jpg" && this.jpgImage && this.jpgBounds) {
      const { sx, sy, sw, sh } = this._jpgCellRect(x, y);
      ctx.drawImage(this.jpgImage, sx, sy, sw, sh, px, py, ts + 0.5, ts + 0.5);
      return;
    }

    if (this.texturesReady && !this.terrainOnly) {
      const img = TileAtlas.get(tile.terrain, x, y);
      if (img) {
        ctx.drawImage(img, px, py, ts + 0.5, ts + 0.5);
        return;
      }
    }

    ctx.fillStyle = this._terrainColor(tile, x, y);
    ctx.fillRect(px, py, ts + 0.5, ts + 0.5);

    if (tile.terrain === "river" && this.terrainOnly) {
      ctx.fillStyle = "rgba(200, 230, 255, 0.35)";
      ctx.fillRect(px + ts * 0.2, py + ts * 0.25, ts * 0.6, ts * 0.5);
    }
    if (tile.terrain === "mountain" && this.terrainOnly) {
      ctx.fillStyle = "rgba(255, 255, 255, 0.12)";
      ctx.fillRect(px + ts * 0.55, py + ts * 0.15, ts * 0.35, ts * 0.35);
    }
  }

  draw() {
    const { ctx, map } = this;
    const ts = map.tileSize * this.scale;
    const showGrid = this.viewMode === "grid" || this.scale >= 1.2;

    ctx.clearRect(0, 0, this.displayWidth, this.displayHeight);
    ctx.fillStyle = "#081018";
    ctx.fillRect(0, 0, this.displayWidth, this.displayHeight);

    ctx.save();
    ctx.translate(this.offsetX, this.offsetY);
    ctx.imageSmoothingEnabled = false;

    for (let y = 0; y < map.height; y++) {
      for (let x = 0; x < map.width; x++) {
        const px = x * ts;
        const py = y * ts;
        this._drawTile(px, py, ts, map.tiles[y][x], x, y);
        this._drawCellCoords(px, py, ts, x, y);
      }
    }

    if (showGrid) {
      ctx.strokeStyle = this.viewMode === "grid"
        ? "rgba(0,0,0,0.22)"
        : "rgba(0,0,0,0.1)";
      ctx.lineWidth = 0.5;
      for (let y = 0; y <= map.height; y++) {
        ctx.beginPath();
        ctx.moveTo(0, y * ts);
        ctx.lineTo(map.width * ts, y * ts);
        ctx.stroke();
      }
      for (let x = 0; x <= map.width; x++) {
        ctx.beginPath();
        ctx.moveTo(x * ts, 0);
        ctx.lineTo(x * ts, map.height * ts);
        ctx.stroke();
      }
    }

    for (const tile of [this.hoveredTile, this.selectedTile]) {
      if (!tile) continue;
      const px = tile.x * ts;
      const py = tile.y * ts;
      ctx.strokeStyle = tile === this.selectedTile ? "#ffd700" : "rgba(255,255,255,0.6)";
      ctx.lineWidth = tile === this.selectedTile ? 2 : 1;
      ctx.strokeRect(px + 0.5, py + 0.5, ts - 1, ts - 1);
    }

    ctx.restore();

    this._drawAxes(ts);
  }
}

function inBoundsCheck(x, y) {
  return x >= 0 && x < MAP_DATA.width && y >= 0 && y < MAP_DATA.height;
}
