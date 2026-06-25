/**
 * 纯地形地图交互
 */
(function () {
  const canvas = document.getElementById("mapCanvas");
  const tooltip = document.getElementById("tooltip");
  const infoPanel = document.getElementById("infoPanel");
  const loadingEl = document.getElementById("loadingOverlay");
  let renderer;

  let isDragging = false;
  let didDrag = false;
  let lastX = 0;
  let lastY = 0;

  function terrainName(id) {
    return MAP_DATA.terrain[id]?.name ?? id;
  }

  function terrainDesc(id) {
    return MAP_DATA.terrain[id]?.desc ?? "";
  }

  function updateTooltip(tile, clientX, clientY) {
    if (!tile) {
      tooltip.classList.add("hidden");
      return;
    }
    const [lon, lat] = gridToGeo(tile.x, tile.y);
    tooltip.textContent = `${terrainName(tile.terrain)} · ${lon.toFixed(1)}°E ${lat.toFixed(1)}°N`;
    tooltip.classList.remove("hidden");
    const rect = canvas.parentElement.getBoundingClientRect();
    tooltip.style.left = `${clientX - rect.left + 12}px`;
    tooltip.style.top = `${clientY - rect.top + 12}px`;
  }

  function updateInfoPanel(tile) {
    if (!tile) {
      infoPanel.innerHTML = `<h2>地块信息</h2><p class="hint">点击格子查看地形</p>`;
      return;
    }
    const [lon, lat] = gridToGeo(tile.x, tile.y);
    const t = MAP_DATA.terrain[tile.terrain];
    infoPanel.innerHTML = `
      <h2>地块信息</h2>
      <div class="info-row"><span>格子</span><span>(${tile.x}, ${tile.y})</span></div>
      <div class="info-row"><span>经度</span><span>${lon.toFixed(2)}°E</span></div>
      <div class="info-row"><span>纬度</span><span>${lat.toFixed(2)}°N</span></div>
      <div class="info-row"><span>地形</span><span>${t.name}</span></div>
      <div class="info-row"><span>通行</span><span>${t.moveCost >= 99 ? "不可" : "消耗 " + t.moveCost}</span></div>
      <p class="terrain-desc">${t.desc || ""}</p>
    `;
  }

  function bindEvents() {
    canvas.addEventListener("mousedown", (e) => {
      isDragging = true;
      didDrag = false;
      lastX = e.clientX;
      lastY = e.clientY;
    });
    window.addEventListener("mouseup", () => { isDragging = false; });

    canvas.addEventListener("mousemove", (e) => {
      const rect = canvas.getBoundingClientRect();
      if (isDragging) {
        const dx = e.clientX - lastX;
        const dy = e.clientY - lastY;
        if (Math.abs(dx) > 3 || Math.abs(dy) > 3) didDrag = true;
        renderer.pan(dx, dy);
        lastX = e.clientX;
        lastY = e.clientY;
        return;
      }
      const tile = renderer.screenToTile(e.clientX - rect.left, e.clientY - rect.top);
      renderer.setHoveredTile(tile);
      updateTooltip(tile, e.clientX, e.clientY);
    });

    canvas.addEventListener("mouseleave", () => {
      renderer.setHoveredTile(null);
      tooltip.classList.add("hidden");
    });

    canvas.addEventListener("click", (e) => {
      if (didDrag) return;
      const rect = canvas.getBoundingClientRect();
      const tile = renderer.screenToTile(e.clientX - rect.left, e.clientY - rect.top);
      renderer.setSelectedTile(tile);
      updateInfoPanel(tile);
    });

    canvas.addEventListener("wheel", (e) => {
      e.preventDefault();
      const rect = canvas.getBoundingClientRect();
      renderer.zoom(-e.deltaY, e.clientX - rect.left, e.clientY - rect.top);
    }, { passive: false });

    canvas.addEventListener("dblclick", () => {
      renderer._fitToView();
      renderer.draw();
    });
  }

  renderer = new MapRenderer(canvas, MAP_DATA);
  bindEvents();

  const btnGrid = document.getElementById("btnViewGrid");
  const btnJpg = document.getElementById("btnViewJpg");

  function setViewButtons(mode) {
    btnGrid?.classList.toggle("active", mode === "grid");
    btnJpg?.classList.toggle("active", mode === "jpg");
  }

  btnGrid?.addEventListener("click", () => {
    renderer.setViewMode("grid");
    setViewButtons("grid");
  });

  btnJpg?.addEventListener("click", () => {
    renderer.setViewMode("jpg");
    setViewButtons("jpg");
  });

  // 预加载 JPG 供「原图对照」切换，默认显示识别后的方格地形
  if (typeof JPG_SOURCE !== "undefined" && typeof JPG_MAP_BOUNDS !== "undefined") {
    const jpgImg = new Image();
    jpgImg.onload = () => {
      renderer.setJpgSource(jpgImg, JPG_MAP_BOUNDS);
      if (loadingEl) loadingEl.classList.add("hidden");
    };
    jpgImg.onerror = () => {
      btnJpg?.setAttribute("disabled", "true");
      if (loadingEl) loadingEl.classList.add("hidden");
    };
    jpgImg.src = JPG_SOURCE;
  } else if (loadingEl) {
    loadingEl.classList.add("hidden");
  }
})();
