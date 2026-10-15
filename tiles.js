/* ===== タイルを並べる仕組み（ふだんは触らなくてOK） =====
   tools.js や games.js のリストを受け取って、タイルを並べます */
function renderTiles(gridId, items) {
  const grid = document.getElementById(gridId);
  if (!grid) return;

  function lang() {
    return window.caprameLang ? window.caprameLang() : "ja";
  }
  // 英語表示のときは title_en / desc_en を使う（なければ日本語のまま）
  function pick(item, key) {
    return lang() === "en" && item[key + "_en"] ? item[key + "_en"] : item[key];
  }

  function draw() {
  grid.textContent = "";
  items.forEach(function (tool) {
    // page（説明ページ）があればそちらへ。なければ url へ直接
    const href = tool.page || tool.url;
    const tile = document.createElement(href ? "a" : "div");
    tile.className = "tile";
    if (href) tile.href = href;
    // note など外部サイトへのリンクは新しいタブで開き、右上に目印を出す
    if (tool.external) {
      tile.target = "_blank";
      tile.rel = "noopener";
      const badge = document.createElement("span");
      badge.className = "tile-badge";
      badge.textContent = tool.external + " ↗";
      tile.appendChild(badge);
    }
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
    title.textContent = pick(tool, "title");
    info.appendChild(title);

    const desc = document.createElement("span");
    desc.className = "tile-desc";
    desc.textContent = pick(tool, "desc");
    info.appendChild(desc);

    const go = document.createElement("span");
    go.className = "tile-go";
    const en = lang() === "en";
    if (!href) go.textContent = en ? "Coming soon" : "準備中";
    else if (tool.external) go.textContent = en ? "Read on " + tool.external + " ↗" : tool.external + " で読む ↗";
    else if (tool.page) go.textContent = en ? "Details →" : "詳しく見る →";
    else go.textContent = en ? "Open →" : "開く →";
    info.appendChild(go);

    tile.appendChild(info);
    grid.appendChild(tile);
  });
  fillLastRow();
  }

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
  draw();
  window.addEventListener("resize", fillLastRow);
  document.addEventListener("caprame:langchange", draw);
}
