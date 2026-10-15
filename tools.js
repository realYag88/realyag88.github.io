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
    desc: "参考画像を一定時間ごとに切り替えるクロッキー練習用のスライドショー。分割線を表示できる。",
    url: "https://caprame.com/FilmStudyViewer/",
    image: "images/film-study-viewer.jpg",
    color: "#2a2e38",
  },
  {
    title: "ストレッチループ",
    desc: "ストレッチの秒数をくり返し計るループ式のタイマー。",
    url: "https://caprame.com/stretch-loop/",
    image: "images/stretch-loop.jpg",
    color: "#24302e",
  },
  {
    title: "ベース練習帳",
    desc: "課題曲、YouTubeの区間ループ、基礎練、メトロノームをまとめたベース練習用webアプリ",
    url: "https://caprame.com/bass-practice/",
    image: "images/bass-practice.jpg",
    color: "#332828",
  },
  {
    title: "筋トレログ",
    desc: "部位別のメニューとセットを記録できる筋トレ記録アプリ。体重やカレンダーも搭載。",
    url: "https://caprame.com/kintore-log/",
    image: "images/kintore-log.jpg",
    color: "#2a2833",
  },
];
