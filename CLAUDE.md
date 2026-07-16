# Peter Lohmann Website

## What we're building
A clean, multi-page personal website for **peterlohmann.com**, rebuilt to match the
look and feel of the 2026 PLM Media Kit (`Projects/PLM media kit/index.html`). It copies
the content that's currently on the live Squarespace site but reorganizes it to be far
cleaner and less text-heavy, especially the Home/About page.

Static HTML/CSS only. No framework, no build step. Opens in any browser and can be hosted
anywhere (Squarespace embed, GitHub Pages, Netlify, etc.).

## Pages (mirrors the live site's nav)
1. `index.html` ............ Home / About  ✅ built
2. `newsletter.html` ....... Newsletter
3. `podcast.html` .......... Podcast
4. `largest-pm-companies.html`  The Largest PM Companies
5. `blog.html` ............. Blog (cards linking to live posts)
6. `ma-report.html` ........ Property Management M&A Report
7. `peterbot.html` ......... PeterBot
8. `products.html` ......... Products
9. `contact.html` .......... Contact

## How it's structured (plain English)
- **`styles.css`** — ONE shared stylesheet for the whole site. Change a color, font, or
  spacing here and it updates every page at once. Design tokens (colors) live at the very
  top in the `:root` block.
- **`site.js`** — ONE shared script. Handles the scroll-in animations and the mobile menu.
- Every page links to those two files and shares the same top nav + footer.
- **`images/`** — photos (currently `peter-headshot.jpg`). `favicon.*` in the root.

## How to update (no coding)
- **Change the site's look** → edit `styles.css`.
- **Swap the headshot** → replace `images/peter-headshot.jpg`.
- **Edit page words** → open that page's `.html` file; text sits between the tags, plainly.
- **Swap a link** → search the page for `SWAP:` comments marking the spots to update.

## Design system (media-kit colors + 2026 pmtrends-inspired refresh)
- Primary steel blue `#2C7CB0`, navy text `#1F3A4D`, orange accent `#E0703C`, light blue-gray
  washes, rounded white cards. Extra tints for tasteful color pops: `--sky`, `--gold`, `--mint`.
- Type: **Inter** (Google Fonts @import in styles.css) with heavy 800/900 headings, tight tracking.
- Signature touches (all in styles.css): slim tricolor accent line under the nav (`nav.top::after`),
  hero tick marks (`.ticks`), standout hero headshot (blob + accent dot + white ring + floating
  `.hero-badge`), colorful stat tiles (`.stats-color`), modern rank badges (`.rank-badge`),
  blog featured banner (`.feature-post`) + 3-up image cards (`.post-card` / `.ph-img`).

## Live embeds (third-party, fine on GitHub Pages)
- Newsletter: Beehiiv subscribe iframe + subscribe URL https://peter.beehiiv.com/subscribe
- Podcast: latest-episode YouTube embed (video id hardcoded in podcast.html, currently zqyXW_Sy1Kw,
  update by hand when a new episode airs), plus Apple/Spotify/YouTube links + full playlist
- Largest PM Companies: live Google Sheets pubhtml iframe (edit the sheet to update the list)
- PeterBot: Delphi widget (scripts inside the embed section; Delphi injects #delphi-container there)

## Interactive features
Per Andrew's decision, buttons for PeterBot chat, Products checkout, the M&A Report purchase,
and individual blog posts **link out to the existing live peterlohmann.com pages** so nothing
functional breaks. These are marked in each page.

## Writing rules
- **No em dashes or en dashes** anywhere (Andrew's standing rule). Use commas, parentheses,
  hyphens, colons, or a sentence split instead.

## Preview locally
From this folder: `python3 -m http.server 8747`, then open http://localhost:8747/index.html
(the `file://` path is blocked by the browser preview, so use the local server).

## Status
- 2026-07-16: ALL 9 pages built (About, Newsletter, Podcast, Largest PM Companies, Blog,
  M&A Report, PeterBot, Products, Contact). Shared styles.css + site.js in place.
- Blog is structured for individual posts: index at blog.html, posts live in blog/ (one .html
  each, named by slug). One example post transferred: blog/vendor-rebates-are-kickbacks.html.
  Remaining blog cards still link to the live peterlohmann.com posts until transferred.
- SWAP points still open (search "SWAP:" in each file): newsletter subscribe URL, podcast
  platform links, store/checkout links, M&A report purchase link, PeterBot chat link,
  contact media-kit + Jotform links. Most currently point to the live peterlohmann.com pages.
