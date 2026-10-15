"""
Notes(ブログ)のページを作ります。build.py から呼ばれるので、単体で実行する必要はありません。

■ 記事の置き場所
  _notes/記事名/index.md   … 本文
  _notes/記事名/画像.jpg   … その記事で使う画像(本文から ![](画像.jpg) で参照)
  画像がない記事は _notes/記事名.md の1ファイルでもかまいません。
  「記事名」がそのまま URL になります(caprame.com/notes/記事名/)。英数字とハイフンで。

■ 本文の先頭に書く項目
  ---
  title: 記事のタイトル
  date: 2026-10-15
  tags: CG Tips, After Effects
  description: 一覧やSNSで出る説明(省略すると本文の頭から自動で作る)
  draft: true      ← 書いている途中の記事。付けている間は公開されない
  ---

■ 本文の書き方(Markdown)
  ・改行はそのまま改行になる。段落を分けるときは空行を入れる
  ・## 見出し / - 箇条書き / 1. 番号付き / **太字** / `コード` / ```で囲んだコード
  ・画像: ![説明](画像.jpg) 。 ![説明](画像.jpg "キャプション") でキャプション付き
  ・YouTube: 行に @youtube https://www.youtube.com/watch?v=xxxx とだけ書く
  ・画像は書き出すときに撮影情報(EXIF)を消してから公開フォルダへコピーする

■ _ で始まるファイル・フォルダ(_template.md など)は記事として扱わない
"""
import datetime
import html
import os
import re
import shutil
from urllib.parse import parse_qs, quote, urlparse

import markdown

try:
    from PIL import Image, ImageOps
except ImportError:  # Pillow がなければ EXIF を消さずにコピーして警告を出す
    Image = None

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "_notes")
OUT = os.path.join(ROOT, "notes")
SITE = "https://caprame.com"

# 一覧の絞り込みボタンに最初から出すタグ(この順に並ぶ。ほかのタグは記事数の多い順に後ろへ)
FIXED_TAGS = ["CG Tips", "雑記"]
# 英語表示のときのタグ名(ここにないタグはそのまま)
TAG_EN = {"雑記": "Journal"}

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp"}
COPY_EXT = IMAGE_EXT | {".gif", ".mp4", ".webm", ".svg"}


def esc(s):
    return html.escape(s or "", quote=True)


# ---------------- 読み込み ----------------
def parse_front(text):
    meta = {}
    if text.startswith("---"):
        parts = text.split("\n")
        end = None
        for i in range(1, len(parts)):
            if parts[i].strip() == "---":
                end = i
                break
        if end:
            for line in parts[1:end]:
                if ":" in line:
                    k, v = line.split(":", 1)
                    meta[k.strip().lower()] = v.strip()
            text = "\n".join(parts[end + 1:])
    return meta, text


def youtube_embed(url):
    u = urlparse(url.strip())
    vid = ""
    if u.hostname in ("youtu.be",):
        vid = u.path.lstrip("/")
    elif u.hostname and "youtube" in u.hostname:
        if u.path.startswith(("/shorts/", "/embed/", "/live/")):
            vid = u.path.split("/")[2]
        else:
            vid = parse_qs(u.query).get("v", [""])[0]
    if not re.fullmatch(r"[A-Za-z0-9_-]{6,20}", vid or ""):
        return None
    start = parse_qs(u.query).get("t", [""])[0].rstrip("s")
    q = f"?start={start}" if start.isdigit() else ""
    return (f'<div class="embed"><iframe src="https://www.youtube-nocookie.com/embed/{vid}{q}" '
            f'title="YouTube" loading="lazy" allow="accelerometer; encrypted-media; gyroscope; '
            f'picture-in-picture; fullscreen" allowfullscreen></iframe></div>')


def render_body(md_text):
    lines = []
    for line in md_text.split("\n"):
        m = re.match(r"^\s*@youtube\s+(\S+)\s*$", line)
        if m:
            emb = youtube_embed(m.group(1))
            if emb:
                lines += ["", emb, ""]
                continue
            print("  ! YouTube のURLが読めませんでした:", m.group(1))
        lines.append(line)
    body = markdown.markdown("\n".join(lines),
                             extensions=["fenced_code", "tables", "sane_lists", "nl2br"],
                             output_format="html")
    # 画像は遅延読み込み。title 付きの画像だけの段落はキャプション付きの図にする
    body = body.replace("<img ", '<img loading="lazy" decoding="async" ')

    def to_figure(m):
        img = m.group(1)
        cap = re.search(r'title="([^"]*)"', img)
        if not cap:
            return m.group(0)
        img = re.sub(r'\s*title="[^"]*"', "", img)
        return f"<figure>{img}<figcaption>{cap.group(1)}</figcaption></figure>"
    body = re.sub(r"<p>(<img [^>]*>)</p>", to_figure, body)
    body = re.sub(r"<p>(<img [^>]*>)</p>", r"<figure>\1</figure>", body)
    # 外部リンクは新しいタブで開く
    body = re.sub(r'<a href="(https?://(?!caprame\.com)[^"]*)"',
                  r'<a href="\1" target="_blank" rel="noopener"', body)
    # 表は横にスクロールできる枠に入れる(スマホで画面からはみ出さないように)
    body = body.replace("<table>", '<div class="table-wrap"><table>').replace("</table>", "</table></div>")
    return body


def plain_text(body_html, n=110):
    t = re.sub(r"<(pre|figure|div class=\"embed\")[\s\S]*?</(pre|figure|div)>", " ", body_html)
    t = html.unescape(re.sub(r"<[^>]+>", " ", t))
    t = re.sub(r"\s+", " ", t).strip()
    return t if len(t) <= n else t[:n].rstrip() + "…"


def load_posts():
    posts = []
    if not os.path.isdir(SRC):
        return posts
    for name in sorted(os.listdir(SRC)):
        if name.startswith((".", "_")):
            continue
        path = os.path.join(SRC, name)
        if os.path.isdir(path):
            md_path, slug, asset_dir = os.path.join(path, "index.md"), name, path
            if not os.path.exists(md_path):
                continue
        elif name.endswith(".md"):
            md_path, slug, asset_dir = path, name[:-3], None
        else:
            continue
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", slug):
            print(f"  ! 記事名は英小文字・数字・ハイフンだけにしてください(スキップ): {name}")
            continue
        with open(md_path, encoding="utf-8") as f:
            meta, text = parse_front(f.read())
        if meta.get("draft", "").lower() in ("true", "yes", "1"):
            print(f"  - 下書きのため公開しません: {slug}")
            continue
        try:
            date = datetime.date.fromisoformat(meta.get("date", ""))
        except ValueError:
            print(f"  ! date が読めません(2026-10-15 の形で書いてください)。スキップ: {slug}")
            continue
        title = meta.get("title") or slug
        tags = [t.strip() for t in meta.get("tags", "").replace("、", ",").split(",") if t.strip()]
        body = render_body(text)
        first_img = re.search(r'<img [^>]*src="([^"]+)"', body)
        posts.append({
            "slug": slug, "title": title, "date": date, "tags": tags, "body": body,
            "desc": meta.get("description") or plain_text(body),
            "image": first_img.group(1) if first_img else "",
            "asset_dir": asset_dir,
        })
    posts.sort(key=lambda p: (p["date"], p["slug"]), reverse=True)
    return posts


# ---------------- 画像のコピー(EXIF を消す) ----------------
def copy_assets(post, out_dir):
    src = post["asset_dir"]
    if not src:
        return
    for name in os.listdir(src):
        ext = os.path.splitext(name)[1].lower()
        if name.startswith((".", "_")) or ext not in COPY_EXT:
            continue
        a, b = os.path.join(src, name), os.path.join(out_dir, name)
        if ext in IMAGE_EXT and Image is not None:
            with Image.open(a) as im:
                im = ImageOps.exif_transpose(im)  # 向きを反映してから情報を消す
                im.info.clear()
                if ext in (".jpg", ".jpeg"):
                    im.convert("RGB").save(b, quality=92, optimize=True)
                else:
                    im.save(b, optimize=True)
        else:
            if ext in IMAGE_EXT:
                print(f"  ! Pillow がないため撮影情報を消さずにコピーしました: {name}")
            shutil.copyfile(a, b)


# ---------------- ページ ----------------
def tag_label(t):
    return f'<span data-en="{esc(TAG_EN.get(t, t))}">{esc(t)}</span>' if t in TAG_EN else esc(t)


def date_str(d):
    return d.strftime("%Y.%m.%d")


def head(title_ja, title_en, desc, url, og_type="website", image="", content_lang=False):
    og_img = f'\n  <meta property="og:image" content="{esc(image)}">' if image else ""
    cl = ' data-content-lang="ja"' if content_lang else ""
    return f"""<!doctype html>
<html lang="ja"{cl}>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title data-en="{esc(title_en)} | caprame">{esc(title_ja)} | カプラメー</title>
  <meta name="description" content="{esc(desc)}">
  <meta name="theme-color" content="#1b1a1f">
  <link rel="canonical" href="{url}">
  <meta property="og:title" content="{esc(title_ja)} | カプラメー">
  <meta property="og:description" content="{esc(desc)}">
  <meta property="og:url" content="{url}">
  <meta property="og:type" content="{og_type}">{og_img}
  <link rel="icon" href="/favicon.svg" type="image/svg+xml">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Shippori+Mincho+B1:wght@500;700&family=Zen+Kaku+Gothic+New:wght@400;500;700&display=swap">
  <link rel="stylesheet" href="/style.css">
  <script src="/i18n.js"></script>
</head>
<body>
"""


def list_item(p):
    tags = "".join(f'<span class="note-tag">{tag_label(t)}</span>' for t in p["tags"])
    return f"""        <li data-tags="{esc('|'.join(p['tags']))}">
          <a class="note-row" href="/notes/{p['slug']}/">
            <time datetime="{p['date'].isoformat()}">{date_str(p['date'])}</time>
            <span class="note-title">{esc(p['title'])}</span>
            <span class="note-tags">{tags}</span>
          </a>
        </li>"""


FILTER_JS = """  <script>
  /* タグの絞り込み。?tag=〇〇 付きで開くと最初からそのタグで絞り込む */
  (function () {
    var list = document.getElementById("note-list");
    var empty = document.getElementById("note-empty");
    var btns = document.querySelectorAll(".note-filter button");
    function show(tag) {
      var n = 0;
      list.querySelectorAll("li").forEach(function (li) {
        var hit = !tag || li.getAttribute("data-tags").split("|").indexOf(tag) >= 0;
        li.hidden = !hit;
        if (hit) n++;
      });
      empty.hidden = n > 0;
      btns.forEach(function (b) {
        b.setAttribute("aria-pressed", String((b.getAttribute("data-tag") || "") === (tag || "")));
      });
    }
    btns.forEach(function (b) {
      b.addEventListener("click", function () {
        var tag = b.getAttribute("data-tag") || "";
        var u = new URL(location.href);
        if (tag) u.searchParams.set("tag", tag); else u.searchParams.delete("tag");
        history.replaceState(null, "", u);
        show(tag);
      });
    });
    show(new URL(location.href).searchParams.get("tag") || "");
  })();
  </script>
"""


def list_page(posts, header_html, footer):
    counts = {}
    for p in posts:
        for t in p["tags"]:
            counts[t] = counts.get(t, 0) + 1
    tags = FIXED_TAGS + sorted((t for t in counts if t not in FIXED_TAGS), key=lambda t: (-counts[t], t))
    btns = ['        <button type="button" data-tag="" aria-pressed="true">All</button>']
    btns += [f'        <button type="button" data-tag="{esc(t)}" aria-pressed="false">{tag_label(t)}</button>'
             for t in tags]
    items = "\n".join(list_item(p) for p in posts)
    return (head("Notes", "Notes", "CGのtipsと雑記。", f"{SITE}/notes.html")
            + header_html("notes", page_is_list=True)
            + f"""
  <p class="wrap lead" data-en="CG tips and miscellaneous notes, written in Japanese.">CGのtipsと雑記。</p>

  <main class="wrap">
    <div class="notes">
      <div class="note-filter" role="group" aria-label="タグで絞り込む">
{chr(10).join(btns)}
      </div>
      <ul class="note-list" id="note-list">
{items}
      </ul>
      <p class="note-empty" id="note-empty" hidden data-en="No posts yet.">まだ記事はありません。</p>
    </div>
  </main>

""" + footer + FILTER_JS + "</body>\n</html>\n")


def related(post, posts, n=3):
    same = [p for p in posts if p is not post and set(p["tags"]) & set(post["tags"])]
    return same[:n]


def post_page(post, posts, header_html, footer):
    url = f"{SITE}/notes/{post['slug']}/"
    image = post["image"]
    if image and not image.startswith("http"):
        image = f"{SITE}/notes/{post['slug']}/{image}" if not image.startswith("/") else SITE + image
    tags = "".join(f'<a class="note-tag" href="/notes.html?tag={quote(t)}">{tag_label(t)}</a>'
                   for t in post["tags"])
    rel = related(post, posts)
    rel_html = ""
    if rel:
        rel_html = f"""
      <section class="note-related">
        <h2 data-en="Related">関連する記事</h2>
        <ul class="note-list">
{chr(10).join(list_item(p) for p in rel)}
        </ul>
      </section>"""
    return (head(post["title"], post["title"], post["desc"], url, "article", image, content_lang=True)
            + header_html("notes")
            + f"""
  <main class="wrap">
    <article class="note">
      <a class="back-link" href="/notes.html" data-en="← All notes">← Notes 一覧</a>
      <h1>{esc(post['title'])}</h1>
      <p class="note-meta">
        <time datetime="{post['date'].isoformat()}">{date_str(post['date'])}</time>
        <span class="note-tags">{tags}</span>
      </p>
      <div class="prose" lang="ja">
{post['body']}
      </div>
{rel_html}
      <a class="back-link note-back" href="/notes.html" data-en="← All notes">← Notes 一覧</a>
    </article>
  </main>

""" + footer + "</body>\n</html>\n")


def build(header_html, footer):
    """記事一覧(notes.html)と各記事(notes/記事名/)を作る。記事の URL の一覧を返す"""
    posts = load_posts()
    os.makedirs(OUT, exist_ok=True)
    slugs = {p["slug"] for p in posts}
    for name in os.listdir(OUT):
        if os.path.isdir(os.path.join(OUT, name)) and name not in slugs:
            print(f"  ! notes/{name}/ は元の記事がありません(下書きにした・名前を変えた場合は消してください)")
    for p in posts:
        d = os.path.join(OUT, p["slug"])
        os.makedirs(d, exist_ok=True)
        copy_assets(p, d)
        with open(os.path.join(d, "index.html"), "w", encoding="utf-8") as f:
            f.write(post_page(p, posts, header_html, footer))
        print("wrote", f"notes/{p['slug']}/")
    with open(os.path.join(ROOT, "notes.html"), "w", encoding="utf-8") as f:
        f.write(list_page(posts, header_html, footer))
    print(f"wrote notes.html ({len(posts)} 件)")
    return [f"{SITE}/notes/{p['slug']}/" for p in posts]
