/*
  ===== ツール一覧 =====
  ツールを追加・編集するときは、このリストだけ書き換えればOKです。

  title : タイルに出る名前
  desc  : カーソルを乗せたときに出る説明（1〜2文）
  url   : ツールのアドレス（https://caprame.com/リポジトリ名/）。
          空 "" のままだとタイルは押せない状態で表示されます
  image : スクショ画像のパス（images フォルダに入れる）。
          空 "" のままだと color の色だけのタイルになります
  color : 画像がないとき・読み込み中の背景色

  並び順＝表示順です。
*/
const TOOLS = [
  {
    title: "Film study viewer",
    desc: "参考画像を一定時間ごとに切り替える、クロッキー練習用のスライドショー。分割線も重ねられます。",
    url: "https://caprame.com/FilmStudyViewer/",
    image: "",
    color: "#2a2e38",
  },
  {
    title: "ストレッチループ",
    desc: "ストレッチの秒数をくり返し計る、ループ式のタイマー。",
    url: "", // ← リポジトリ名がわかったら入れる
    image: "",
    color: "#24302e",
  },
  {
    title: "ベース練習帳",
    desc: "課題曲、YouTubeの区間ループ、基礎練、メトロノームをまとめたベース練習用アプリ。",
    url: "", // ← リポジトリ名がわかったら入れる
    image: "",
    color: "#332828",
  },
  {
    title: "筋トレログ",
    desc: "部位別のメニューとセットを記録できる筋トレ記録アプリ。体重やカレンダーも。",
    url: "", // ← リポジトリ名がわかったら入れる
    image: "",
    color: "#2a2833",
  },
];

/* ===== ここから下は表示の仕組み（ふだんは触らなくてOK） ===== */
(function () {
  const grid = document.getElementById("tool-grid");
  if (!grid) return;

  TOOLS.forEach(function (tool) {
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
    const rest = TOOLS.length % columns;
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
})();
