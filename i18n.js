/*
  ===== 日本語／英語の切り替え =====
  ・最初に開いたときは、ブラウザの言語が日本語なら日本語、それ以外なら英語で表示
  ・右上の JA / EN ボタンで切り替えると、その選択を覚えておく
  ・HTMLの要素に data-en="英語の文" を付けると、英語表示のときにその文に入れ替わる
  ・まとまった文章は data-lang-block="ja" / "en" を付けたブロックを2つ用意する
*/
(function () {
  var KEY = "caprame-lang";
  var root = document.documentElement;

  function detect() {
    try {
      var saved = localStorage.getItem(KEY);
      if (saved === "ja" || saved === "en") return saved;
    } catch (e) {}
    var list = navigator.languages && navigator.languages.length ? navigator.languages : [navigator.language || "ja"];
    return /^ja\b/i.test(list[0] || "") ? "ja" : "en";
  }

  // 本文が日本語だけのページ（Notes の記事）は、英語表示でも lang="ja" のままにして
  // ブラウザの翻訳機能が「日本語のページ」として翻訳を提案できるようにする
  var contentLang = root.getAttribute("data-content-lang");

  function apply(lang) {
    root.setAttribute("data-lang", lang);
    root.lang = contentLang || lang;
    document.querySelectorAll("[data-en]").forEach(function (el) {
      if (!el.hasAttribute("data-ja")) el.setAttribute("data-ja", el.textContent);
      el.textContent = lang === "en" ? el.getAttribute("data-en") : el.getAttribute("data-ja");
    });
    document.querySelectorAll(".lang-toggle button").forEach(function (b) {
      b.setAttribute("aria-pressed", String(b.getAttribute("data-set-lang") === lang));
    });
    document.dispatchEvent(new CustomEvent("caprame:langchange", { detail: lang }));
  }

  window.caprameLang = function () {
    return root.getAttribute("data-lang") === "en" ? "en" : "ja";
  };

  var initial = detect();
  root.setAttribute("data-lang", initial);
  root.lang = contentLang || initial;

  document.addEventListener("DOMContentLoaded", function () {
    apply(initial);
    document.querySelectorAll(".lang-toggle button").forEach(function (b) {
      b.addEventListener("click", function () {
        var lang = b.getAttribute("data-set-lang");
        try { localStorage.setItem(KEY, lang); } catch (e) {}
        apply(lang);
      });
    });
  });
})();
