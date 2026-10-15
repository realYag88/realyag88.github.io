/* ===== タイルを並べる仕組み（ふだんは触らなくてOK） =====
   tools.js や games.js のリストを受け取って、タイルを並べます */
function renderTiles(gridId, items) {
  const grid = document.getElementById(gridId);
  if (!grid) return;

  items.forEach(function (tool) {
    const tile = document.createElement(tool.url ? "a" : "div");
    tile.className = "tile";
    if (tool.url) tile.href = tool.url;
    if (tool.color) tile.style.setProperty("--tile-color", tool.color);

    if (tool.image) {
      const img = document.createElement("img");
      img.src = tool.image;
      img.alt = "";
      img.loading = "lazy";
      tile.appendChild(img);
    }

    const info = document.createElement("div");
    info.className = "tile-info";

    const title = document.createElement("span");
    title.className = "tile-title";
    title.textContent = tool.title;
    info.appendChild(title);

    const desc = document.createElement("span");
    desc.className = "tile-desc";
    desc.textContent = tool.desc;
    info.appendChild(desc);

    const go = document.createElement("span");
    go.className = "tile-go";
    go.textContent = tool.url ? "開く →" : "準備中";
    info.appendChild(go);

    tile.appendChild(info);
    grid.appendChild(tile);
  });

  // 最後の段が半端なときは、空きタイルで埋めて見た目をそろえる
  function fillLastRow() {
    grid.querySelectorAll(".tile-empty").forEach(function (el) { el.remove(); });
    const columns = getComputedStyle(grid).gridTemplateColumns.split(" ").length;
    const rest = items.length % columns;
    if (rest === 0) return;
    for (let i = 0; i < columns - rest; i++) {
      const empty = document.createElement("div");
      empty.className = "tile-empty";
      empty.setAttribute("aria-hidden", "true");
      grid.appendChild(empty);
    }
  }
  fillLastRow();
  window.addEventListener("resize", fillLastRow);
}
