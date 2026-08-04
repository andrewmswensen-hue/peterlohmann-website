#!/usr/bin/env python3
"""
Imports Peter's blog from peterlohmann.com into this site.

WHAT IT DOES (re-runnable):
  - Pulls every post from Squarespace's JSON feed (title, date, body, featured image).
  - Downloads featured + inline images into images/blog/ (self-hosted; skips ones already there).
  - Cleans the Squarespace markup into our article style, keeps YouTube as clean players,
    converts embedded tweets to a quote + "View on X" link, rewrites post-to-post links local.
  - Writes one blog/<slug>.html per post and rebuilds blog.html (featured banner + card grid).

RUN:  python3 build-blog.py           (all posts)
      LIMIT=3 python3 build-blog.py   (first 3, for testing)

Needs: lxml (already installed). No other deps.
"""
import json, urllib.request, urllib.parse, time, re, os, html as htmlmod, datetime
import lxml.html
from lxml.html import builder as E

HERE = os.path.dirname(os.path.abspath(__file__))
IMGDIR = os.path.join(HERE, "images", "blog")
BLOGDIR = os.path.join(HERE, "blog")
os.makedirs(IMGDIR, exist_ok=True)
os.makedirs(BLOGDIR, exist_ok=True)
LIMIT = int(os.environ.get("LIMIT", "0"))
ASSET_V = "20"  # cache-bust version for styles.css / site.js (keep in sync with the rest of the site)

UA = {"User-Agent": "Mozilla/5.0"}

def fetch_json(url):
    return json.load(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40))

def fetch_all():
    base = "https://www.peterlohmann.com/blog?format=json&nojs=true"
    items, url, pages = [], base, 0
    while True:
        d = fetch_json(url); pages += 1
        items.extend(d.get("items", []))
        pag = d.get("pagination", {})
        if pag.get("nextPage") and pag.get("nextPageOffset"):
            url = base + "&offset=" + str(pag["nextPageOffset"]); time.sleep(0.25)
        else:
            break
        if pages > 40:
            break
    # newest first, de-dupe by slug
    seen, out = set(), []
    for it in sorted(items, key=lambda x: x.get("publishOn", 0), reverse=True):
        slug = it["fullUrl"].rstrip("/").split("/")[-1]
        if slug in seen:
            continue
        seen.add(slug); it["_slug"] = slug; out.append(it)
    return out

def fmt_date(ms):
    if not ms:
        return ""
    d = datetime.datetime.fromtimestamp(ms / 1000, datetime.timezone.utc)
    return f"{d.strftime('%b')} {d.day}, {d.year}"

_dl_cache = {}
def download_image(url, basename, width=1000):
    """Fetch an image and save it as an optimized WebP at images/blog/<basename>.webp.
    Reuses an already-downloaded original (converts it in place, no re-download) so re-runs
    are fast. Returns the repo-relative path or None. Falls back to the original if WebP fails."""
    if not url or url.startswith("data:"):
        return None
    if url.startswith("//"):
        url = "https:" + url
    url = htmlmod.unescape(url)
    dl = url
    if "squarespace-cdn.com" in url and "format=" not in url:
        dl = url + ("&" if "?" in url else "?") + f"format={width}w"

    webp_rel = f"images/blog/{basename}.webp"
    webp_dest = os.path.join(IMGDIR, basename + ".webp")
    if os.path.exists(webp_dest) and os.path.getsize(webp_dest) > 0:
        return webp_rel
    if dl in _dl_cache:
        return _dl_cache[dl]

    # reuse a previously-downloaded original if present (convert in place); else download
    data, orig_path = None, None
    for ext in (".png", ".jpg", ".jpeg", ".gif"):
        p = os.path.join(IMGDIR, basename + ext)
        if os.path.exists(p) and os.path.getsize(p) > 0:
            data, orig_path = open(p, "rb").read(), p
            break
    if data is None:
        try:
            data = urllib.request.urlopen(urllib.request.Request(dl, headers=UA), timeout=60).read()
        except Exception as e:
            print(f"    ! image download failed ({e}) for {url[:80]}")
            return None
        if len(data) < 100:
            return None

    # convert to optimized WebP
    try:
        from PIL import Image
        import io
        im = Image.open(io.BytesIO(data))
        if im.width > width:
            im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
        has_alpha = im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info)
        im = im.convert("RGBA" if has_alpha else "RGB")
        im.save(webp_dest, "WEBP", quality=80, method=6)
        if orig_path and orig_path != webp_dest:
            os.remove(orig_path)  # tidy up the now-redundant original
        _dl_cache[dl] = webp_rel
        return webp_rel
    except Exception as e:
        print(f"    ! webp convert failed ({e}); keeping original for {basename}")
        if orig_path:
            _dl_cache[dl] = f"images/blog/{os.path.basename(orig_path)}"
            return _dl_cache[dl]
        ext = os.path.splitext(urllib.parse.urlparse(url).path)[1].lower()
        if ext not in (".jpg", ".jpeg", ".png", ".gif"):
            ext = ".jpg"
        with open(os.path.join(IMGDIR, basename + ext), "wb") as f:
            f.write(data)
        _dl_cache[dl] = f"images/blog/{basename}{ext}"
        return _dl_cache[dl]

def yt_id(url):
    m = re.search(r"(?:youtu\.be/|youtube\.com/(?:embed/|watch\?v=|v/))([A-Za-z0-9_-]{6,})", url or "")
    return m.group(1) if m else None

INTERNAL_POST = re.compile(r'^(?:https?://(?:www\.)?peterlohmann\.com)?/blog/([A-Za-z0-9\-]+)/?$')
# Other internal (non-post) pages / root-relative paths -> local site files.
INTERNAL_PAGE = re.compile(r'^(?:https?://(?:www\.)?peterlohmann\.com)?/([A-Za-z0-9\-]*)/?$')
PAGE_MAP = {
    '': '../index.html', 'about': '../index.html', 'contact': '../contact.html',
    'podcast': '../podcast.html', 'newsletter': '../newsletter.html', 'blog': '../blog.html',
    'products': '../products.html', 'peterbot': '../peterbot.html', 'featured': '../featured.html',
    'largest-pm-companies': '../largest-pm-companies.html',
}

def process_body(body, slug):
    """Clean Squarespace body HTML -> our article HTML. Returns an HTML string."""
    root = lxml.html.fromstring("<div>" + body + "</div>")

    # 1) drop scripts/styles/noscript
    for tag in ("script", "style", "noscript"):
        for el in root.xpath(f".//{tag}"):
            el.getparent().remove(el)

    # 2) embed blocks (YouTube -> player, Twitter/X -> quote+link, else -> link)
    for wrap in root.xpath('.//*[@data-block-json]'):
        raw = wrap.get("data-block-json")
        url = None
        try:
            j = json.loads(htmlmod.unescape(raw)); url = j.get("url") or (j.get("oembed") or {}).get("url")
        except Exception:
            m = re.search(r'"url":"([^"]+)"', raw or ""); url = m.group(1) if m else None
        vid = yt_id(url or "")
        if vid:
            new = lxml.html.fromstring(
                '<div class="embed-frame video"><iframe src="https://www.youtube.com/embed/%s" '
                'title="YouTube video" allow="accelerometer; autoplay; clipboard-write; encrypted-media; '
                'gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" '
                'allowfullscreen></iframe></div>' % vid)
        elif url and ("twitter.com" in url or "x.com" in url):
            new = lxml.html.fromstring(
                '<p class="embed-note"><a href="%s" target="_blank" rel="noopener">View post on X &rarr;</a></p>' % htmlmod.escape(url, quote=True))
        elif url:
            new = lxml.html.fromstring(
                '<p class="embed-note"><a href="%s" target="_blank" rel="noopener">View embedded content &rarr;</a></p>' % htmlmod.escape(url, quote=True))
        else:
            continue
        p = wrap.getparent()
        if p is not None:
            p.replace(wrap, new)

    # 3) embedded tweet cards (blockquote.twitter-tweet) -> quote + View on X
    for bq in root.xpath('.//blockquote[contains(@class,"twitter-tweet")]'):
        text = " ".join(bq.xpath('.//p[1]//text()')).strip()
        links = bq.xpath('.//a[@href]')
        perma = ""
        for a in links:
            if "twitter.com" in (a.get("href") or "") or "x.com" in (a.get("href") or ""):
                perma = a.get("href")
        html = '<blockquote>'
        if text:
            html += "<p>" + htmlmod.escape(text) + "</p>"
        if perma:
            html += '<p class="embed-note"><a href="%s" target="_blank" rel="noopener">View post on X &rarr;</a></p>' % htmlmod.escape(perma, quote=True)
        html += "</blockquote>"
        new = lxml.html.fromstring(html)
        bq.getparent().replace(bq, new)

    # 4) images -> download + rebuild as clean <figure>
    imgn = 0
    for img in root.xpath('.//img'):
        src = img.get("data-src") or img.get("data-image") or img.get("src")
        if not src or src.startswith("data:"):
            # can't recover a real URL; drop the empty image
            anc = img.getparent()
            if anc is not None:
                anc.remove(img)
            continue
        imgn += 1
        rel = download_image(src, f"{slug}--{imgn:02d}")
        if not rel:
            continue
        alt = img.get("alt") or ""
        # caption: look for a figcaption/image-caption near the image's block
        cap = ""
        block = img
        for _ in range(6):
            if block.getparent() is None:
                break
            block = block.getparent()
            cls = block.get("class") or ""
            if "image-block" in cls or "sqs-block-image" in cls or block.tag == "figure":
                caps = block.xpath('.//figcaption//text() | .//*[contains(@class,"image-caption")]//text()')
                cap = " ".join(t.strip() for t in caps if t.strip())
                break
        fightml = '<figure><img src="../%s" alt="%s" loading="lazy"/>' % (rel, htmlmod.escape(alt, quote=True))
        if cap:
            fightml += "<figcaption>" + htmlmod.escape(cap) + "</figcaption>"
        fightml += "</figure>"
        fig = lxml.html.fromstring(fightml)
        # replace the OUTERMOST image wrapper (Squarespace image block or any <figure>)
        # so we get one clean figure per image, no padding hacks and no nested figures
        target = img
        b2 = img
        for _ in range(8):
            if b2.getparent() is None:
                break
            b2 = b2.getparent()
            cls = b2.get("class") or ""
            if b2.tag == "figure" or "image-block" in cls or "sqs-block-image" in cls:
                target = b2  # keep climbing to the highest matching wrapper
        p = target.getparent()
        if p is not None:
            p.replace(target, fig)

    # 5) rewrite internal post-to-post links to local files; strip tracking noise
    for a in root.xpath('.//a[@href]'):
        href = (a.get("href") or "").strip()
        m = INTERNAL_POST.match(href)
        pg = INTERNAL_PAGE.match(href) if not m else None
        if m:
            a.set("href", m.group(1) + ".html")
        elif pg and pg.group(1) in PAGE_MAP and "report.peterlohmann.com" not in href:
            a.set("href", PAGE_MAP[pg.group(1)])           # e.g. /contact -> ../contact.html
        elif href.startswith("http") and "peterlohmann.com" not in href:
            a.set("target", "_blank"); a.set("rel", "noopener")

    # serialize inner html of the root div
    inner = (root.text or "")
    for child in root:
        inner += lxml.html.tostring(child, encoding="unicode")
    # tidy: collapse Squarespace's empty layout wrappers' noise is fine to leave; drop stray &nbsp; runs
    return inner

NAV = """  <div class="bar">
    <a class="brand" href="../index.html">Peter <span>Lohmann</span></a>
    <button class="nav-toggle" aria-expanded="false" aria-controls="navlinks">Menu</button>
    <div class="links" id="navlinks">
      <a href="../index.html">About</a>
      <a href="../newsletter.html">Newsletter</a>
      <a href="../podcast.html">Podcast</a>
      <a href="../largest-pm-companies.html">Largest PM Companies</a>
      <a href="../blog.html" class="active">Blog</a>
      <a href="../report/index.html">M&amp;A Report</a>
      <a href="../peterbot.html">PeterBot</a>
      <a href="../products.html">Products</a>
    </div>
    <a class="btn btn-navy btn-sm cta" href="../contact.html">Contact</a>
  </div>"""

FOOT = """      <nav class="foot-links" aria-label="Footer">
        <a href="../index.html">About</a>
        <a href="../newsletter.html">Newsletter</a>
        <a href="../podcast.html">Podcast</a>
        <a href="../largest-pm-companies.html">Largest PM Companies</a>
        <a href="../blog.html">Blog</a>
        <a href="../report/index.html">M&amp;A Report</a>
        <a href="../peterbot.html">PeterBot</a>
        <a href="../products.html">Products</a>
        <a href="../featured.html">Featured</a>
        <a href="../contact.html">Contact</a>
        <a href="https://www.linkedin.com/in/pslohmann/" target="_blank" rel="noopener">LinkedIn</a>
        <a href="../financial-interest-disclosure.html">Disclosures</a>
      </nav>"""

DISC = ("The content of this website is for informational purposes only and does not constitute "
        "professional advice. I may have consulting agreements with, or financial interests in, "
        "companies mentioned on this website. Additionally, some of the links across this site may be "
        "affiliate links, meaning I may earn a commission if you make a purchase through those links. "
        "Always perform your own due diligence before making any financial or business decisions.")

# Social icons (absolute URLs, so identical for blog.html and the posts)
_SOC_ICONS = (
  '<a href="https://www.youtube.com/@peterlohmann" target="_blank" rel="noopener" aria-label="YouTube"><svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M23.5 6.2a3 3 0 0 0-2.1-2.1C19.5 3.5 12 3.5 12 3.5s-7.5 0-9.4.6A3 3 0 0 0 .5 6.2 31 31 0 0 0 0 12a31 31 0 0 0 .5 5.8 3 3 0 0 0 2.1 2.1c1.9.6 9.4.6 9.4.6s7.5 0 9.4-.6a3 3 0 0 0 2.1-2.1A31 31 0 0 0 24 12a31 31 0 0 0-.5-5.8zM9.5 15.6V8.4l6.3 3.6-6.3 3.6z"/></svg></a>'
  '<a href="https://www.linkedin.com/in/pslohmann/" target="_blank" rel="noopener" aria-label="LinkedIn"><svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M20.5 2h-17A1.5 1.5 0 0 0 2 3.5v17A1.5 1.5 0 0 0 3.5 22h17a1.5 1.5 0 0 0 1.5-1.5v-17A1.5 1.5 0 0 0 20.5 2zM8 19H5v-9h3zM6.5 8.3a1.7 1.7 0 1 1 0-3.5 1.7 1.7 0 0 1 0 3.5zM19 19h-3v-4.4c0-1 0-2.4-1.5-2.4S13 13.4 13 14.5V19h-3v-9h2.9v1.2h.04a3.2 3.2 0 0 1 2.9-1.6c3.1 0 3.7 2 3.7 4.7z"/></svg></a>'
  '<a href="https://x.com/pslohmann" target="_blank" rel="noopener" aria-label="X (formerly Twitter)"><svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M18.9 2H22l-7.6 8.7L23.3 22h-6.9l-5.4-7-6.2 7H1.7l8.1-9.3L.9 2h7.1l4.9 6.5zM17.7 20h1.9L7.1 4H5.1z"/></svg></a>'
  '<a href="https://www.facebook.com/lohmann" target="_blank" rel="noopener" aria-label="Facebook"><svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M24 12a12 12 0 1 0-13.9 11.9v-8.4H7v-3.5h3.1V9.4c0-3 1.8-4.7 4.5-4.7 1.3 0 2.7.24 2.7.24v3H15.8c-1.5 0-2 .93-2 1.9v2.2h3.4l-.54 3.5h-2.9v8.4A12 12 0 0 0 24 12z"/></svg></a>'
  '<a href="https://www.instagram.com/peterlohmann_media/" target="_blank" rel="noopener" aria-label="Instagram"><svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M12 2.2c3.2 0 3.6 0 4.9.07 1.2.05 1.8.25 2.2.42.56.2.96.48 1.38.9.42.42.7.82.9 1.38.17.4.37 1 .42 2.2.06 1.3.07 1.7.07 4.9s0 3.6-.07 4.9c-.05 1.2-.25 1.8-.42 2.2a3.7 3.7 0 0 1-.9 1.38 3.7 3.7 0 0 1-1.38.9c-.4.17-1 .37-2.2.42-1.3.06-1.7.07-4.9.07s-3.6 0-4.9-.07c-1.2-.05-1.8-.25-2.2-.42a3.7 3.7 0 0 1-1.38-.9 3.7 3.7 0 0 1-.9-1.38c-.17-.4-.37-1-.42-2.2-.06-1.3-.07-1.7-.07-4.9s0-3.6.07-4.9c.05-1.2.25-1.8.42-2.2.2-.56.48-.96.9-1.38.42-.42.82-.7 1.38-.9.4-.17 1-.37 2.2-.42C8.4 2.2 8.8 2.2 12 2.2zm0 3.14A6.66 6.66 0 1 0 18.66 12 6.66 6.66 0 0 0 12 5.34zm0 10.98A4.32 4.32 0 1 1 16.32 12 4.32 4.32 0 0 1 12 16.32zm6.9-11.24a1.56 1.56 0 1 1-1.56-1.56 1.56 1.56 0 0 1 1.56 1.56z"/></svg></a>'
)
FOOT_SOCIAL = f'    <div class="foot-social" aria-label="Peter Lohmann on social media">\n      {_SOC_ICONS}\n    </div>'
POST_FOLLOW = f'        <div class="post-follow">\n          <span class="pf-label">Follow Peter for more:</span>\n          <span class="inline-social">{_SOC_ICONS}</span>\n        </div>'

def esc(s):
    return htmlmod.escape(s or "", quote=True)

def write_post(it, body_html, cover=None):
    slug = it["_slug"]
    title = it.get("title") or slug
    date = fmt_date(it.get("publishOn"))
    author = (it.get("author") or {}).get("displayName") or "Peter Lohmann"
    excerpt = re.sub(r"<[^>]+>", "", it.get("excerpt") or "").strip()
    desc = (excerpt or title)[:180]
    cover_html = (f'\n        <figure class="article-cover"><img src="../{cover}" alt="" /></figure>'
                  if cover else "")
    page = f"""<!-- GENERATED by build-blog.py from peterlohmann.com. Do not hand-edit; re-run the script. -->
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>{esc(title)} &middot; Peter Lohmann</title>
<meta name="description" content="{esc(desc)}" />
<link rel="icon" type="image/svg+xml" href="../favicon.svg" />
<link rel="icon" type="image/png" sizes="32x32" href="../favicon-32.png" />
<link rel="apple-touch-icon" href="../favicon.png" />
<link rel="stylesheet" href="../styles.css?v={ASSET_V}" />
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<nav class="top" aria-label="Primary">
{NAV}
</nav>
<main id="main">
  <article class="band">
    <div class="wrap">
      <div class="article">
        <a class="article-back" href="../blog.html">&larr; All posts</a>
        <div class="article-meta">{esc(date)} &middot; by {esc(author)}</div>
        <h1>{esc(title)}</h1>{cover_html}
        <div class="article-body">
{body_html}
        </div>
{POST_FOLLOW}
      </div>
    </div>
  </article>
  <section class="band tight wash">
    <div class="wrap center">
      <h2 class="h-lead">Get posts like this in your inbox.</h2>
      <p class="sub" style="margin:8px auto 20px;">Twice a week, read by 20,000+ property management professionals.</p>
      <a class="btn btn-primary" href="../newsletter.html">Subscribe to the newsletter</a>
    </div>
  </section>
</main>
<footer class="site">
  <div class="wrap">
    <div class="foot-grid">
      <div class="brand" style="font-weight:700;color:var(--navy);">Peter <span style="color:var(--primary);">Lohmann</span></div>
{FOOT}
    </div>
{FOOT_SOCIAL}
    <p class="disc">{DISC}</p>
  </div>
</footer>
<script src="../site.js?v={ASSET_V}"></script>
</body>
</html>
"""
    with open(os.path.join(BLOGDIR, slug + ".html"), "w") as f:
        f.write(page)

def write_index(posts):
    # posts: list of dicts with slug, title, date, excerpt, cover(rel path or None)
    def card(p, featured=False):
        img = (f'<div class="ph-img"><img src="{p["cover"]}" alt="" loading="lazy"></div>'
               if p["cover"] else '<div class="ph-img"><span class="ph-note">No image</span></div>')
        if featured:
            return f"""      <a class="feature-post" href="blog/{p['slug']}.html">
        {img}
        <div class="fp-body">
          <span class="tag tag-warn">Latest</span>
          <div class="date">{esc(p['date'])}</div>
          <h2>{esc(p['title'])}</h2>
          <p>{esc(p['excerpt'])}</p>
          <span class="arrow">Read the post &rarr;</span>
        </div>
      </a>"""
        return f"""        <a class="post-card" href="blog/{p['slug']}.html">
          {img}
          <div class="pc-body"><div class="date">{esc(p['date'])}</div><h3>{esc(p['title'])}</h3><p>{esc(p['excerpt'])}</p><span class="arrow">Read &rarr;</span></div>
        </a>"""

    feat = card(posts[0], featured=True)
    grid = "\n".join(card(p) for p in posts[1:])
    page = f"""<!-- Blog index. The post cards are GENERATED by build-blog.py. Re-run it to refresh. -->
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Blog &middot; Peter Lohmann</title>
<meta name="description" content="Peter Lohmann's property management blog: software, M&amp;A, NARPM, fair housing, and honest takes on the industry." />
<link rel="icon" type="image/svg+xml" href="favicon.svg" />
<link rel="icon" type="image/png" sizes="32x32" href="favicon-32.png" />
<link rel="apple-touch-icon" href="favicon.png" />
<link rel="stylesheet" href="styles.css?v={ASSET_V}" />
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<nav class="top" aria-label="Primary">
  <div class="bar">
    <a class="brand" href="index.html">Peter <span>Lohmann</span></a>
    <button class="nav-toggle" aria-expanded="false" aria-controls="navlinks">Menu</button>
    <div class="links" id="navlinks">
      <a href="index.html">About</a>
      <a href="newsletter.html">Newsletter</a>
      <a href="podcast.html">Podcast</a>
      <a href="largest-pm-companies.html">Largest PM Companies</a>
      <a href="blog.html" class="active">Blog</a>
      <a href="report/index.html">M&amp;A Report</a>
      <a href="peterbot.html">PeterBot</a>
      <a href="products.html">Products</a>
    </div>
    <a class="btn btn-navy btn-sm cta" href="contact.html">Contact</a>
  </div>
</nav>
<main id="main">
  <header class="page-hero">
    <div class="wrap">
      <div class="ticks" aria-hidden="true"><i></i><i></i><i></i></div>
      <span class="kicker">The Blog</span>
      <h1>Property management, in plain English.</h1>
      <p class="lead">Longer takes on the industry: software, M&amp;A, NARPM, fair housing, and the occasional honest rant. {len(posts)} posts and counting.</p>
    </div>
  </header>
  <section class="band">
    <div class="wrap">
{feat}
      <div class="post-cards mt-lg">
{grid}
      </div>
    </div>
  </section>
  <section class="band tight wash">
    <div class="wrap center">
      <h2 class="h-lead">Never miss a post.</h2>
      <p class="sub" style="margin:8px auto 20px;">The best of the blog lands in the newsletter twice a week, read by 20,000+ PM professionals.</p>
      <a class="btn btn-primary" href="newsletter.html">Subscribe to the newsletter</a>
    </div>
  </section>
</main>
<footer class="site">
  <div class="wrap">
    <div class="foot-grid">
      <div class="brand" style="font-weight:700;color:var(--navy);">Peter <span style="color:var(--primary);">Lohmann</span></div>
      <nav class="foot-links" aria-label="Footer">
        <a href="index.html">About</a>
        <a href="newsletter.html">Newsletter</a>
        <a href="podcast.html">Podcast</a>
        <a href="largest-pm-companies.html">Largest PM Companies</a>
        <a href="blog.html">Blog</a>
        <a href="report/index.html">M&amp;A Report</a>
        <a href="peterbot.html">PeterBot</a>
        <a href="products.html">Products</a>
        <a href="featured.html">Featured</a>
        <a href="contact.html">Contact</a>
        <a href="https://www.linkedin.com/in/pslohmann/" target="_blank" rel="noopener">LinkedIn</a>
        <a href="financial-interest-disclosure.html">Disclosures</a>
      </nav>
    </div>
{FOOT_SOCIAL}
    <p class="disc">{DISC}</p>
  </div>
</footer>
<script src="site.js?v={ASSET_V}"></script>
</body>
</html>
"""
    with open(os.path.join(HERE, "blog.html"), "w") as f:
        f.write(page)

def main():
    posts = fetch_all()
    if LIMIT:
        posts = posts[:LIMIT]
    print(f"Processing {len(posts)} posts...")
    index_rows = []
    for i, it in enumerate(posts, 1):
        slug = it["_slug"]
        try:
            body_html = process_body(it.get("body") or "", slug)
        except Exception as e:
            print(f"  [{i}/{len(posts)}] {slug}: BODY ERROR {e}")
            body_html = "<p>(content could not be imported)</p>"
        cover = download_image(it.get("assetUrl"), f"{slug}--cover", width=1200)
        write_post(it, body_html, cover)
        excerpt = re.sub(r"<[^>]+>", "", it.get("excerpt") or "").strip()
        if not excerpt:
            txt = re.sub(r"<[^>]+>", " ", it.get("body") or "")
            excerpt = re.sub(r"\s+", " ", htmlmod.unescape(txt)).strip()[:160]
        index_rows.append({"slug": slug, "title": it.get("title") or slug,
                           "date": fmt_date(it.get("publishOn")), "excerpt": excerpt[:180],
                           "cover": cover})
        print(f"  [{i}/{len(posts)}] {slug}  (cover: {'yes' if cover else 'no'})")
    write_index(index_rows)
    print(f"Done. Wrote {len(posts)} posts + blog.html. Images in images/blog/.")

if __name__ == "__main__":
    main()
