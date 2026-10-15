/*
  ===== ゲーム一覧 =====
  書き方は tools.js と同じです。
  title / desc / page / url / image / color を書いて、並び順＝表示順です。

  note など外部サイトに飛ばしたいときは、page を書かずに url に記事のアドレスを入れ、
  external: "note" を足します（新しいタブで開き、タイル右上に「note ↗」が出ます）。
  例：
  {
    title: "死因特定ARG",
    desc: "……",
    url: "https://note.com/〇〇/n/〇〇",
    external: "note",
    image: "images/arg.jpg",
    color: "#2a2424",
  },
*/
const GAMES = [
  {
    title: "ローグライクサモンカードゲーム",
    desc: "グー・チョキ・パーの相性で戦う、ドット絵のローグライクカードバトル。階層を進みながらデッキを育てていきます。",
    title_en: "Roguelike Summon Card Game",
    desc_en: "A pixel-art roguelike card battler built on rock-paper-scissors matchups. Grow your deck as you descend floor by floor. (Japanese only)",
    page: "games/summon-card/",
    url: "https://caprame.com/DotRoguelikeCardBattle/",
    image: "images/summon-card.jpg",
    color: "#2e2a24",
  },
];
