/**
 * 地图浏览 + 地形编辑
 * 默认浏览；开启编辑后显示笔刷，左键涂抹，空格/中键拖平移
 */
(function () {
  const STORAGE_KEY = "simple_sango_terrain_edit_v1";
  const EDIT_FILENAME = "china-terrain-data.edit.js";

  const canvas = document.getElementById("mapCanvas");
  const mapWrapper = document.getElementById("mapWrapper");
  const tooltip = document.getElementById("tooltip");
  const infoPanel = document.getElementById("infoPanel");
  const btnEditMode = document.getElementById("btnEditMode");
  const btnSaveMap = document.getElementById("btnSaveMap");
  const btnResetOriginal = document.getElementById("btnResetOriginal");
  const editStatus = document.getElementById("editStatus");
  const paintLog = document.getElementById("paintLog");
  const palette = document.getElementById("terrainPalette");
  const btnGrid = document.getElementById("btnViewGrid");
  const btnJpg = document.getElementById("btnViewJpg");

  if (!canvas || typeof MapRenderer === "undefined" || typeof MAP_DATA === "undefined") {
    alert("地图脚本加载失败，请运行：python scripts/serve_map.py");
    return;
  }

  const renderer = new MapRenderer(canvas, MAP_DATA);

  let editMode = false;
  let brushTerrain = "desert";
  let dirty = false;
  let spaceHeld = false;
  let dragging = false;
  let painting = false;
  let lastX = 0;
  let lastY = 0;
  let lastPaintKey = "";

  function tName(id) {
    return MAP_DATA.terrain[id]?.name ?? id;
  }

  function logPaint(msg) {
    if (paintLog) paintLog.textContent = msg;
    if (editStatus) editStatus.textContent = msg;
  }

  function setDirty(v) {
    dirty = v;
    if (btnSaveMap) btnSaveMap.disabled = !v;
  }

  function setBrush(id) {
    if (!MAP_DATA.terrain[id] || id === "city") return;
    brushTerrain = id;
    palette?.querySelectorAll("[data-terrain]").forEach((el) => {
      el.classList.toggle("brush-active", el.dataset.terrain === id);
    });
    if (editMode) logPaint(`编辑中 · 笔刷「${tName(id)}」· 左键点地图`);
  }

  function setEditMode(on) {
    editMode = !!on;
    btnEditMode?.classList.toggle("active", editMode);
    mapWrapper?.classList.toggle("edit-mode", editMode);
    palette?.classList.toggle("hidden", !editMode);
    btnSaveMap?.classList.toggle("hidden", !editMode);
    btnResetOriginal?.classList.toggle("hidden", !editMode);
    editStatus?.classList.toggle("editing", editMode);
    if (editMode) {
      renderer.setViewMode("grid");
      btnGrid?.classList.add("active");
      btnJpg?.classList.remove("active");
      setBrush(brushTerrain);
    } else {
      painting = false;
      logPaint("浏览中 · 左键拖动平移");
    }
  }

  function canvasPos(e) {
    const r = canvas.getBoundingClientRect();
    return { x: e.clientX - r.left, y: e.clientY - r.top };
  }

  function tileAt(e) {
    const p = canvasPos(e);
    return renderer.screenToTile(p.x, p.y);
  }

  function showInfo(tile) {
    if (!tile) {
      infoPanel.innerHTML = `<h2>地块信息</h2><p class="hint">点击格子查看地形 · 左键拖动平移</p>`;
      return;
    }
    const [lon, lat] = gridToGeo(tile.x, tile.y);
    const t = MAP_DATA.terrain[tile.terrain];
    infoPanel.innerHTML = `
      <h2>地块信息</h2>
      <div class="info-row"><span>格子</span><span>(${tile.x}, ${tile.y})</span></div>
      <div class="info-row"><span>经纬度</span><span>${lon.toFixed(2)}°E ${lat.toFixed(2)}°N</span></div>
      <div class="info-row"><span>地形</span><span>${t.name}</span></div>
      <p class="hint">${editMode ? "左键可改此地块" : "点「编辑模式」后可修改"}</p>
    `;
  }

  function paint(e) {
    if (!editMode) {
      logPaint("请先打开「编辑模式」");
      return;
    }
    if (renderer.viewMode !== "grid") {
      renderer.setViewMode("grid");
      btnGrid?.classList.add("active");
      btnJpg?.classList.remove("active");
    }

    const tile = tileAt(e);
    if (!tile) {
      logPaint("未点中格子（点彩色地图区域）");
      return;
    }

    const key = `${tile.x},${tile.y}`;
    if (key === lastPaintKey) return;
    lastPaintKey = key;

    const before = tile.terrain;
    const ok = setTileTerrain(MAP_DATA, tile.x, tile.y, brushTerrain);
    if (ok) {
      setDirty(true);
      logPaint(`已改 (${tile.x},${tile.y}) ${tName(before)} → ${tName(brushTerrain)}`);
    } else {
      logPaint(`(${tile.x},${tile.y}) 已是「${tName(brushTerrain)}」，换个笔刷`);
    }
    renderer.setSelectedTile(tile);
    renderer.draw();
    showInfo(tile);
  }

  function onPointerDown(e) {
    canvas.setPointerCapture?.(e.pointerId);
    lastPaintKey = "";
    lastX = e.clientX;
    lastY = e.clientY;
    dragging = false;
    painting = false;

    const pan = spaceHeld || e.button === 1 || e.altKey || (!editMode && e.button === 0);
    if (pan) {
      dragging = true;
      mapWrapper?.classList.add("panning");
      return;
    }

    if (editMode && e.button === 0) {
      painting = true;
      paint(e);
    }
  }

  function onPointerMove(e) {
    if (painting) {
      paint(e);
      return;
    }
    if (dragging) {
      renderer.pan(e.clientX - lastX, e.clientY - lastY);
      lastX = e.clientX;
      lastY = e.clientY;
      return;
    }
    const tile = tileAt(e);
    renderer.setHoveredTile(tile);
    if (tile) {
      const [lon, lat] = gridToGeo(tile.x, tile.y);
      tooltip.classList.remove("hidden");
      tooltip.textContent = `${editMode ? `[${tName(brushTerrain)}] ` : ""}${tName(tile.terrain)} (${tile.x},${tile.y}) ${lon.toFixed(1)}°E`;
      const rect = mapWrapper.getBoundingClientRect();
      tooltip.style.left = `${e.clientX - rect.left + 12}px`;
      tooltip.style.top = `${e.clientY - rect.top + 12}px`;
    } else {
      tooltip.classList.add("hidden");
    }
  }

  function onPointerUp(e) {
    try { canvas.releasePointerCapture?.(e.pointerId); } catch { /* ignore */ }
    painting = false;
    dragging = false;
    lastPaintKey = "";
    mapWrapper?.classList.remove("panning");
  }

  function buildFile(rows) {
    return `/**
 * 可编辑地形数据（页面每次从本文件加载）
 * 文件：china-terrain-data.edit.js（项目根目录）
 * 栅格 ${MAP_DATA.width}×${MAP_DATA.height}
 * 字符: s=海 p=平原 h=丘陵 f=森林 m=山地 r=河 d=沙漠 w=沼泽 c=海岸
 */
const CHINA_TERRAIN_ROWS = ${JSON.stringify(rows)};

const CHINA_TERRAIN_DECODE = {
  s: "sea", p: "plain", h: "hill", f: "forest", m: "mountain",
  r: "river", d: "desert", w: "swamp", c: "coast",
};
`;
  }

  async function saveToEditFile(text) {
    const res = await fetch("/api/save-edit", {
      method: "POST",
      headers: { "Content-Type": "text/javascript; charset=utf-8" },
      body: text,
    });
    if (!res.ok) throw new Error(await res.text());
    return res.text();
  }

  async function save() {
    const rows = exportTerrainRows(MAP_DATA);
    const text = buildFile(rows);

    try {
      const msg = await saveToEditFile(text);
      setDirty(false);
      try { localStorage.removeItem(STORAGE_KEY); } catch { /* ignore */ }
      logPaint(`已写入 china-terrain-data.edit.js（${msg}）`);
      return;
    } catch (err) {
      console.warn("server save failed, fallback download", err);
    }

    if (window.showSaveFilePicker) {
      try {
        const handle = await window.showSaveFilePicker({
          suggestedName: EDIT_FILENAME,
          types: [{ description: "JS", accept: { "text/javascript": [".js"] } }],
        });
        const w = await handle.createWritable();
        await w.write(text);
        await w.close();
        setDirty(false);
        logPaint("已保存到所选文件（请确保是根目录 china-terrain-data.edit.js）");
        return;
      } catch (err) {
        if (err?.name === "AbortError") return;
      }
    }

    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([text], { type: "text/javascript" }));
    a.download = EDIT_FILENAME;
    a.click();
    setDirty(false);
    logPaint(`已下载 ${EDIT_FILENAME}，请放到项目根目录后刷新`);
  }

  async function resetOriginal() {
    if (typeof CHINA_TERRAIN_ROWS_ORIGINAL === "undefined") {
      alert("缺少 china-terrain-data.original.js");
      return;
    }
    if (dirty && !confirm("恢复原始地形并写回 edit.js？未保存修改会丢失")) return;
    applyTerrainRows(MAP_DATA, CHINA_TERRAIN_ROWS_ORIGINAL);
    renderer.draw();
    setDirty(true);
    await save();
    logPaint("已用原始数据覆盖 china-terrain-data.edit.js");
  }

  // —— 绑定 ——
  canvas.style.touchAction = "none";
  canvas.addEventListener("pointerdown", onPointerDown);
  canvas.addEventListener("pointermove", onPointerMove);
  canvas.addEventListener("pointerup", onPointerUp);
  canvas.addEventListener("pointercancel", onPointerUp);
  canvas.addEventListener("contextmenu", (e) => e.preventDefault());
  canvas.addEventListener("wheel", (e) => {
    e.preventDefault();
    const p = canvasPos(e);
    renderer.zoom(-e.deltaY, p.x, p.y);
  }, { passive: false });
  canvas.addEventListener("dblclick", () => {
    renderer._fitToView();
    renderer.draw();
  });

  window.addEventListener("keydown", (e) => {
    if (e.code === "Space") {
      spaceHeld = true;
      e.preventDefault();
    }
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "s") {
      e.preventDefault();
      if (dirty) save();
    }
  });
  window.addEventListener("keyup", (e) => {
    if (e.code === "Space") spaceHeld = false;
  });

  btnEditMode?.addEventListener("click", () => setEditMode(!editMode));
  btnSaveMap?.addEventListener("click", () => save());
  btnResetOriginal?.addEventListener("click", () => resetOriginal());

  palette?.querySelectorAll("[data-terrain]").forEach((el) => {
    el.addEventListener("click", () => setBrush(el.dataset.terrain));
  });

  btnGrid?.addEventListener("click", () => {
    renderer.setViewMode("grid");
    btnGrid.classList.add("active");
    btnJpg?.classList.remove("active");
  });
  btnJpg?.addEventListener("click", () => {
    setEditMode(false);
    renderer.setViewMode("jpg");
    btnJpg.classList.add("active");
    btnGrid?.classList.remove("active");
  });

  setEditMode(false);
  renderer.draw();
  showInfo(null);
  logPaint(`已从 china-terrain-data.edit.js 加载 ${MAP_DATA.width}×${MAP_DATA.height}`);

  if (typeof JPG_SOURCE !== "undefined" && typeof JPG_MAP_BOUNDS !== "undefined") {
    const img = new Image();
    img.onload = () => renderer.setJpgSource(img, JPG_MAP_BOUNDS);
    img.onerror = () => btnJpg?.setAttribute("disabled", "true");
    img.src = JPG_SOURCE;
  }
})();
