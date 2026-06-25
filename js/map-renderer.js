/**
 * 地图渲染器 — 贴图地形 + 城池标注
 */
class MapRenderer {
  constructor(canvas, mapData) {
    this.canvas = canvas;
    this.ctx = canvas.getContext("2d");
    this.map = mapData;
    this.scale = 1;
    this.offsetX = 0;
    this.offsetY = 0;
    this.hoveredTile = null;
    this.selectedTile = null;
    this.cityPositions = [];
    this.texturesReady = false;

    this._buildCityPositions();
    this._resize();
    window.addEventListener("resize", () => this._resize());
  }

  setTexturesReady(ready) {
    this.texturesReady = ready;
    this.draw();
  }

  _buildCityPositions() {
    this.cityPositions = [];
    for (let y = 0; y < this.map.height; y++) {
      for (let x = 0; x < this.map.width; x++) {
        const tile = this.map.tiles[y][x];
        if (tile.city) {
          this.cityPositions.push({ tile, city: this.map.cities[tile.city] });
        }
      }
    }
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
    const scaleX = (this.displayWidth - 32) / mapW;
    const scaleY = (this.displayHeight - 32) / mapH;
    this.scale = Math.min(scaleX, scaleY, 2.5);
    this.offsetX = (this.displayWidth - mapW * this.scale) / 2;
    this.offsetY = (this.displayHeight - mapH * this.scale) / 2;
  }

  screenToTile(sx, sy) {
    const x = Math.floor((sx - this.offsetX) / (this.map.tileSize * this.scale));
    const y = Math.floor((sy - this.offsetY) / (this.map.tileSize * this.scale));
    if (x < 0 || y < 0 || x >= this.map.width || y >= this.map.height) return null;
    return this.map.tiles[y][x];
  }

  setHoveredTile(tile) {
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
    const hash = ((x * 17 + y * 31) % 7) - 3;
    const r = parseInt(base.slice(1, 3), 16);
    const g = parseInt(base.slice(3, 5), 16);
    const b = parseInt(base.slice(5, 7), 16);
    const adjust = (c) => Math.max(0, Math.min(255, c + hash * 3));
    return `rgb(${adjust(r)},${adjust(g)},${adjust(b)})`;
  }

  _drawTile(px, py, ts, tile, x, y) {
    const { ctx } = this;

    if (this.texturesReady) {
      const img = TileAtlas.get(tile.terrain, x, y);
      if (img) {
        ctx.drawImage(img, px, py, ts + 0.5, ts + 0.5);
      } else {
        ctx.fillStyle = this._terrainColor(tile, x, y);
        ctx.fillRect(px, py, ts + 0.5, ts + 0.5);
      }
    } else {
      ctx.fillStyle = this._terrainColor(tile, x, y);
      ctx.fillRect(px, py, ts + 0.5, ts + 0.5);
    }

    // 势力淡染（水域不加）
    if (!["sea", "river"].includes(tile.terrain)) {
      const fac = this.map.faction[tile.faction];
      if (fac) {
        ctx.fillStyle = fac.color;
        ctx.fillRect(px, py, ts, ts);
      }
    }
  }

  draw() {
    const { ctx, map } = this;
    const ts = map.tileSize * this.scale;
    const showGrid = this.scale >= 1.2;

    ctx.clearRect(0, 0, this.displayWidth, this.displayHeight);
    ctx.fillStyle = "#0e1520";
    ctx.fillRect(0, 0, this.displayWidth, this.displayHeight);

    ctx.save();
    ctx.translate(this.offsetX, this.offsetY);
    ctx.imageSmoothingEnabled = this.scale < 2;

    for (let y = 0; y < map.height; y++) {
      for (let x = 0; x < map.width; x++) {
        const tile = map.tiles[y][x];
        this._drawTile(x * ts, y * ts, ts, tile, x, y);
      }
    }

    if (showGrid) {
      ctx.strokeStyle = "rgba(0,0,0,0.12)";
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

    if (this.scale >= 0.7) {
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      const fontSize = Math.max(10, Math.min(16, ts * 0.55));
      ctx.font = `${fontSize}px "Microsoft YaHei", serif`;
      for (const label of map.provinceLabels) {
        const px = label.x * ts + ts / 2;
        const py = label.y * ts + ts / 2;
        ctx.fillStyle = "rgba(0,0,0,0.4)";
        ctx.fillText(label.name, px + 1, py + 1);
        ctx.fillStyle = "rgba(230, 210, 170, 0.6)";
        ctx.fillText(label.name, px, py);
      }
    }

    for (const tile of [this.hoveredTile, this.selectedTile]) {
      if (!tile) continue;
      const px = tile.x * ts;
      const py = tile.y * ts;
      ctx.strokeStyle = tile === this.selectedTile ? "#ffd700" : "rgba(255,255,255,0.75)";
      ctx.lineWidth = tile === this.selectedTile ? 2.5 : 1.5;
      ctx.strokeRect(px + 0.5, py + 0.5, ts - 1, ts - 1);
    }

    for (const { tile, city } of this.cityPositions) {
      const px = tile.x * ts + ts / 2;
      const py = tile.y * ts + ts / 2;
      const r = Math.max(4, ts * 0.22);
      const facColor = { wei: "#4a7ab8", shu: "#5a9048", wu: "#b84848", neutral: "#888880" };

      ctx.beginPath();
      ctx.arc(px, py, r + 2, 0, Math.PI * 2);
      ctx.fillStyle = "rgba(0,0,0,0.55)";
      ctx.fill();
      ctx.beginPath();
      ctx.arc(px, py, r, 0, Math.PI * 2);
      ctx.fillStyle = facColor[tile.faction] || "#888";
      ctx.fill();
      ctx.strokeStyle = "#f5e6b8";
      ctx.lineWidth = 1.5;
      ctx.stroke();

      if (this.scale >= 0.5) {
        const nameSize = Math.max(10, Math.min(14, ts * 0.42));
        ctx.font = `bold ${nameSize}px "Microsoft YaHei", sans-serif`;
        ctx.textAlign = "center";
        ctx.textBaseline = "bottom";
        const labelY = py - r - 3;
        ctx.fillStyle = "rgba(0,0,0,0.75)";
        ctx.fillText(city.name, px + 1, labelY + 1);
        ctx.fillStyle = "#fff8e8";
        ctx.fillText(city.name, px, labelY);
      }
    }

    ctx.restore();
  }
}

function inBoundsCheck(x, y) {
  return x >= 0 && x < MAP_DATA.width && y >= 0 && y < MAP_DATA.height;
}
