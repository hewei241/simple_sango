/**
 * 地形贴图加载器
 */
const TileAtlas = {
  images: {},
  ready: false,

  variantIndex(x, y) {
    return Math.abs((x * 17 + y * 31) % MAP_DATA.textureVariants);
  },

  loadAll() {
    const tasks = [];
    for (const [id, terrain] of Object.entries(MAP_DATA.terrain)) {
      if (!terrain.texture) continue;
      for (let v = 0; v < MAP_DATA.textureVariants; v++) {
        const key = `${id}_${v}`;
        const src = `${terrain.texture}_${v}.png`;
        tasks.push(this._loadImage(key, src));
      }
    }
    return Promise.all(tasks).then(() => {
      this.ready = true;
    });
  },

  _loadImage(key, src) {
    return new Promise((resolve, reject) => {
      const img = new Image();
      img.onload = () => {
        this.images[key] = img;
        resolve();
      };
      img.onerror = () => reject(new Error(`贴图加载失败: ${src}`));
      img.src = src;
    });
  },

  get(terrainId, x, y) {
    const v = this.variantIndex(x, y);
    return this.images[`${terrainId}_${v}`] || this.images[`${terrainId}_0`];
  },
};
