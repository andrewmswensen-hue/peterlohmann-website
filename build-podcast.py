#!/usr/bin/env python3
"""
Regenerates podcast.html from live sources (re-runnable):
  - YouTube playlist RSS  -> newest episode (hero) + the next 9 (cards), with video embeds
  - iTunes lookup API     -> per-episode Apple Podcasts links (matched by title)
  Spotify links point to the show (per-episode needs their API).

RUN:  python3 build-podcast.py     (then commit + push)

No external libraries (standard library only). Update the IDs below if the show moves.
"""
import urllib.request, json, re, html as htmlmod, datetime, os, difflib

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "podcast.html")
ASSET_V = "13"   # keep in sync with the site's ?v= cache version

YT_PLAYLIST = "PLQihvuykg8UaJqy5CnF2Fok8MDdoNuZ66"
ITUNES_ID = "1554806227"
APPLE_SHOW = "https://podcasts.apple.com/us/podcast/peter-lohmanns-podcast/id1554806227"
SPOTIFY_SHOW = "https://open.spotify.com/show/5BLsN2TwI8mDtIhGoKfnZV?si=be32f2f710c84d67"
YT_CHANNEL = "https://www.youtube.com/@peterlohmann/podcasts"
YT_PLAYLIST_URL = f"https://www.youtube.com/playlist?list={YT_PLAYLIST}"
UA = {"User-Agent": "Mozilla/5.0"}

# Brand logos (inline SVG, currentColor) for the Apple/Spotify/YouTube buttons
APPLE_SVG = '<svg class="pf-ic" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M17.05 12.5c-.03-2.9 2.37-4.3 2.48-4.36-1.35-1.98-3.45-2.25-4.2-2.28-1.79-.18-3.49 1.05-4.4 1.05-.9 0-2.3-1.03-3.79-1-1.95.03-3.75 1.13-4.75 2.88-2.03 3.52-.52 8.73 1.45 11.58.96 1.4 2.11 2.96 3.61 2.9 1.45-.06 2-.94 3.75-.94 1.74 0 2.24.94 3.77.91 1.56-.03 2.55-1.42 3.5-2.82 1.1-1.62 1.56-3.19 1.58-3.27-.03-.02-3.03-1.16-3.06-4.61zM14.13 3.9c.8-.97 1.34-2.32 1.19-3.66-1.15.05-2.54.77-3.37 1.73-.74.85-1.39 2.22-1.22 3.53 1.28.1 2.59-.65 3.4-1.6z"/></svg>'
SPOTIFY_SVG = '<svg class="pf-ic" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.5 17.3a.75.75 0 0 1-1.03.25c-2.82-1.72-6.37-2.11-10.55-1.16a.75.75 0 1 1-.33-1.46c4.57-1.04 8.5-.59 11.66 1.34.35.22.46.68.25 1.03zm1.47-3.27a.94.94 0 0 1-1.29.31c-3.23-1.98-8.16-2.56-11.98-1.4a.94.94 0 1 1-.55-1.8c4.37-1.33 9.8-.68 13.5 1.6.44.27.58.85.32 1.29zm.13-3.4C15.63 8.4 8.5 8.11 5.03 9.17a1.12 1.12 0 1 1-.65-2.15C8.36 5.8 16.24 6.13 20.2 8.48a1.12 1.12 0 1 1-1.17 1.92z"/></svg>'
YT_SVG = '<svg class="pf-ic" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M23.5 6.2a3 3 0 0 0-2.1-2.1C19.5 3.5 12 3.5 12 3.5s-7.5 0-9.4.6A3 3 0 0 0 .5 6.2 31 31 0 0 0 0 12a31 31 0 0 0 .5 5.8 3 3 0 0 0 2.1 2.1c1.9.6 9.4.6 9.4.6s7.5 0 9.4-.6a3 3 0 0 0 2.1-2.1A31 31 0 0 0 24 12a31 31 0 0 0-.5-5.8zM9.5 15.6V8.4l6.3 3.6-6.3 3.6z"/></svg>'
MIC_SVG = '<svg class="k-ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" x2="12" y1="19" y2="22"/></svg>'

# Other shows Peter is part of (cover art pulled from the iTunes API at build time)
SHOWS = [
    {"name": "The Crane Podcast", "itunes": "1896866062",
     "apple": "https://podcasts.apple.com/us/podcast/the-crane-property-management-podcast/id1896866062",
     "spotify": "https://open.spotify.com/show/763FBQuzXqTqJ3mb837WbW?si=e2c101d63d0c46f0",
     "youtube": "https://www.youtube.com/@JoinCrane/videos"},
    {"name": "Lazy Leverage", "itunes": "1777098486",
     "apple": "https://podcasts.apple.com/us/podcast/lazy-leverage/id1777098486",
     "spotify": "https://open.spotify.com/show/763FBQuzXqTqJ3mb837WbW",
     "youtube": "https://www.youtube.com/@LazyLeverageofficial"},
]

FOOT_SOCIAL = """    <div class="foot-social" aria-label="Peter Lohmann on social media">
      <a href="https://www.youtube.com/@peterlohmann" target="_blank" rel="noopener" aria-label="YouTube"><svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M23.5 6.2a3 3 0 0 0-2.1-2.1C19.5 3.5 12 3.5 12 3.5s-7.5 0-9.4.6A3 3 0 0 0 .5 6.2 31 31 0 0 0 0 12a31 31 0 0 0 .5 5.8 3 3 0 0 0 2.1 2.1c1.9.6 9.4.6 9.4.6s7.5 0 9.4-.6a3 3 0 0 0 2.1-2.1A31 31 0 0 0 24 12a31 31 0 0 0-.5-5.8zM9.5 15.6V8.4l6.3 3.6-6.3 3.6z"/></svg></a>
      <a href="https://www.linkedin.com/in/pslohmann/" target="_blank" rel="noopener" aria-label="LinkedIn"><svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M20.5 2h-17A1.5 1.5 0 0 0 2 3.5v17A1.5 1.5 0 0 0 3.5 22h17a1.5 1.5 0 0 0 1.5-1.5v-17A1.5 1.5 0 0 0 20.5 2zM8 19H5v-9h3zM6.5 8.3a1.7 1.7 0 1 1 0-3.5 1.7 1.7 0 0 1 0 3.5zM19 19h-3v-4.4c0-1 0-2.4-1.5-2.4S13 13.4 13 14.5V19h-3v-9h2.9v1.2h.04a3.2 3.2 0 0 1 2.9-1.6c3.1 0 3.7 2 3.7 4.7z"/></svg></a>
      <a href="https://x.com/pslohmann" target="_blank" rel="noopener" aria-label="X (formerly Twitter)"><svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M18.9 2H22l-7.6 8.7L23.3 22h-6.9l-5.4-7-6.2 7H1.7l8.1-9.3L.9 2h7.1l4.9 6.5zM17.7 20h1.9L7.1 4H5.1z"/></svg></a>
      <a href="https://www.facebook.com/lohmann" target="_blank" rel="noopener" aria-label="Facebook"><svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M24 12a12 12 0 1 0-13.9 11.9v-8.4H7v-3.5h3.1V9.4c0-3 1.8-4.7 4.5-4.7 1.3 0 2.7.24 2.7.24v3H15.8c-1.5 0-2 .93-2 1.9v2.2h3.4l-.54 3.5h-2.9v8.4A12 12 0 0 0 24 12z"/></svg></a>
      <a href="https://www.instagram.com/peterlohmann_media/" target="_blank" rel="noopener" aria-label="Instagram"><svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M12 2.2c3.2 0 3.6 0 4.9.07 1.2.05 1.8.25 2.2.42.56.2.96.48 1.38.9.42.42.7.82.9 1.38.17.4.37 1 .42 2.2.06 1.3.07 1.7.07 4.9s0 3.6-.07 4.9c-.05 1.2-.25 1.8-.42 2.2a3.7 3.7 0 0 1-.9 1.38 3.7 3.7 0 0 1-1.38.9c-.4.17-1 .37-2.2.42-1.3.06-1.7.07-4.9.07s-3.6 0-4.9-.07c-1.2-.05-1.8-.25-2.2-.42a3.7 3.7 0 0 1-1.38-.9 3.7 3.7 0 0 1-.9-1.38c-.17-.4-.37-1-.42-2.2-.06-1.3-.07-1.7-.07-4.9s0-3.6.07-4.9c.05-1.2.25-1.8.42-2.2.2-.56.48-.96.9-1.38.42-.42.82-.7 1.38-.9.4-.17 1-.37 2.2-.42C8.4 2.2 8.8 2.2 12 2.2zm0 3.14A6.66 6.66 0 1 0 18.66 12 6.66 6.66 0 0 0 12 5.34zm0 10.98A4.32 4.32 0 1 1 16.32 12 4.32 4.32 0 0 1 12 16.32zm6.9-11.24a1.56 1.56 0 1 1-1.56-1.56 1.56 1.56 0 0 1 1.56 1.56z"/></svg></a>
    </div>"""

def get(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40).read().decode("utf-8", "replace")

def clean_title(t):
    t = htmlmod.unescape(t or "").strip()
    t = re.split(r"\s*\|\s*Peter Lohmann", t)[0]      # drop "| Peter Lohmann's Podcast"
    t = re.split(r"\s*\|\s*", t)[0]                    # drop any trailing "| ..."
    return t.strip()

def fetch_youtube():
    xml = get(f"https://www.youtube.com/feeds/videos.xml?playlist_id={YT_PLAYLIST}")
    entries = re.findall(r"<entry>(.*?)</entry>", xml, re.S)
    eps = []
    for e in entries:
        vid = (re.search(r"<yt:videoId>([^<]+)</yt:videoId>", e) or [None, None])
        vid = re.search(r"<yt:videoId>([^<]+)</yt:videoId>", e)
        title = re.search(r"<media:title>([^<]+)</media:title>", e) or re.search(r"<title>([^<]+)</title>", e)
        pub = re.search(r"<published>([^<]+)</published>", e)
        if not vid:
            continue
        eps.append({"id": vid.group(1), "title": clean_title(title.group(1) if title else ""),
                    "date": pub.group(1)[:10] if pub else ""})
    return eps

def fetch_apple():
    try:
        d = json.loads(get(f"https://itunes.apple.com/lookup?id={ITUNES_ID}&country=US&media=podcast&entity=podcastEpisode&limit=30"))
    except Exception:
        return []
    out = []
    for r in d.get("results", []):
        if r.get("wrapperType") == "podcastEpisode" and r.get("trackViewUrl"):
            out.append({"title": r.get("trackName") or "", "url": r.get("trackViewUrl")})
    return out

def norm(s):
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()

def match_apple(yt_title, apple):
    nt = norm(yt_title)
    best, score = None, 0.0
    for a in apple:
        s = difflib.SequenceMatcher(None, nt, norm(a["title"])).ratio()
        if s > score:
            best, score = a, s
    return best["url"] if best and score >= 0.55 else None

def fmt_date(d):
    try:
        return datetime.datetime.strptime(d, "%Y-%m-%d").strftime("%b ") + str(int(d[8:10])) + ", " + d[:4]
    except Exception:
        return ""

def esc(s):
    return htmlmod.escape(s or "", quote=True)

def platform_btn(kind, url):
    ic = {"apple": APPLE_SVG, "spotify": SPOTIFY_SVG, "youtube": YT_SVG}[kind]
    label = {"apple": "Apple", "spotify": "Spotify", "youtube": "YouTube"}[kind]
    return f'<a class="ep-btn {kind}" href="{esc(url)}" target="_blank" rel="noopener">{ic}{label}</a>'

def itunes_artwork(itunes_id):
    try:
        data = json.loads(get(f"https://itunes.apple.com/lookup?id={itunes_id}"))
        r = data["results"][0]
        return r.get("artworkUrl600") or r.get("artworkUrl100") or ""
    except Exception:
        return ""

def show_card(s):
    art = itunes_artwork(s["itunes"])
    cover = (f'<img class="show-cover" src="{esc(art)}" alt="{esc(s["name"])} cover art" loading="lazy" />'
             if art else f'<div class="show-cover show-cover-fb">{MIC_SVG}</div>')
    return f"""        <div class="show-card">
          {cover}
          <div class="show-body">
            <h3>{esc(s['name'])}</h3>
            <div class="ep-links">
              {platform_btn("apple", s["apple"])}
              {platform_btn("spotify", s["spotify"])}
              {platform_btn("youtube", s["youtube"])}
            </div>
          </div>
        </div>"""

def shows_section():
    cards = "\n".join(show_card(s) for s in SHOWS)
    return f"""  <!-- OTHER SHOWS (blue full-width callout) -->
  <section class="band shows-band">
    <div class="wrap center">
      <span class="kicker kicker-light">{MIC_SVG} Also on the mic</span>
      <h2 class="h-lead" style="color:#fff;">Other shows I'm part of.</h2>
      <p class="sub" style="color:#d7e6f2;max-width:56ch;margin:8px auto 0;">A couple more podcasts I co-host and appear on, with the same three places to listen.</p>
      <div class="show-grid mt-md">
{cards}
      </div>
    </div>
  </section>
"""

def card(ep, apple_url):
    apple = apple_url or APPLE_SHOW
    date = fmt_date(ep["date"])
    return f"""        <div class="ep-card">
          <div class="ep-player" data-id="{ep['id']}" role="button" tabindex="0" aria-label="Play: {esc(ep['title'])}">
            <img src="https://i.ytimg.com/vi/{ep['id']}/hqdefault.jpg" alt="" loading="lazy" />
            <span class="ep-play" aria-hidden="true"></span>
          </div>
          <div class="ep-body">
            {'<div class="ep-date">'+esc(date)+'</div>' if date else ''}
            <h3>{esc(ep['title'])}</h3>
            <div class="ep-links">
              {platform_btn("apple", apple)}
              {platform_btn("spotify", SPOTIFY_SHOW)}
            </div>
          </div>
        </div>"""

def build():
    yt = fetch_youtube()
    apple = fetch_apple()
    if not yt:
        raise SystemExit("No YouTube episodes found; aborting (leaving podcast.html unchanged).")
    hero = yt[0]
    cards = yt[1:10]
    print(f"Hero: {hero['title']} ({hero['id']})")
    cards_html = "\n".join(card(ep, match_apple(ep["title"], apple)) for ep in cards)
    matched = sum(1 for ep in cards if match_apple(ep["title"], apple))
    print(f"Cards: {len(cards)}  (Apple per-episode matches: {matched}/{len(cards)})")
    shows_html = shows_section()

    page = f"""<!-- GENERATED by build-podcast.py (YouTube playlist RSS + iTunes API). Re-run to refresh episodes. -->
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Podcast &middot; Peter Lohmann</title>
<meta name="description" content="Peter Lohmann's Podcast: honest, operator-to-operator conversations about property management. Watch the latest episodes, or listen on Apple Podcasts and Spotify." />
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
      <a href="podcast.html" class="active">Podcast</a>
      <a href="largest-pm-companies.html">Largest PM Companies</a>
      <a href="blog.html">Blog</a>
      <a href="report/index.html" target="_blank" rel="noopener">M&amp;A Report</a>
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
      <span class="kicker">The Podcast</span>
      <h1>Honest, operator-to-operator conversations.</h1>
      <p class="lead">100+ episodes across six seasons. Interviews with fellow business owners and executives about growth, hiring, systems, and the realities of leadership. No fluff, just smart people talking shop.</p>
    </div>
  </header>

  <!-- LATEST EPISODE (newest video) -->
  <section class="band">
    <div class="wrap">
      <div class="split" style="align-items:center;">
        <div>
          <span class="tag tag-warn">Latest episode</span>
          <h2 class="h-lead" style="margin:14px 0 10px;">{esc(hero['title'])}</h2>
          <p class="sub">Fresh conversations drop regularly. Hit play, or catch the full back catalog on the platform of your choice.</p>
          <div class="listen-row mt-sm">
            <a class="btn btn-primary" href="{YT_PLAYLIST_URL}" target="_blank" rel="noopener">Full episode playlist</a>
            <a class="btn btn-yt" href="https://www.youtube.com/@peterlohmann?sub_confirmation=1" target="_blank" rel="noopener">{YT_SVG} Subscribe on YouTube</a>
          </div>
        </div>
        <div>
          <div class="embed-frame video">
            <iframe src="https://www.youtube.com/embed/{hero['id']}" title="{esc(hero['title'])}"
                    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
                    referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe>
          </div>
        </div>
      </div>
    </div>
  </section>

  <!-- RECENT EPISODES (cards) -->
  <section class="band tight">
    <div class="wrap">
      <span class="kicker">Recent Episodes</span>
      <h2 class="h-lead">More to watch and hear.</h2>
      <p class="sub" style="margin-bottom:22px;">Tap any episode to play it right here, or listen on your platform of choice.</p>
      <div class="ep-grid">
{cards_html}
      </div>
      <div class="center mt-lg">
        <a class="btn btn-ghost" href="{YT_CHANNEL}" target="_blank" rel="noopener">See all episodes on YouTube</a>
      </div>
    </div>
  </section>

  <!-- STATS -->
  <section class="band tight wash" aria-label="At a glance">
    <div class="wrap">
      <div class="stats stats-color">
        <div class="stat"><div class="v">100+</div><div class="k">Episodes published</div></div>
        <div class="stat"><div class="v">6</div><div class="k">Seasons and counting</div></div>
        <div class="stat"><div class="v">20k+</div><div class="k">Weekly audience across the platform</div></div>
      </div>
    </div>
  </section>

  <!-- LISTEN ANYWHERE -->
  <section class="band">
    <div class="wrap center">
      <span class="kicker">Listen &amp; Subscribe</span>
      <h2 class="h-lead">Catch it wherever you listen.</h2>
      <p class="sub" style="margin:8px auto 0;">Tune in, turn up the property know-how, and have a blast while you're at it.</p>
      <div class="listen-row mt-md" style="justify-content:center;">
        <a class="listen-btn" href="{APPLE_SHOW}" target="_blank" rel="noopener">{APPLE_SVG} Apple Podcasts</a>
        <a class="listen-btn" href="{SPOTIFY_SHOW}" target="_blank" rel="noopener">{SPOTIFY_SVG} Spotify</a>
        <a class="listen-btn" href="{YT_CHANNEL}" target="_blank" rel="noopener">{YT_SVG} YouTube</a>
      </div>
    </div>
  </section>

{shows_html}
  <!-- SPONSOR -->
  <section class="band tight">
    <div class="wrap">
      <div class="panel orange">
        <span class="tag tag-warn">Want to sponsor?</span>
        <h2 class="h-lead" style="margin-top:14px;">Reach the audience.</h2>
        <p class="sub">Get targeted exposure to over 20,000 property management professionals every week across the newsletter and podcast.</p>
        <a class="btn btn-primary mt-sm" href="contact.html">Explore sponsorship</a>
      </div>
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
        <a href="report/index.html" target="_blank" rel="noopener">M&amp;A Report</a>
        <a href="peterbot.html">PeterBot</a>
        <a href="products.html">Products</a>
        <a href="featured.html">Featured</a>
        <a href="contact.html">Contact</a>
        <a href="https://www.linkedin.com/in/pslohmann/" target="_blank" rel="noopener">LinkedIn</a>
        <a href="financial-interest-disclosure.html">Disclosures</a>
      </nav>
    </div>
{FOOT_SOCIAL}
    <p class="disc">The content of this website is for informational purposes only and does not constitute professional advice. I may have consulting agreements with, or financial interests in, companies mentioned on this website. Additionally, some of the links across this site may be affiliate links, meaning I may earn a commission if you make a purchase through those links. Always perform your own due diligence before making any financial or business decisions.</p>
  </div>
</footer>
<script src="site.js?v={ASSET_V}"></script>
</body>
</html>
"""
    with open(OUT, "w") as f:
        f.write(page)
    print(f"Wrote {OUT}")

if __name__ == "__main__":
    build()
