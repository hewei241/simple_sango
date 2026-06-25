/**
 * 地图交互入口
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

  function factionName(id) {
    return MAP_DATA.faction[id]?.name ?? id;
  }

  function updateTooltip(tile, clientX, clientY) {
    if (!tile) {
      tooltip.classList.add("hidden");
      return;
    }

    const rect = canvas.parentElement.getBoundingClientRect();
    let text = `(${tile.x}, ${tile.y}) ${terrainName(tile.terrain)}`;
    if (tile.region) text += ` · ${tile.region}`;
    if (tile.city) text += ` · ${MAP_DATA.cities[tile.city].name}`;

    tooltip.textContent = text;
    tooltip.classList.remove("hidden");
    tooltip.style.left = `${clientX - rect.left + 12}px`;
    tooltip.style.top = `${clientY - rect.top + 12}px`;
  }

  function updateInfoPanel(tile) {
    if (!tile) {
      infoPanel.innerHTML = `
        <h2>地块信息</h2>
        <p class="hint">点击格子查看详情</p>
      `;
      return;
    }

    const rows = [
      ["坐标", `(${tile.x}, ${tile.y})`],
      ["地形", terrainName(tile.terrain)],
      ["州郡", tile.region || "—"],
      ["势力", factionName(tile.faction)],
      ["移动消耗", String(MAP_DATA.terrain[tile.terrain]?.moveCost ?? "—")],
    ];

    let html = `<h2>地块信息</h2>`;
    for (const [label, value] of rows) {
      html += `<div class="info-row"><span>${label}</span><span>${value}</span></div>`;
    }

    const desc = terrainDesc(tile.terrain);
    if (desc) {
      html += `<p class="terrain-desc">${desc}</p>`;
    }

    if (tile.city) {
      const city = MAP_DATA.cities[tile.city];
      html += `
        <div class="info-city">
          <h3>${city.name}</h3>
          <p>${city.desc}</p>
        </div>
      `;
    }

    infoPanel.innerHTML = html;
  }

  function bindEvents() {
    canvas.addEventListener("mousedown", (e) => {
      isDragging = true;
      didDrag = false;
      lastX = e.clientX;
      lastY = e.clientY;
    });

    window.addEventListener("mouseup", () => {
      isDragging = false;
    });

    canvas.addEventListener("mousemove", (e) => {
      const rect = canvas.getBoundingClientRect();
      const sx = e.clientX - rect.left;
      const sy = e.clientY - rect.top;

      if (isDragging) {
        const dx = e.clientX - lastX;
        const dy = e.clientY - lastY;
        if (Math.abs(dx) > 3 || Math.abs(dy) > 3) didDrag = true;
        renderer.pan(dx, dy);
        lastX = e.clientX;
        lastY = e.clientY;
        return;
      }

      const tile = renderer.screenToTile(sx, sy);
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

  TileAtlas.loadAll()
    .then(() => {
      renderer = new MapRenderer(canvas, MAP_DATA);
      renderer.setTexturesReady(true);
      bindEvents();
      if (loadingEl) loadingEl.classList.add("hidden");
    })
    .catch((err) => {
      console.warn(err);
      renderer = new MapRenderer(canvas, MAP_DATA);
      bindEvents();
      if (loadingEl) loadingEl.classList.add("hidden");
    });
})();
