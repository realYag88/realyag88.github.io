"""
content.json から、タイル一覧(tools.js / games.js)と説明ページ(tools/〇〇/・games/〇〇/)を作り直します。

  python3 _build/build.py

・文面を変えるときは content.json だけを書き換えて、このスクリプトを実行します
・英語(en)の項目が空のときは、日本語の文面をそのまま使います
・external(note など)を付けた項目は説明ページを作らず、タイルから直接そのURLへ飛びます
・Notes(ブログ)の記事は _notes フォルダに置きます。書き方は _build/notes.py の先頭を見てください
・_build・_notes フォルダはサイトとしては公開されません(GitHub Pages は _ で始まるフォルダを無視します)
・Markdown の変換に python の markdown、画像の撮影情報を消すのに Pillow を使います
  (入っていなければ pip install markdown pillow)
"""
import html
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIELDS_TEXT = ["title", "tile", "lead", "env", "data", "note", "language", "howto_label"]
FIELDS_LIST = ["when", "howto", "features"]

X_ICON = ('<svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path fill="currentColor" '
          'd="M18.901 1.153h3.68l-8.04 9.19L24 22.846h-7.406l-5.8-7.584-6.638 7.584H.474l8.6-9.83L0 1.154h7.594'
          'l5.243 6.932ZM17.61 20.644h2.039L6.486 3.24H4.298Z"/></svg>')


def esc(s):
    return html.escape(s or "", quote=True)


def esc_br(s):
    """本文用。文中の改行はそのまま改行として表示する"""
    return "<br>".join(esc(line) for line in (s or "").split("\n"))


def one_line(s):
    """meta description などは改行をつなげて1行に"""
    return " ".join(x.strip() for x in (s or "").split("\n") if x.strip())


def lang_pair(item, key):
    """(日本語, 英語)。英語が空なら日本語で埋める"""
    ja = item["ja"].get(key)
    en = item.get("en", {}).get(key)
    if key in FIELDS_LIST:
        ja = [x for x in (ja or []) if x.strip()]
        en = [x for x in (en or []) if x.strip()]
        if len(en) != len(ja):
            en = ja if not en else en
        return ja, en
    ja = (ja or "").strip()
    en = (en or "").strip() or ja
    return ja, en


# ---------------- タイル一覧 ----------------
TILE_HEADER = {
    "tools": "ツール一覧",
    "games": "ゲーム一覧",
}


def build_tiles(section, items):
    rows = []
    for it in items:
        t_ja, t_en = lang_pair(it, "title")
        d_ja, d_en = lang_pair(it, "tile")
        row = {"title": t_ja, "desc": d_ja, "title_en": t_en, "desc_en": d_en}
        if it.get("external"):
            row["url"] = it.get("url", "")
            row["external"] = it["external"]
        else:
            row["page"] = f"{section}/{it['slug']}/"
            row["url"] = it.get("url", "")
        row["image"] = f"images/{it['image']}" if it.get("image") else ""
        row["color"] = it.get("color", "")
        rows.append(row)
    var = "TOOLS" if section == "tools" else "GAMES"
    body = json.dumps(rows, ensure_ascii=False, indent=2)
    text = (f"/*\n  ===== {TILE_HEADER[section]} =====\n"
            f"  このファイルは content.json から自動で作られます。直接書き換えず、\n"
            f"  content.json を直して python3 _build/build.py を実行してください。\n*/\n"
            f"const {var} = {body};\n")
    with open(os.path.join(ROOT, f"{section}.js"), "w", encoding="utf-8") as f:
        f.write(text)


# ---------------- 説明ページ ----------------
def li(items):
    return "\n".join(f"        <li>{esc_br(i)}</li>" for i in items)


def section_html(title_ja, title_en, items_ja, items_en, ordered=False):
    if not items_ja:
        return ""
    tag = "ol" if ordered else "ul"
    return f"""
    <section class="detail-section">
      <h2 data-en="{esc(title_en)}">{esc(title_ja)}</h2>
      <{tag} data-lang-block="ja">
{li(items_ja)}
      </{tag}>
      <{tag} data-lang-block="en">
{li(items_en)}
      </{tag}>
    </section>"""


# ---------------- 共通ヘッダー ----------------
TABS = [("tools", "/", "Tools"), ("games", "/games.html", "Games"),
        ("notes", "/notes.html", "Notes"), ("about", "/about.html", "About")]


def header_html(current, page_is_list=False):
    """current: いま開いているタブ。一覧ページなら aria-current="page"、その下のページなら "true" """
    mark = "page" if page_is_list else "true"
    rows = []
    for key, href, label in TABS:
        cur = f' aria-current="{mark}"' if key == current else ""
        rows.append(f'        <a class="tab" href="{href}"{cur}>{label}</a>')
    tabs = "\n".join(rows)
    return f"""  <header class="wrap site-header">
    <a class="brand" href="/">
      <img class="brand-eye" src="/logo.svg" alt="">
      <span class="brand-text">
        <span class="brand-name">カプラメー</span>
        <span class="brand-sub">CAPRAME</span>
      </span>
    </a>
    <div class="header-right">
      <nav class="tabs" aria-label="カテゴリ">
{tabs}
      </nav>
      <div class="lang-toggle" role="group" aria-label="Language">
        <button type="button" data-set-lang="ja" aria-pressed="true">JA</button>
        <button type="button" data-set-lang="en" aria-pressed="false">EN</button>
      </div>
      <a class="icon-link" href="https://x.com/_caprame_" rel="me noopener" target="_blank" aria-label="X（@_caprame_）">
        {X_ICON}
      </a>
    </div>
  </header>
"""


FOOTER = """  <footer class="wrap site-footer">
    <span class="footer-links">
      <a href="/privacy.html" data-en="Privacy Policy">プライバシーポリシー</a>
    </span>
    <span>© 2026 caprame. All rights reserved.</span>
  </footer>
  <!-- Cloudflare Web Analytics --><script type='module' src='https://static.cloudflareinsights.com/beacon.min.js' data-cf-beacon='{"token": "991d75fb98894c599ec91ff6296ff0bf"}'></script><!-- End Cloudflare Web Analytics -->
"""


def page_html(section, it):
    is_tools = section == "tools"
    sec_label = "Tools" if is_tools else "Games"
    list_href = "/" if is_tools else "/games.html"
    url = f"https://caprame.com/{section}/{it['slug']}/"

    title, title_en = lang_pair(it, "title")
    lead, lead_en = lang_pair(it, "lead")
    note, note_en = lang_pair(it, "note")
    when, when_en = lang_pair(it, "when")
    howto, howto_en = lang_pair(it, "howto")
    feats, feats_en = lang_pair(it, "features")
    hl, hl_en = lang_pair(it, "howto_label")
    if not hl:
        hl, hl_en = "使い方", "How to use"

    btns = []
    for b in it.get("buttons", []):
        ja, en = b.get("ja", ""), b.get("en") or b.get("ja", "")
        if b.get("kind") == "download":
            btns.append(f'      <a class="btn btn-secondary" href="{esc(b["href"])}" data-en="{esc(en)}">{esc(ja)}</a>')
        else:
            btns.append(f'      <a class="btn btn-primary" href="{esc(b["href"])}" data-en="{esc(en)} →">{esc(ja)} →</a>')

    after = ""
    if note:
        after = f"""
    <p class="detail-note" data-lang-block="ja">{esc_br(note)}</p>
    <p class="detail-note" data-lang-block="en">{esc_br(note_en)}</p>"""

    spec_rows = []
    for key, kja, ken in (("env", "対応環境", "Works on"), ("language", "言語", "Language"),
                          ("data", "データの保存", "Your data")):
        vja, ven = lang_pair(it, key)
        if vja:
            spec_rows.append(
                f'        <dt data-en="{ken}">{kja}</dt>\n'
                f'        <dd><span data-lang-block="ja">{esc_br(vja)}</span>'
                f'<span data-lang-block="en">{esc_br(ven)}</span></dd>')
    spec = ""
    if spec_rows:
        spec = ('\n    <section class="detail-section">\n      <dl class="detail-spec">\n'
                + "\n".join(spec_rows) + "\n      </dl>\n    </section>")

    image = it.get("image", "")
    shot = og = ""
    if image:
        shot = f"""
    <div class="detail-shot" style="--tile-color:{esc(it.get('color', ''))}">
      <img src="/images/{esc(image)}" alt="" width="1280" height="800">
    </div>
"""
        og = f'\n  <meta property="og:image" content="https://caprame.com/images/{esc(image)}">'

    return f"""<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title data-en="{esc(title_en)} | caprame">{esc(title)} | カプラメー</title>
  <meta name="description" content="{esc(one_line(lead))}">
  <meta name="theme-color" content="#1b1a1f">
  <link rel="canonical" href="{url}">
  <meta property="og:title" content="{esc(title)} | カプラメー">
  <meta property="og:description" content="{esc(one_line(lead))}">
  <meta property="og:url" content="{url}">
  <meta property="og:type" content="website">{og}
  <link rel="icon" href="/favicon.svg" type="image/svg+xml">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Shippori+Mincho+B1:wght@500;700&family=Zen+Kaku+Gothic+New:wght@400;500;700&display=swap">
  <link rel="stylesheet" href="/style.css">
  <script src="/i18n.js"></script>
</head>
<body>
{header_html(section)}
  <main class="wrap">
    <article class="detail">
    <a class="back-link" href="{list_href}" data-en="← All {sec_label.lower()}">← {sec_label} 一覧</a>

    <h1 data-en="{esc(title_en)}">{esc(title)}</h1>
    <p class="detail-lead" data-lang-block="ja">{esc_br(lead)}</p>
    <p class="detail-lead" data-lang-block="en">{esc_br(lead_en)}</p>
{shot}
    <div class="detail-actions">
{chr(10).join(btns)}
    </div>{after}
{section_html("こんなときに", "Good for", when, when_en)}
{section_html(hl, hl_en, howto, howto_en, ordered=True)}
{section_html("主な機能", "Features", feats, feats_en)}
{spec}
    </article>
  </main>

  <footer class="wrap site-footer">
    <span class="footer-links">
      <a href="/privacy.html" data-en="Privacy Policy">プライバシーポリシー</a>
    </span>
    <span>© 2026 caprame. All rights reserved.</span>
  </footer>
  <!-- Cloudflare Web Analytics --><script type='module' src='https://static.cloudflareinsights.com/beacon.min.js' data-cf-beacon='{{"token": "991d75fb98894c599ec91ff6296ff0bf"}}'></script><!-- End Cloudflare Web Analytics -->
</body>
</html>
"""


def build_sitemap(content, note_urls=()):
    fixed = ["", "games.html", "notes.html", "about.html", "privacy.html"]
    urls = [f"https://caprame.com/{u}" for u in fixed] + list(note_urls)
    for section in ("tools", "games"):
        for it in content.get(section, []):
            if not it.get("external"):
                urls.append(f"https://caprame.com/{section}/{it['slug']}/")
            if it.get("url", "").startswith("https://caprame.com/"):
                urls.append(it["url"])
    seen = []
    for u in urls:
        if u not in seen:
            seen.append(u)
    body = "\n".join(f"  <url><loc>{u}</loc></url>" for u in seen)
    with open(os.path.join(ROOT, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n'
                '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                f"{body}\n</urlset>\n")


def main():
    with open(os.path.join(ROOT, "content.json"), encoding="utf-8") as f:
        content = json.load(f)
    for section in ("tools", "games"):
        items = content.get(section, [])
        build_tiles(section, items)
        for it in items:
            if it.get("external"):
                continue
            d = os.path.join(ROOT, section, it["slug"])
            os.makedirs(d, exist_ok=True)
            with open(os.path.join(d, "index.html"), "w", encoding="utf-8") as f:
                f.write(page_html(section, it))
            print("wrote", f"{section}/{it['slug']}/")
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import notes
    note_urls = notes.build(header_html, FOOTER)
    build_sitemap(content, note_urls)
    print("wrote tools.js, games.js, sitemap.xml")


if __name__ == "__main__":
    main()
