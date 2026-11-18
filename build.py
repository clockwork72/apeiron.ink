#!/usr/bin/env python3
"""Build the Apeiron site: posts/*.md -> docs/ (served by GitHub Pages).

Python stdlib only. Posts are Markdown files with a small header:

    ---
    title: My post
    date: 2026-11-18
    description: optional one-line summary
    ---

Files starting with "_" are drafts and are skipped. Anything in static/ is
copied to the site root (e.g. static/images/a.jpg -> /images/a.jpg).
"""
import datetime, html, pathlib, re, shutil, sys
from email.utils import format_datetime

ROOT = pathlib.Path(__file__).resolve().parent
POSTS, STATIC, OUT = ROOT / "posts", ROOT / "static", ROOT / "docs"
SITE = {"title": "Apeiron", "url": "https://apeiron.ink", "domain": "apeiron.ink",
        "description": ""}

# ── Markdown (the subset a blog needs) ────────────────────────────────────────
IMG = r'!\[([^\]]*)\]\(\s*([^)\s]+)(?:\s+"([^"]*)")?\s*\)'
LINK = r'\[([^\]]+)\]\(\s*([^)\s]+)(?:\s+"[^"]*")?\s*\)'
UL, OL = re.compile(r"[-*+]\s+(.*)"), re.compile(r"\d+[.)]\s+(.*)")
HR = re.compile(r"(\*\s*){3,}|(-\s*){3,}|(_\s*){3,}")


def esc(s):
    return html.escape(s, quote=True)


def attr(s):
    return s.replace('"', "&quot;")


def inline(text):
    stash = []

    def keep(s):
        stash.append(s)
        return f"\x00{len(stash) - 1}\x00"

    text = re.sub(r"`([^`]+)`", lambda m: keep(f"<code>{html.escape(m[1], quote=False)}</code>"), text)
    text = html.escape(text, quote=False)
    text = re.sub(IMG, lambda m: keep(f'<img src="{attr(m[2])}" alt="{attr(m[1])}" loading="lazy">'), text)
    text = re.sub(LINK, lambda m: f'<a href="{attr(m[2])}">{m[1]}</a>', text)
    text = re.sub(r"\*\*(?=\S)(.+?)(?<=\S)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<![\w*])\*(?=\S)(.+?)(?<=\S)\*(?![\w*])", r"<em>\1</em>", text)
    return re.sub(r"\x00(\d+)\x00", lambda m: stash[int(m[1])], text)


def figure(m):
    src, alt = attr(html.escape(m[2], quote=False)), attr(html.escape(m[1], quote=False))
    cap = f"<figcaption>{inline(m[3])}</figcaption>" if m[3] else ""
    return f'<figure><img src="{src}" alt="{alt}" loading="lazy">{cap}</figure>'


def markdown(src):
    lines, out, para, i = src.replace("\r\n", "\n").split("\n"), [], [], 0

    def flush():
        if para:
            text = " ".join(l.strip() for l in para)
            m = re.fullmatch(IMG, text)
            out.append(figure(m) if m else f"<p>{inline(text)}</p>")
            para.clear()

    while i < len(lines):
        line, s = lines[i], lines[i].strip()
        if s.startswith("```"):                       # code block
            flush(); i += 1; code = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code.append(lines[i]); i += 1
            out.append(f"<pre><code>{html.escape(chr(10).join(code), quote=False)}</code></pre>")
            i += 1; continue
        if not s:
            flush(); i += 1; continue
        if HR.fullmatch(s):
            flush(); out.append("<hr>"); i += 1; continue
        m = re.match(r"(#{1,6})\s+(.+?)\s*#*$", s)
        if m:
            flush(); n = len(m[1]); out.append(f"<h{n}>{inline(m[2])}</h{n}>"); i += 1; continue
        if s.startswith(">"):                         # blockquote
            flush(); q = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                q.append(re.sub(r"^\s*>\s?", "", lines[i])); i += 1
            out.append(f"<blockquote>{markdown(chr(10).join(q))}</blockquote>"); continue
        if UL.match(s) or OL.match(s):                # list
            flush(); pat = OL if OL.match(s) else UL; tag = "ol" if pat is OL else "ul"; items = []
            while i < len(lines):
                t = lines[i].strip(); mm = pat.match(t)
                if mm:
                    items.append(mm[1])
                elif t and items and lines[i][:1] in (" ", "\t"):
                    items[-1] += " " + t
                else:
                    break
                i += 1
            out.append(f"<{tag}>" + "".join(f"<li>{inline(x)}</li>" for x in items) + f"</{tag}>"); continue
        if s.startswith("<") and not para:            # raw HTML block, passed through
            block = []
            while i < len(lines) and lines[i].strip():
                block.append(lines[i]); i += 1
            out.append("\n".join(block)); continue
        para.append(line); i += 1
    flush()
    return "\n".join(out)


# ── Posts ─────────────────────────────────────────────────────────────────────
def long_date(d):
    return f"{d.day} {d:%B %Y}"


def load(path):
    text = path.read_text(encoding="utf-8")
    meta, m = {}, re.match(r"---\n(.*?)\n---[ \t]*(?:\n|$)(.*)", text, re.S)
    if m:
        for line in m[1].splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip().lower()] = v.strip().strip("\"'")
        text = m[2]
    slug = re.sub(r"[^a-z0-9]+", "-", meta.get("slug", path.stem).lower()).strip("-")
    try:
        date = datetime.date.fromisoformat(meta.get("date", "")[:10])
    except ValueError:
        date = datetime.date.fromtimestamp(path.stat().st_mtime)
        print(f"  ! {path.name}: no valid 'date:', using {date}", file=sys.stderr)
    body = markdown(text)
    first = re.search(r"<p>(.*?)</p>", body, re.S)
    summary = meta.get("description") or (html.unescape(re.sub(r"<[^>]+>", "", first[1])) if first else "")
    if len(summary) > 200:
        summary = summary[:200].rsplit(" ", 1)[0] + "…"
    return {"title": meta.get("title") or path.stem.replace("-", " ").capitalize(), "slug": slug,
            "date": date, "html": body, "summary": summary, "url": f"{SITE['url']}/{slug}/"}


# ── Templates ─────────────────────────────────────────────────────────────────
FONTS = ("https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,300..650;"
         "1,9..144,300..600&family=Newsreader:ital,opsz,wght@0,6..72,400..560;1,6..72,400..480&display=swap")


def page(title, body, url, description="", kind="home"):
    full = SITE["title"] if title == SITE["title"] else f"{title} · {SITE['title']}"
    desc = f'<meta name="description" content="{esc(description)}">\n' if description else ""
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(full)}</title>
{desc}<link rel="canonical" href="{url}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:url" content="{url}">
<meta property="og:site_name" content="{SITE['title']}">
<link rel="alternate" type="application/rss+xml" title="{SITE['title']}" href="/feed.xml">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="{FONTS}">
<link rel="stylesheet" href="/style.css">
</head>
<body class="is-{kind}">
<div class="frame">
<header class="masthead"><a class="wordmark" href="/">{SITE['title']}</a></header>
<main>
{body}
</main>
<footer class="colophon"><a href="/feed.xml">RSS feed</a></footer>
</div>
</body>
</html>
"""


def home(posts):
    tagline = f'<p class="tagline">{esc(SITE["description"])}</p>\n' if SITE["description"] else ""
    if not posts:
        return tagline + '<p class="empty">No posts yet.</p>'
    items = "\n".join(
        f'<li><a href="/{p["slug"]}/"><h2>{esc(p["title"])}</h2></a>'
        f'<time datetime="{p["date"]}">{long_date(p["date"])}</time>'
        + (f'<p class="summary">{esc(p["summary"])}</p>' if p["summary"] else "") + "</li>"
        for p in posts)
    return f'{tagline}<ul class="posts">\n{items}\n</ul>'


def post(p):
    return (f'<article class="post">\n<header><h1>{esc(p["title"])}</h1>'
            f'<time datetime="{p["date"]}">{long_date(p["date"])}</time></header>\n'
            f'<div class="content">\n{p["html"]}\n</div>\n</article>\n'
            f'<nav class="back"><a href="/">All posts</a></nav>')


def feed(posts):
    items = "".join(
        f"<item><title>{esc(p['title'])}</title><link>{p['url']}</link><guid>{p['url']}</guid>"
        f"<pubDate>{format_datetime(datetime.datetime.combine(p['date'], datetime.time(12), datetime.timezone.utc))}</pubDate>"
        f"<description>{esc(p['html'])}</description></item>\n" for p in posts[:20])
    return (f'<?xml version="1.0" encoding="utf-8"?>\n<rss version="2.0"><channel>'
            f"<title>{SITE['title']}</title><link>{SITE['url']}/</link>"
            f"<description>{esc(SITE['description'] or SITE['title'])}</description>\n{items}</channel></rss>\n")


# ── Build ─────────────────────────────────────────────────────────────────────
def main():
    posts = sorted((load(f) for f in POSTS.glob("*.md") if not f.name.startswith("_")),
                   key=lambda p: p["date"], reverse=True)
    slugs = [p["slug"] for p in posts]
    dupes = {s for s in slugs if slugs.count(s) > 1}
    if dupes:
        sys.exit(f"Two posts share the address: {', '.join(sorted(dupes))}. Rename one file.")

    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(STATIC, OUT, dirs_exist_ok=True) if STATIC.exists() else OUT.mkdir()

    (OUT / "index.html").write_text(page(SITE["title"], home(posts), SITE["url"] + "/", SITE["description"]))
    for p in posts:
        (OUT / p["slug"]).mkdir()
        (OUT / p["slug"] / "index.html").write_text(page(p["title"], post(p), p["url"], p["summary"], "post"))
    (OUT / "404.html").write_text(page("Page not found",
        '<article class="post"><header><h1>Page not found</h1></header>\n'
        '<div class="content"><p>There is nothing at this address. '
        'Go to the <a href="/">home page</a> to see all posts.</p></div></article>',
        SITE["url"] + "/404.html", kind="post"))
    (OUT / "feed.xml").write_text(feed(posts))
    (OUT / "CNAME").write_text(SITE["domain"] + "\n")
    (OUT / ".nojekyll").write_text("")
    print(f"Built {len(posts)} post(s) into docs/")


if __name__ == "__main__":
    main()
