"""
Notes(ブログ)のページを作ります。build.py から呼ばれるので、単体で実行する必要はありません。
ふだんは Pages CMS(https://app.pagescms.org)で記事を書くと、GitHub Actions がこれを実行して公開します。

■ 記事の置き場所
  _notes/〇〇.md           … Pages CMS で書いた記事(ファイル名は日時から自動で付く)
  _notes/media/            … Pages CMS で貼った画像
  _notes/〇〇/index.md     … 画像を記事と同じフォルダに置く書き方(手で置く時用)
  ファイル名(フォルダ名)がそのまま URL になります(caprame.com/notes/〇〇/)。

■ 記事の先頭の項目(Pages CMS の入力欄と同じ)
  ---
  title: 記事のタイトル
  date: 2026-10-15
  tags:
    - CG Tips
    - After Effects
  description: 一覧やSNSで出る説明(省略すると本文の頭から自動で作る)
  ---

■ 本文(Markdown)
  ・改行はそのまま改行になる。段落を分ける時は空行を入れる
  ・YouTube: 1行に @youtube https://www.youtube.com/watch?v=xxxx とだけ書く
  ・画像は書き出す時に撮影情報(EXIF)を消してから公開フォルダへコピーする
    (_notes/media の元画像からも消す)
  ・一覧のサムネイルには本文の最初の画像を使う

■ 消した記事のページ(notes/〇〇/)は次の組み立てで自動的に消える
"""
import datetime
import html
import os
import re
import shutil
from urllib.parse import parse_qs, quote, urlparse

import markdown
import yaml

try:
    from PIL import Image, ImageOps
except ImportError:  # Pillow がなければ EXIF を消さずにコピーして警告を出す
    Image = None

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "_notes")
MEDIA_SRC = os.path.join(SRC, "media")
OUT = os.path.join(ROOT, "notes")
MEDIA_OUT = os.path.join(OUT, "media")
SITE = "https://caprame.com"
PER_PAGE = 10  # 一覧の1ページに出す記事数

# 英語表示の時のタグ名(ここにないタグはそのまま)
TAG_EN = {"雑記": "Journal"}

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp"}
COPY_EXT = IMAGE_EXT | {".gif", ".mp4", ".webm", ".svg"}


def esc(s):
    return html.escape(s or "", quote=True)


# ---------------- 読み込み ----------------
def parse_front(text):
    text = text.lstrip("﻿")
    if text.startswith("---"):
        m = re.match(r"---[ \t]*\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|$)", text, re.S)
        if m:
            meta = yaml.safe_load(m.group(1)) or {}
            return (meta if isinstance(meta, dict) else {}), text[m.end():]
    return {}, text


def to_date(v):
    if isinstance(v, datetime.datetime):
        return v.date()
    if isinstance(v, datetime.date):
        return v
    s = str(v or "").strip()
    try:
        return datetime.date.fromisoformat(s[:10])
    except ValueError:
        return None


def to_tags(v):
    if isinstance(v, list):
        items = v
    else:
        items = str(v or "").replace("、", ",").split(",")
    out = []
    for t in items:
        t = str(t or "").strip()
        if t and t not in out:
            out.append(t)
    return out


def make_slug(name, date):
    s = re.sub(r"[^a-z0-9-]+", "-", name.lower()).strip("-")
    s = re.sub(r"-{2,}", "-", s)
    return s or date.isoformat()


def youtube_embed(url):
    u = urlparse(url.strip())
    vid = ""
    if u.hostname == "youtu.be":
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


def preprocess(md_text):
    """@youtube の行を埋め込みにし、エディタが付ける行末の \\ (改行の印)を外す"""
    lines, in_code = [], False
    for line in md_text.split("\n"):
        if line.lstrip().startswith("```"):
            in_code = not in_code
        if not in_code:
            if re.match(r"^\s*\\?@youtube\b", line):
                m = re.search(r"https?://[^\s)\]>]+", line.replace("\\", ""))
                emb = youtube_embed(m.group(0)) if m else None
                if emb:
                    lines += ["", emb, ""]
                    continue
                print("  ! YouTube のURLが読めませんでした:", line.strip())
            line = re.sub(r"(?<!\\)\\$", "", line)
        lines.append(line)
    return "\n".join(lines)


def render_body(md_text, slug):
    body = markdown.markdown(preprocess(md_text),
                             extensions=["fenced_code", "tables", "sane_lists", "nl2br"],
                             output_format="html")

    # 相対パスの画像は記事のフォルダを指すように
    def fix_src(m):
        src = m.group(1)
        if not re.match(r"(https?:)?/", src):
            src = f"/notes/{slug}/{src}"
        return f'<img loading="lazy" decoding="async" src="{src}"'
    body = re.sub(r'<img src="([^"]*)"', fix_src, body)

    # 画像だけの段落は図にする(title があればキャプション)
    def to_figure(m):
        img = m.group(1)
        cap = re.search(r'title="([^"]*)"', img)
        if cap:
            img = re.sub(r'\s*title="[^"]*"', "", img)
            return f"<figure>{img}<figcaption>{cap.group(1)}</figcaption></figure>"
        return f"<figure>{img}</figure>"
    body = re.sub(r"<p>(<img [^>]*>)</p>", to_figure, body)
    # 外部リンクは新しいタブで開く
    body = re.sub(r'<a href="(https?://(?!caprame\.com)[^"]*)"',
                  r'<a href="\1" target="_blank" rel="noopener"', body)
    # 表は横にスクロールできる枠に入れる
    body = body.replace("<table>", '<div class="table-wrap"><table>').replace("</table>", "</table></div>")
    return body


def plain_text(body_html, n=140):
    t = re.sub(r'<(pre|figure|div class="embed")[\s\S]*?</(pre|figure|div)>', " ", body_html)
    t = html.unescape(re.sub(r"<[^>]+>", " ", t))
    t = re.sub(r"\s+", " ", t).strip()
    return t if len(t) <= n else t[:n].rstrip() + "…"


def load_posts():
    posts = []
    if not os.path.isdir(SRC):
        return posts
    for name in sorted(os.listdir(SRC)):
        if name.startswith((".", "_")) or name == "media":
            continue
        path = os.path.join(SRC, name)
        if os.path.isdir(path):
            md_path, base, asset_dir = os.path.join(path, "index.md"), name, path
            if not os.path.exists(md_path):
                continue
        elif name.endswith(".md"):
            md_path, base, asset_dir = path, name[:-3], None
        else:
            continue
        with open(md_path, encoding="utf-8") as f:
            meta, text = parse_front(f.read())
        date = to_date(meta.get("date"))
        if not date:
            print(f"  ! 日付が読めないためスキップしました: {name}")
            continue
        slug = make_slug(base, date)
        body = render_body(text, slug)
        first_img = re.search(r'<img [^>]*src="([^"]+)"', body)
        posts.append({
            "slug": slug, "title": str(meta.get("title") or base), "date": date,
            "tags": to_tags(meta.get("tags")), "body": body,
            "desc": str(meta.get("description") or "").strip() or plain_text(body),
            "image": first_img.group(1) if first_img else "",
            "asset_dir": asset_dir,
        })
    seen = set()
    for p in posts:  # 同じ URL になった記事は後ろに番号を付ける
        s, i = p["slug"], 2
        while p["slug"] in seen:
            p["slug"], i = f"{s}-{i}", i + 1
        seen.add(p["slug"])
    posts.sort(key=lambda p: (p["date"], p["slug"]), reverse=True)
    return posts


# ---------------- 画像のコピー(EXIF を消す) ----------------
def has_meta(path):
    try:
        with Image.open(path) as im:
            return bool(im.getexif()) or any(k in im.info for k in ("exif", "xmp", "XML:com.adobe.xmp"))
    except Exception:
        return False


def strip_save(src, dst):
    with Image.open(src) as im:
        im = ImageOps.exif_transpose(im)  # 向きを反映してから情報を消す
        im.info.clear()
        if os.path.splitext(src)[1].lower() in (".jpg", ".jpeg"):
            im.convert("RGB").save(dst, quality=92, optimize=True)
        else:
            im.save(dst, optimize=True)


def sync_files(src_dir, out_dir, clean_source=False):
    """src_dir の画像などを out_dir へ。out_dir にあって src_dir にないものは消す"""
    os.makedirs(out_dir, exist_ok=True)
    wanted = set()
    for name in sorted(os.listdir(src_dir)):
        a = os.path.join(src_dir, name)
        ext = os.path.splitext(name)[1].lower()
        if name.startswith(".") or not os.path.isfile(a) or ext not in COPY_EXT:
            continue
        wanted.add(name)
        b = os.path.join(out_dir, name)
        if ext in IMAGE_EXT and Image is not None:
            if clean_source and has_meta(a):
                strip_save(a, a)
                print(f"  - 撮影情報を消しました: {os.path.relpath(a, ROOT)}")
            strip_save(a, b)
        else:
            if ext in IMAGE_EXT:
                print(f"  ! Pillow がないため撮影情報を消さずにコピーしました: {name}")
            shutil.copyfile(a, b)
    for name in os.listdir(out_dir):
        p = os.path.join(out_dir, name)
        if os.path.isfile(p) and name not in wanted and name != "index.html":
            os.remove(p)


# ---------------- 部品 ----------------
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


def card(p):
    tags = "".join(f'<span class="note-tag">{tag_label(t)}</span>' for t in p["tags"])
    thumb = ""
    if p["image"]:
        thumb = f'\n            <img class="note-thumb" src="{esc(p["image"])}" alt="" loading="lazy" decoding="async">'
    return f"""        <li data-tags="{esc('|'.join(p['tags']))}">
          <a class="note-card{' has-thumb' if thumb else ''}" href="/notes/{p['slug']}/">
            <span class="note-card-text">
              <time datetime="{p['date'].isoformat()}">{date_str(p['date'])}</time>
              <span class="note-title">{esc(p['title'])}</span>
              <span class="note-excerpt">{esc(p['desc'])}</span>
              <span class="note-tags">{tags}</span>
            </span>{thumb}
          </a>
        </li>"""


LIST_JS = """  <script>
  /* タグの絞り込みとページ送り。?tag=〇〇&page=2 のように開くとその状態で表示する */
  (function () {
    var PER = %d;
    var list = document.getElementById("note-list");
    if (!list) return;
    var items = Array.prototype.slice.call(list.querySelectorAll("li"));
    var pager = document.getElementById("note-pager");
    var btns = document.querySelectorAll(".note-filter button");
    var state = { tag: "", page: 1 };

    function en() { return window.caprameLang && window.caprameLang() === "en"; }

    function read() {
      var q = new URL(location.href).searchParams;
      state.tag = q.get("tag") || "";
      state.page = Math.max(1, parseInt(q.get("page"), 10) || 1);
    }
    function write() {
      var u = new URL(location.href);
      if (state.tag) u.searchParams.set("tag", state.tag); else u.searchParams.delete("tag");
      if (state.page > 1) u.searchParams.set("page", state.page); else u.searchParams.delete("page");
      history.replaceState(null, "", u);
    }

    function pageBtn(label, page, opts) {
      var b = document.createElement("button");
      b.type = "button";
      b.textContent = label;
      if (opts.current) b.setAttribute("aria-current", "page");
      if (opts.disabled) b.disabled = true;
      if (opts.label) b.setAttribute("aria-label", opts.label);
      b.addEventListener("click", function () {
        state.page = page; write(); draw();
        list.scrollIntoView({ block: "start" });
      });
      return b;
    }

    function draw() {
      var hits = items.filter(function (li) {
        return !state.tag || li.getAttribute("data-tags").split("|").indexOf(state.tag) >= 0;
      });
      var pages = Math.max(1, Math.ceil(hits.length / PER));
      if (state.page > pages) state.page = pages;
      var from = (state.page - 1) * PER;
      items.forEach(function (li) { li.hidden = true; });
      hits.slice(from, from + PER).forEach(function (li) { li.hidden = false; });

      pager.textContent = "";
      pager.hidden = pages < 2;
      if (pages > 1) {
        pager.appendChild(pageBtn(en() ? "← Prev" : "← 前へ", state.page - 1, { disabled: state.page === 1 }));
        for (var i = 1; i <= pages; i++) {
          pager.appendChild(pageBtn(String(i), i, { current: i === state.page, label: (en() ? "Page " : "ページ ") + i }));
        }
        pager.appendChild(pageBtn(en() ? "Next →" : "次へ →", state.page + 1, { disabled: state.page === pages }));
      }
      btns.forEach(function (b) {
        b.setAttribute("aria-pressed", String((b.getAttribute("data-tag") || "") === state.tag));
      });
    }

    btns.forEach(function (b) {
      b.addEventListener("click", function () {
        state.tag = b.getAttribute("data-tag") || "";
        state.page = 1; write(); draw();
      });
    });
    document.addEventListener("caprame:langchange", draw);
    read(); draw();
  })();
  </script>
""" % PER_PAGE


def list_page(posts, header_html, footer):
    counts = {}
    for p in posts:
        for t in p["tags"]:
            counts[t] = counts.get(t, 0) + 1
    tags = sorted(counts, key=lambda t: (-counts[t], t))

    if posts:
        items = "\n".join(card(p) for p in posts)
        listing = f"""      <ul class="note-cards" id="note-list">
{items}
      </ul>
      <nav class="note-pager" id="note-pager" aria-label="ページ送り" hidden></nav>"""
    else:
        listing = '      <p class="note-empty" data-en="No posts yet.">まだ記事はありません。</p>'

    filt = ""
    if tags:
        btns = ['          <button type="button" data-tag="" aria-pressed="true">All</button>']
        btns += [f'          <button type="button" data-tag="{esc(t)}" aria-pressed="false">{tag_label(t)}'
                 f'<span class="note-count">{counts[t]}</span></button>' for t in tags]
        filt = f"""
      <section class="note-filter-wrap">
        <h2 data-en="Tags">タグ</h2>
        <div class="note-filter" role="group" aria-label="タグで絞り込む">
{chr(10).join(btns)}
        </div>
      </section>"""

    return (head("Notes", "Notes", "Tipsと雑記。", f"{SITE}/notes.html")
            + header_html("notes", page_is_list=True)
            + f"""
  <p class="wrap lead" data-en="Tips and miscellaneous notes, written in Japanese.">Tipsと雑記。</p>

  <main class="wrap">
    <div class="notes">
{listing}{filt}
    </div>
  </main>

""" + footer + (LIST_JS if posts else "") + "</body>\n</html>\n")


def related(post, posts, n=3):
    return [p for p in posts if p is not post and set(p["tags"]) & set(post["tags"])][:n]


def post_page(post, posts, header_html, footer):
    url = f"{SITE}/notes/{post['slug']}/"
    image = post["image"]
    if image.startswith("/"):
        image = SITE + image
    tags = "".join(f'<a class="note-tag" href="/notes.html?tag={quote(t)}">{tag_label(t)}</a>'
                   for t in post["tags"])
    rel = related(post, posts)
    rel_html = ""
    if rel:
        rel_html = f"""
      <section class="note-related">
        <h2 data-en="Related">関連する記事</h2>
        <ul class="note-cards">
{chr(10).join(card(p) for p in rel)}
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
      </div>{rel_html}
      <a class="back-link note-back" href="/notes.html" data-en="← All notes">← Notes 一覧</a>
    </article>
  </main>

""" + footer + "</body>\n</html>\n")


def build(header_html, footer):
    """記事一覧(notes.html)と各記事(notes/〇〇/)を作る。記事の URL の一覧を返す"""
    posts = load_posts()
    os.makedirs(OUT, exist_ok=True)

    # 共通の画像フォルダ
    if os.path.isdir(MEDIA_SRC):
        sync_files(MEDIA_SRC, MEDIA_OUT, clean_source=True)
    elif os.path.isdir(MEDIA_OUT):
        shutil.rmtree(MEDIA_OUT)

    # 元の記事がなくなったページは消す
    slugs = {p["slug"] for p in posts}
    for name in os.listdir(OUT):
        d = os.path.join(OUT, name)
        if os.path.isdir(d) and name != "media" and name not in slugs:
            shutil.rmtree(d)
            print(f"  - 元の記事がないので消しました: notes/{name}/")

    for p in posts:
        d = os.path.join(OUT, p["slug"])
        os.makedirs(d, exist_ok=True)
        if p["asset_dir"]:
            sync_files(p["asset_dir"], d, clean_source=True)
        with open(os.path.join(d, "index.html"), "w", encoding="utf-8") as f:
            f.write(post_page(p, posts, header_html, footer))
        print("wrote", f"notes/{p['slug']}/")
    with open(os.path.join(ROOT, "notes.html"), "w", encoding="utf-8") as f:
        f.write(list_page(posts, header_html, footer))
    print(f"wrote notes.html ({len(posts)} 件)")
    return [f"{SITE}/notes/{p['slug']}/" for p in posts]
