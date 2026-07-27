#!/usr/bin/env python3
"""
Regenerates largest-pm-companies.html from data/largest-pm-2026.csv.

WHEN MORE SUBMISSIONS COME IN:
  1) Export the latest responses to data/largest-pm-2026.csv (same columns).
  2) Run:  python3 build-largest-list.py
  3) Commit + push. The page rebuilds with the new ranking, stats, and charts.

No external libraries needed (standard library only).
"""
import csv, re, collections, html, os

HERE = os.path.dirname(os.path.abspath(__file__))
CSV  = os.path.join(HERE, "data", "largest-pm-2026.csv")
OUT  = os.path.join(HERE, "largest-pm-companies.html")

STATE_ABBR = {'AL','AK','AZ','AR','CA','CO','CT','DE','FL','GA','HI','ID','IL','IN','IA','KS','KY','LA','ME','MD','MA','MI','MN','MS','MO','MT','NE','NV','NH','NJ','NM','NY','NC','ND','OH','OK','OR','PA','RI','SC','SD','TN','TX','UT','VT','VA','WA','WV','WI','WY','DC'}
STATE_NAME = {'AL':'Alabama','AZ':'Arizona','CA':'California','CO':'Colorado','DC':'Washington, D.C.','FL':'Florida','GA':'Georgia','ID':'Idaho','IL':'Illinois','IN':'Indiana','KY':'Kentucky','MA':'Massachusetts','MD':'Maryland','MI':'Michigan','MN':'Minnesota','MO':'Missouri','MT':'Montana','NC':'North Carolina','NJ':'New Jersey','NV':'Nevada','NY':'New York','OH':'Ohio','OK':'Oklahoma','OR':'Oregon','SC':'South Carolina','TN':'Tennessee','TX':'Texas','VA':'Virginia','WA':'Washington','WI':'Wisconsin'}
FULLMAP = {'washington':'WA','oregon':'OR','california':'CA','texas':'TX','arizona':'AZ','montana':'MT','wisconsin':'WI','missouri':'MO','indiana':'IN','idaho':'ID','minnesota':'MN','maryland':'MD','georgia':'GA','massachusetts':'MA','tennessee':'TN'}

def num(s):
    m = re.search(r"\d+", (s or "").replace(",",""))
    return int(m.group()) if m else 0

def state_of(loc):
    loc = (loc or "").strip()
    for p in reversed(re.split(r"[,\s]+", loc)):
        pu = p.upper().strip(".")
        if pu in STATE_ABBR: return pu
    low = loc.lower()
    if 'ontario' in low or 'canada' in low: return 'ON'
    if 'd.c' in low or 'washington, d' in low: return 'DC'
    for k,v in FULLMAP.items():
        if k in low: return v
    return '??'

def norm_soft(s):
    s = (s or "").strip().lower()
    for key,label in [('appfolio','AppFolio'),('rentvine','Rentvine'),('rentmanager','Rent Manager'),
                      ('rent manager','Rent Manager'),('buildium','Buildium'),('propertyware','Propertyware'),
                      ('yardi','Yardi'),('rentec','Rentec Direct'),('hostaway','Hostaway')]:
        if key in s: return label
    return s.title() if s else 'Unknown'

def norm_org(s):
    s = (s or "").strip().lower()
    if 'hybrid' in s: return 'Pod-Departmental Hybrid'
    if 'pod' in s or 'squad' in s: return 'Pods (Squads)'
    if 'depar' in s: return 'Departmental'
    if 'potfolio' in s or 'portfolio' in s: return 'Portfolio'
    return s.title() if s else 'Unknown'

# ---- load + clean ----
raw = []
with open(CSV, newline='') as f:
    for d in csv.DictReader(f):
        raw.append(d)

records = []
for d in raw:
    doors = num(d['Total 3rd party rental doors under management:'])
    records.append({
        'name': d['Company Name'].strip(),
        'loc': d['Company HQ Location (City, State)'].strip(),
        'state': state_of(d['Company HQ Location (City, State)']),
        'doors': doors,
        'soft': norm_soft(d['Primary Software Used For Property Accounting?']),
        'narpm': (d['Is your company a member of NARPM?'] or '').strip().lower().startswith('y'),
        'org': norm_org(d['How is your PM Company Organized?']),
        'markets': num(d['How many markets (metro areas) does your company operate in?']),
    })

# keep >=50 doors; dedupe by lowercased name (keep highest doors)
valid = [r for r in records if r['doors'] >= 50]
best = {}
for r in valid:
    k = r['name'].lower().strip()
    if k not in best or r['doors'] > best[k]['doors']:
        best[k] = r
valid = sorted(best.values(), key=lambda x: -x['doors'])

n = len(valid)
total_doors = sum(r['doors'] for r in valid)
median = sorted(r['doors'] for r in valid)[n//2]
us_states = sorted({r['state'] for r in valid if r['state'] in STATE_NAME})
has_canada = any(r['state'] == 'ON' for r in valid)

soft_counts = collections.Counter(r['soft'] for r in valid).most_common()
org_counts  = collections.Counter(r['org'] for r in valid).most_common()
narpm_n = sum(1 for r in valid if r['narpm'])
biggest = valid[0]
footprint = max((r for r in valid if r['markets'] < 500), key=lambda x: x['markets'])
multi = sum(1 for r in valid if 1 < r['markets'] < 500)

# states with 3-10 clean entries -> mini rankings
by_state = collections.Counter(r['state'] for r in valid)
state_lists = []
for st, c in by_state.most_common():
    if st in STATE_NAME and 3 <= c <= 10:
        rows = sorted([r for r in valid if r['state'] == st], key=lambda x: -x['doors'])[:10]
        state_lists.append((st, rows))

def esc(s): return html.escape(s, quote=True)
def comma(x): return f"{x:,}"

# ---- build fragments ----
NAV_LINKS = """      <a href="index.html">About</a>
      <a href="newsletter.html">Newsletter</a>
      <a href="podcast.html">Podcast</a>
      <a href="largest-pm-companies.html" class="active">Largest PM Companies</a>
      <a href="blog.html">Blog</a>
      <a href="https://report.peterlohmann.com/" target="_blank" rel="noopener">M&amp;A Report</a>
      <a href="peterbot.html">PeterBot</a>
      <a href="products.html">Products</a>"""

FOOT_LINKS = """        <a href="index.html">About</a>
        <a href="newsletter.html">Newsletter</a>
        <a href="podcast.html">Podcast</a>
        <a href="largest-pm-companies.html">Largest PM Companies</a>
        <a href="blog.html">Blog</a>
        <a href="https://report.peterlohmann.com/" target="_blank" rel="noopener">M&amp;A Report</a>
        <a href="peterbot.html">PeterBot</a>
        <a href="products.html">Products</a>
        <a href="featured.html">Featured</a>
        <a href="contact.html">Contact</a>
        <a href="https://www.linkedin.com/in/pslohmann/" target="_blank" rel="noopener">LinkedIn</a>"""

# podium (top 3)
def pod(r, cls, badge_cls, hashh, num_txt, stars):
    return f"""        <div class="pod {cls}">
          <div class="rank-badge {badge_cls} pod-badge"><span class="rb-hash">{hashh}</span><span class="rb-num">{num_txt}</span><span class="rb-star">{stars}</span></div>
          <div class="pod-doors">{comma(r['doors'])}<small> doors</small></div>
          <div class="pod-co">{esc(r['name'])}</div>
          <div class="pod-loc">{esc(r['loc'])}</div>
        </div>"""
podium = "\n".join([
    pod(valid[1], 'second', '', 'RANK', '2', '★★'),
    pod(valid[0], 'first', 'gold', 'RANK', '1', '★★★'),
    pod(valid[2], 'third', '', 'RANK', '3', '★'),
])

# ranking table rows (cap the displayed list at the top 40)
LIST_CAP = 40
trows = []
for i, r in enumerate(valid[:LIST_CAP], 1):
    top = ' class="top1"' if i == 1 else ''
    chip = '<span class="chip-yes">Yes</span>' if r['narpm'] else '<span class="chip-no">No</span>'
    trows.append(
        f'          <tr{top}>'
        f'<td class="r-rank">{i}</td>'
        f'<td><div class="r-co">{esc(r["name"])}</div><div class="r-loc">{esc(r["loc"])}</div></td>'
        f'<td class="num r-doors">{comma(r["doors"])}</td>'
        f'<td class="hide-sm">{esc(r["soft"])}</td>'
        f'<td class="hide-sm">{esc(r["org"])}</td>'
        f'<td>{chip}</td>'
        f'</tr>')
table_rows = "\n".join(trows)
shown = min(LIST_CAP, n)

# data bars
def bars(counts, klass_cycle):
    out = []
    top = counts[0][1]
    for idx, (label, c) in enumerate(counts):
        pct = round(100 * c / n)
        cls = klass_cycle[idx % len(klass_cycle)]
        out.append(
            f'        <div class="databar {cls}">'
            f'<div class="db-top"><span class="db-label">{esc(label)}</span>'
            f'<span class="db-val">{c} &middot; {pct}%</span></div>'
            f'<div class="db-track"><span class="db-fill" style="--w:{round(100*c/top)}%"></span></div></div>')
    return "\n".join(out)
soft_bars = bars(soft_counts, ['', 'c3', 'c4', 'c2'])
org_bars  = bars(org_counts, ['', 'c2', 'c4', 'c3'])

# state cards
scards = []
for st, rows in state_lists:
    items = "\n".join(
        f'            <li><span class="sl-rank">{i}</span><span class="sl-co">{esc(r["name"])}</span>'
        f'<span class="sl-doors">{comma(r["doors"])}</span></li>'
        for i, r in enumerate(rows, 1))
    scards.append(
        f'        <div class="state-card">\n'
        f'          <h3>{esc(STATE_NAME[st])} <span class="st-count">{len(rows)} ranked</span></h3>\n'
        f'          <ul class="state-list">\n{items}\n          </ul>\n'
        f'        </div>')
state_cards = "\n".join(scards)

ca_note = " (plus Canada)" if has_canada else ""

# ---- full page ----
page = f"""<!--
  PETER LOHMANN - THE LARGEST PM COMPANIES (2026)
  ============================================================================
  THIS FILE IS GENERATED. Do not hand-edit the data sections.
  To update: replace data/largest-pm-2026.csv, then run  python3 build-largest-list.py
  ============================================================================
-->
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>The Largest PM Companies &middot; Peter Lohmann</title>
<meta name="description" content="Peter Lohmann's 2026 ranking of the largest residential property management companies, with software share, org structure, NARPM membership, and top-10-by-state breakdowns." />
<link rel="icon" type="image/svg+xml" href="favicon.svg" />
<link rel="icon" type="image/png" sizes="32x32" href="favicon-32.png" />
<link rel="apple-touch-icon" href="favicon.png" />
<link rel="stylesheet" href="styles.css?v=5" />
</head>
<body>

<a class="skip" href="#main">Skip to content</a>

<nav class="top" aria-label="Primary">
  <div class="bar">
    <a class="brand" href="index.html">Peter <span>Lohmann</span></a>
    <button class="nav-toggle" aria-expanded="false" aria-controls="navlinks">Menu</button>
    <div class="links" id="navlinks">
{NAV_LINKS}
    </div>
    <a class="btn btn-navy btn-sm cta" href="contact.html">Contact</a>
  </div>
</nav>

<main id="main">

  <header class="page-hero">
    <div class="wrap">
      <div class="ticks" aria-hidden="true"><i></i><i></i><i></i></div>
      <span class="kicker">Industry Research &middot; 2026</span>
      <h1>The Largest Property Management Companies</h1>
      <p class="lead">A self-reported ranking of the largest residential property management companies, plus what the data says about software, structure, and how the best operators are built. Submissions are still open, so this list keeps growing.</p>
    </div>
  </header>

  <!-- TOP 3 PODIUM -->
  <section class="band">
    <div class="wrap">
      <span class="kicker reveal">The Top of the List</span>
      <h2 class="h-lead reveal">The three largest, right now.</h2>
      <div class="podium reveal mt-md">
{podium}
      </div>
    </div>
  </section>

  <!-- FULL RANKING -->
  <section class="band tight">
    <div class="wrap">
      <span class="kicker reveal">The Ranking</span>
      <h2 class="h-lead reveal">The full list.</h2>
      <p class="sub reveal" style="margin-bottom:22px;">By third-party doors under management. Self-reported. SFR and small multifamily (under 100 units).</p>
      <div class="table-scroll reveal">
        <table class="rank-table">
          <thead><tr><th class="num">#</th><th>Company</th><th class="num doors-col">Doors</th><th class="hide-sm">Software</th><th class="hide-sm">Structure</th><th>NARPM member?</th></tr></thead>
          <tbody>
{table_rows}
          </tbody>
        </table>
      </div>
      <p class="rank-note">Showing the top {shown} of {n} companies submitted so far. Something look off, or want to be added? Submissions are open through the end of the month.</p>
    </div>
  </section>

  <!-- BY THE NUMBERS -->
  <section class="band wash">
    <div class="wrap">
      <span class="kicker reveal">By the Numbers</span>
      <h2 class="h-lead reveal">What the data says.</h2>
      <div class="stats stats-color g4 reveal mt-md" aria-label="At a glance">
        <div class="stat"><div class="v">{n}</div><div class="k">Companies ranked so far</div></div>
        <div class="stat"><div class="v">{comma(round(total_doors, -2))}+</div><div class="k">Doors under management</div></div>
        <div class="stat"><div class="v">{len(us_states)}</div><div class="k">U.S. states on the list{ca_note}</div></div>
        <div class="stat"><div class="v">{comma(median)}</div><div class="k">Median doors per company</div></div>
      </div>
      <div class="split mt-lg" style="align-items:start;">
        <div class="card reveal">
          <h3 style="margin-bottom:6px;">Accounting software</h3>
          <p style="color:var(--muted);font-size:14.5px;margin-bottom:18px;">What the largest operators run their books on.</p>
          <div class="databars in">
{soft_bars}
          </div>
        </div>
        <div class="card reveal">
          <h3 style="margin-bottom:6px;">How they're organized</h3>
          <p style="color:var(--muted);font-size:14.5px;margin-bottom:18px;">Team structure across the list.</p>
          <div class="databars in">
{org_bars}
          </div>
        </div>
      </div>
      <div class="fact-grid mt-lg stagger">
        <div class="fact"><div class="f-num">{round(100*narpm_n/n)}%</div><h3>Are NARPM members</h3><p>{narpm_n} of {n} companies belong to the National Association of Residential Property Managers.</p></div>
        <div class="fact"><div class="f-num">{comma(biggest['doors'])}</div><h3>Largest single portfolio</h3><p>{esc(biggest['name'])} in {esc(biggest['loc'])} tops the list.</p></div>
        <div class="fact"><div class="f-num">{footprint['markets']}</div><h3>Widest footprint</h3><p>{esc(footprint['name'])} operates across the most metro markets of anyone on the list.</p></div>
        <div class="fact"><div class="f-num">{soft_counts[0][1]}</div><h3>Run {esc(soft_counts[0][0])}</h3><p>Roughly {round(100*soft_counts[0][1]/n)}% of the list uses it, more than every other platform combined.</p></div>
        <div class="fact"><div class="f-num">{multi}</div><h3>Operate in multiple markets</h3><p>The rest run deep in a single metro rather than spreading across regions.</p></div>
        <div class="fact"><div class="f-num">{comma(round(total_doors/n))}</div><h3>Average portfolio</h3><p>The typical company on the list manages this many third-party doors.</p></div>
      </div>
    </div>
  </section>

  <!-- TOP 10 BY STATE -->
  <section class="band">
    <div class="wrap">
      <span class="kicker reveal">Top 10 by State</span>
      <h2 class="h-lead reveal">Where there's enough data, a state ranking.</h2>
      <p class="sub reveal" style="margin-bottom:22px;">A sample of state-level top 10s. As more companies submit, these fill out and new states get added, the goal is a top 10 for every state.</p>
      <div class="state-grid reveal">
{state_cards}
      </div>
    </div>
  </section>

  <!-- GROW THE LIST -->
  <section class="band tight wash">
    <div class="wrap">
      <div class="cta-final">
        <span class="tag tag-warn" style="margin-bottom:14px;display:inline-block;">Help me grow it</span>
        <h2>Get your company on the list.</h2>
        <p>The goal is the largest 40+ PM companies in the U.S., and a top 10 for every state. If you run a qualifying company, add yours. It's free, and it's the fastest way to benchmark against your peers.</p>
        <p style="color:#f0a882;font-weight:700;">Submissions are open through the end of the month.</p>
        <a class="btn btn-primary" href="https://www.peterlohmann.com/largest-pm-companies" target="_blank" rel="noopener">Submit your PM company</a>
      </div>
    </div>
  </section>

  <!-- METHODOLOGY -->
  <section class="band">
    <div class="wrap">
      <div class="split">
        <div>
          <span class="kicker">Why It Matters</span>
          <h2 class="h-lead">Benchmarks for a fragmented industry.</h2>
          <p class="sub">Property management is famously fragmented. Whether you manage 200 doors or 20,000, seeing how the largest operators are built gives you a real benchmark to measure against, and a map of where the ceiling actually is.</p>
        </div>
        <div>
          <h3 style="font-size:19px;margin-bottom:10px;">Methodology</h3>
          <ul class="feat">
            <li>Only third-party managed doors are counted</li>
            <li>Figures are self-reported</li>
            <li>Covers SFR and small multifamily only (under 100 units)</li>
            <li>No HOAs, no big multifamily, no mixed portfolios</li>
            <li>Data is refreshed as new submissions come in</li>
          </ul>
        </div>
      </div>
    </div>
  </section>

</main>

<footer class="site">
  <div class="wrap">
    <div class="foot-grid">
      <div class="brand" style="font-weight:700;color:var(--navy);">Peter <span style="color:var(--primary);">Lohmann</span></div>
      <nav class="foot-links" aria-label="Footer">
{FOOT_LINKS}
      </nav>
    </div>
    <p class="disc">The content of this website is for informational purposes only and does not constitute professional advice. I may have consulting agreements with, or financial interests in, companies mentioned on this website. Additionally, some of the links across this site may be affiliate links, meaning I may earn a commission if you make a purchase through those links. Always perform your own due diligence before making any financial or business decisions.</p>
  </div>
</footer>

<script src="site.js?v=5"></script>
</body>
</html>
"""

with open(OUT, "w") as f:
    f.write(page)

print(f"Wrote {OUT}")
print(f"companies={n}  total_doors={total_doors}  median={median}  states={len(us_states)} canada={has_canada}")
print(f"software={soft_counts}")
print(f"org={org_counts}")
print(f"narpm={narpm_n}/{n}  state_lists={[(s,len(r)) for s,r in state_lists]}")
