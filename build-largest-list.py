#!/usr/bin/env python3
"""
Regenerates largest-pm-companies.html from data/largest-pm-2026.csv.

WHEN MORE SUBMISSIONS COME IN:
  1) Export the latest responses to data/largest-pm-2026.csv (same columns).
  2) Run:  python3 build-largest-list.py
  3) Commit + push. The page rebuilds with the new ranking, stats, and charts.

No external libraries needed (standard library only).
"""
import csv, re, collections, html, os, json, urllib.request, ssl, concurrent.futures

HERE = os.path.dirname(os.path.abspath(__file__))
CSV  = os.path.join(HERE, "data", "largest-pm-2026.csv")
OUT  = os.path.join(HERE, "largest-pm-companies.html")
JOTFORM_FORM_ID = "240037996931060"
SUBMISSION_YEAR = "2026"   # only include submissions from this year (newest data, top of the JotForm sheet)
PRIOR_YEAR = "2025"        # used for the "Change from 2025" column
NAME_Q  = "Company Name"
DOORS_Q = "Total 3rd party rental doors under management:"
CRANE_Q = "Are you (or is someone on your team) a Crane member?"

# Company website is derived from the submitter's email domain (unless it's a generic mailbox).
GENERIC_EMAIL = {"gmail.com","yahoo.com","outlook.com","hotmail.com","aol.com","icloud.com","comcast.net",
                 "me.com","live.com","msn.com","protonmail.com","att.net","verizon.net","sbcglobal.net","ymail.com"}
def email_domain(email):
    email = (email or "").strip().lower()
    if "@" not in email:
        return ""
    dom = email.rsplit("@", 1)[-1].strip().strip(".")
    return "" if (not dom or dom in GENERIC_EMAIL) else dom

# ---- manual data corrections ----
# Applied on top of the live submissions so they survive the daily auto-refresh.
# Keys are the raw company name, lowercased.
NAME_FIXES = {
    "pmi": "PMI Indianapolis",                  # disambiguate the bare "PMI" (Indianapolis office)
    "pmi midwest": "PMI Midwest",               # capital-I typo in the submission
    "pmi midwest.": "PMI Midwest",
    "pacific shpre property management": "Pacific Shore Property Management",  # 'Shpre' typo
    "turbotenant": 'TurboTenant "Autopilot"',   # use their product name
}
CRANE_MEMBERS_FORCE = {                          # confirmed Crane members (matched by raw or display name)
    "on q property management",
    "stratton vantage property management",
    "colorado realty and property management",
    "auben realty",
    "pacific shore property management",
    "grove",
    "tiner properties, inc.",
    "capvest, llc",
    "darwin homes",
    "grace property management & real estate",
    "gc realty & development",
    "evernest",
}
# 2025 door counts for companies whose name changed year-over-year (so "Change from 2025"
# matches despite the different name). Keyed by the 2026 company name, lowercased.
PRIOR_YEAR_DOORS = {
    "renosy by renters warehouse": 11827,   # was "Renters Warehouse" in 2025
    "jwb": 5300,                            # was "JWB PROPERTY MANAGEMENT" in 2025
}
BOOM_CUSTOMERS = {                               # Boom customers (matched by raw or display name)
    "on q property management",
    "jwb",
    "good life property management",
    "stratton vantage property management",
    "pmi midwest",
    "tiner properties, inc.",
}
EXCLUDE_COMPANIES = {                            # scratched from the list (not residential PM, or opt-out requests still in the form)
    "the storage mall management group",
    "galaxy strategy inc.",                      # opt-out (CA) — still in JotForm
    "rosenbaum realty group",                    # opt-out (AZ) — still in JotForm
    "windermere signature properties",           # duplicate of "Windermere Signature Property Management"
}

def _jotform_key():
    """API key from env (GitHub Action) or a local gitignored .jotform_key file. Never printed/committed."""
    k = os.environ.get("JOTFORM_API_KEY")
    if not k:
        p = os.path.join(HERE, ".jotform_key")
        if os.path.exists(p):
            k = open(p).read().strip()
    return k or None

def _row_from_submission(s):
    """Flatten one JotForm submission into a dict keyed by the question labels (same
    shape as the CSV export), plus a 'Submission Date'."""
    row = {"Submission Date": s.get("created_at", "")}
    for a in (s.get("answers") or {}).values():
        label = (a.get("text") or "").strip()
        ans = a.get("answer")
        if isinstance(ans, dict):    # e.g. full-name {first,last}
            ans = " ".join(str(v) for v in ans.values() if v)
        elif isinstance(ans, list):
            ans = ", ".join(str(v) for v in ans)
        row[label] = "" if ans is None else str(ans)
    return row

def fetch_jotform(key):
    """Pull submissions from the JotForm API. The ranking uses CURRENT-YEAR submissions only,
    but Crane membership is treated as a company attribute drawn from ALL years: recent
    submissions rarely fill in the Crane question, so a company counts as a Crane member if
    ANY of its submissions (any year) said Yes."""
    url = f"https://api.jotform.com/form/{JOTFORM_FORM_ID}/submissions?apiKey={key}&limit=1000"
    data = json.load(urllib.request.urlopen(url, timeout=45)).get("content", [])
    all_rows = [_row_from_submission(s) for s in data]

    crane_by_name = {}
    for r in all_rows:
        nm = (r.get(NAME_Q) or "").strip().lower()
        if nm and (r.get(CRANE_Q) or "").strip().lower().startswith("y"):
            crane_by_name[nm] = True

    # Prior-year (2025) door counts, by company name -> highest doors that year.
    # Used to show "Change from 2025" for companies that submitted both years.
    doors_2025 = {}
    for r in all_rows:
        if (r.get("Submission Date") or "").startswith(PRIOR_YEAR + "-"):
            nm = (r.get(NAME_Q) or "").strip().lower()
            dd = num(r.get(DOORS_Q, ""))
            if nm and dd > 0 and dd > doors_2025.get(nm, 0):
                doors_2025[nm] = dd

    kept, skipped = [], 0
    for r in all_rows:
        if not (r.get("Submission Date") or "").startswith(SUBMISSION_YEAR + "-"):
            skipped += 1
            continue
        nm = (r.get(NAME_Q) or "").strip().lower()
        r[CRANE_Q] = "Yes" if crane_by_name.get(nm) else "No"   # all-year Crane lookup
        r["__doors_2025"] = PRIOR_YEAR_DOORS.get(nm, doors_2025.get(nm))   # override handles name changes
        kept.append(r)
    crane_yes = sum(1 for r in kept if r[CRANE_Q] == "Yes")
    both = sum(1 for r in kept if r.get("__doors_2025"))
    print(f"JotForm: kept {len(kept)} submissions from {SUBMISSION_YEAR}, skipped {skipped} from other years; "
          f"{crane_yes} Crane members; {both} also submitted in {PRIOR_YEAR}.")
    return kept

def load_records():
    """Prefer live JotForm data; fall back to the committed CSV snapshot."""
    key = _jotform_key()
    if key:
        try:
            rows = fetch_jotform(key)
            print(f"Loaded {len(rows)} submissions from the JotForm API.")
            return rows
        except Exception as e:
            print(f"JotForm fetch failed ({e}); falling back to CSV.")
    with open(CSV, newline="") as f:
        rows = list(csv.DictReader(f))
    print(f"Loaded {len(rows)} rows from {os.path.basename(CSV)} (CSV fallback).")
    return rows

STATE_ABBR = {'AL','AK','AZ','AR','CA','CO','CT','DE','FL','GA','HI','ID','IL','IN','IA','KS','KY','LA','ME','MD','MA','MI','MN','MS','MO','MT','NE','NV','NH','NJ','NM','NY','NC','ND','OH','OK','OR','PA','RI','SC','SD','TN','TX','UT','VT','VA','WA','WV','WI','WY','DC'}
STATE_NAME = {'AL':'Alabama','AK':'Alaska','AZ':'Arizona','AR':'Arkansas','CA':'California','CO':'Colorado','CT':'Connecticut','DE':'Delaware','DC':'Washington, D.C.','FL':'Florida','GA':'Georgia','HI':'Hawaii','ID':'Idaho','IL':'Illinois','IN':'Indiana','IA':'Iowa','KS':'Kansas','KY':'Kentucky','LA':'Louisiana','ME':'Maine','MD':'Maryland','MA':'Massachusetts','MI':'Michigan','MN':'Minnesota','MS':'Mississippi','MO':'Missouri','MT':'Montana','NE':'Nebraska','NV':'Nevada','NH':'New Hampshire','NJ':'New Jersey','NM':'New Mexico','NY':'New York','NC':'North Carolina','ND':'North Dakota','OH':'Ohio','OK':'Oklahoma','OR':'Oregon','PA':'Pennsylvania','RI':'Rhode Island','SC':'South Carolina','SD':'South Dakota','TN':'Tennessee','TX':'Texas','UT':'Utah','VT':'Vermont','VA':'Virginia','WA':'Washington','WV':'West Virginia','WI':'Wisconsin','WY':'Wyoming'}
FULLMAP = {'washington':'WA','oregon':'OR','california':'CA','texas':'TX','arizona':'AZ','montana':'MT','wisconsin':'WI','missouri':'MO','indiana':'IN','idaho':'ID','minnesota':'MN','maryland':'MD','georgia':'GA','massachusetts':'MA','tennessee':'TN'}

# ---- location copy-editing (normalize to "City, ST"; fill known missing states) ----
US_FULL = {'alabama':'AL','alaska':'AK','arizona':'AZ','arkansas':'AR','california':'CA','colorado':'CO','connecticut':'CT','delaware':'DE','florida':'FL','georgia':'GA','hawaii':'HI','idaho':'ID','illinois':'IL','indiana':'IN','iowa':'IA','kansas':'KS','kentucky':'KY','louisiana':'LA','maine':'ME','maryland':'MD','massachusetts':'MA','michigan':'MI','minnesota':'MN','mississippi':'MS','missouri':'MO','montana':'MT','nebraska':'NE','nevada':'NV','new hampshire':'NH','new jersey':'NJ','new mexico':'NM','new york':'NY','north carolina':'NC','north dakota':'ND','ohio':'OH','oklahoma':'OK','oregon':'OR','pennsylvania':'PA','rhode island':'RI','south carolina':'SC','south dakota':'SD','tennessee':'TN','texas':'TX','utah':'UT','vermont':'VT','virginia':'VA','washington':'WA','west virginia':'WV','wisconsin':'WI','wyoming':'WY'}
US_FULL_SORTED = sorted(US_FULL.items(), key=lambda x: -len(x[0]))
CA_PROV = {'alberta':'AB','british columbia':'BC','ontario':'ON','quebec':'QC','manitoba':'MB','saskatchewan':'SK','nova scotia':'NS','new brunswick':'NB'}
# Unambiguous large cities -> state, used ONLY when a location has no state at all.
CITY_STATE = {'denver':'CO','indianapolis':'IN','houston':'TX','sacramento':'CA','minneapolis':'MN','anaheim':'CA','newport beach':'CA','las vegas':'NV','lake oswego':'OR','kokomo':'IN','grand rapids':'MI','salt lake city':'UT','chicago':'IL','san antonio':'TX','austin':'TX','phoenix':'AZ','san diego':'CA','cincinnati':'OH','tampa':'FL','oklahoma city':'OK','milwaukee':'WI','madison':'WI','omaha':'NE','tucson':'AZ','mesa':'AZ','gilbert':'AZ','chandler':'AZ','albuquerque':'NM','boise':'ID','spokane':'WA','reno':'NV','missoula':'MT','toledo':'OH','norman':'OK','indianpolis':'IN'}
# Per-company location overrides (lowercased display name) for missing states / data-entry errors we've verified.
LOCATION_FIXES = {
    "marblestone property group":"Chicago, IL",   # was "Southside Chicago"
    "sja property management":"Redmond, WA",       # location field held the company name
    "marchant property management":"Greenville, SC",
    "jwb":"Jacksonville, FL",
    "henderson properites":"Charlotte, NC",
    "sureway property management llc":"Marlton, NJ",
    "home365":"Las Vegas, NV",
}

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

def _clean_city(c):
    c = c.strip(' ,.')
    return c.title() if c else c

def clean_location(name, raw):
    """Copy-edit a HQ location to 'City, ST': uppercase abbreviations, convert full state
    names, fill known-missing states, tidy case. Never guesses an ambiguous state."""
    key = (name or "").strip().lower()
    if key in LOCATION_FIXES:
        return LOCATION_FIXES[key]
    raw = re.sub(r"\s+", " ", (raw or "").strip()).strip(" ,.")
    if not raw:
        return ""
    low = raw.lower(); lownd = low.replace(".", "")
    if 'district of columbia' in low or re.search(r"washington\s*,?\s*d\s*c\b", lownd) or re.search(r"\bd\s*c\b$", lownd):
        return "Washington, DC"
    for prov, ab in CA_PROV.items():
        m = re.search(r"(?<![a-z])" + re.escape(prov) + r"(?![a-z])", low)
        if m:
            city = _clean_city(raw[:m.start()])
            return f"{city}, {ab}, Canada" if city else f"{ab}, Canada"
    state = None; city = raw
    toks = re.split(r"[,\s]+", raw)
    for i in range(len(toks) - 1, -1, -1):
        t = re.sub(r"[^A-Za-z]", "", toks[i]).upper()
        if t in STATE_ABBR:
            state = t; city = " ".join(toks[:i]); break
    if not state:
        for full, ab in US_FULL_SORTED:
            m = re.search(r"(?<![a-z])" + re.escape(full) + r"(?![a-z])", low)
            if m:
                state = ab; city = raw[:m.start()]; break
    if not state:
        ck = re.sub(r"[^a-z ]", "", low).strip()
        if ck in CITY_STATE:
            state = CITY_STATE[ck]; city = raw
    city = _clean_city(city)
    if state and city:
        return f"{city}, {state}"
    if state:
        return state
    return _clean_city(raw)

def norm_soft(s):
    s = (s or "").strip().lower()
    for key,label in [('appfolio','AppFolio'),('rentvine','Rentvine'),('rentmanager','Rent Manager'),
                      ('rent manager','Rent Manager'),('buildium','Buildium'),('propertyware','Propertyware'),
                      ('yardi','Yardi'),('rentec','Rentec Direct'),('hostaway','Hostaway')]:
        if key in s: return label
    return s.title() if s else 'Unknown'

def norm_org(s):
    s = (s or "").strip().lower()
    if 'hybr' in s: return 'Pod-Departmental Hybrid'   # also catches typos like 'hybrib'
    if 'pod' in s or 'squad' in s: return 'Pods (Squads)'
    if 'depar' in s: return 'Departmental'
    if 'potfolio' in s or 'portfolio' in s: return 'Portfolio'
    return s.title() if s else 'Unknown'

# ---- load + clean ----
raw = load_records()

records = []
for d in raw:
    doors = num(d.get('Total 3rd party rental doors under management:', ''))
    raw_name = (d.get('Company Name') or '').strip()
    name = NAME_FIXES.get(raw_name.lower(), raw_name)
    lraw, lname = raw_name.lower(), name.lower()
    if lraw in EXCLUDE_COMPANIES or lname in EXCLUDE_COMPANIES:
        continue
    crane = ((d.get('Are you (or is someone on your team) a Crane member?') or '').strip().lower().startswith('y')
             or lraw in CRANE_MEMBERS_FORCE or lname in CRANE_MEMBERS_FORCE)
    records.append({
        'name': name,
        'raw_name': raw_name,
        'loc': clean_location(name, d.get('Company HQ Location (City, State)', '')),
        'state': state_of(clean_location(name, d.get('Company HQ Location (City, State)', ''))),
        'doors': doors,
        'soft': norm_soft(d.get('Primary Software Used For Property Accounting?', '')),
        'narpm': (d.get('Is your company a member of NARPM?') or '').strip().lower().startswith('y'),
        'crane': crane,
        'boom': lname in BOOM_CUSTOMERS or lraw in BOOM_CUSTOMERS,
        'exec': (d.get('Name + Title of Highest-Ranking Corporate Officer?') or '').strip(),
        'email_domain': email_domain(d.get('Your Email', '')),
        'doors_2025': d.get('__doors_2025'),
        'org': norm_org(d.get('How is your PM Company Organized?', '')),
        'markets': num(d.get('How many markets (metro areas) does your company operate in?', '')),
    })

# keep >=50 doors; dedupe by lowercased name (keep highest doors)
valid = [r for r in records if r['doors'] >= 50]
best = {}
for r in valid:
    k = r['name'].lower().strip()
    if k not in best or r['doors'] > best[k]['doors']:
        best[k] = r
valid = sorted(best.values(), key=lambda x: -x['doors'])
overall_rank = {r['name']: i for i, r in enumerate(valid, 1)}  # name -> position on the full ranking

n = len(valid)
total_doors = sum(r['doors'] for r in valid)
median = sorted(r['doors'] for r in valid)[n//2]
us_states = sorted({r['state'] for r in valid if r['state'] in STATE_NAME})
has_canada = any(r['state'] == 'ON' for r in valid)

def _chart_counts(field, keep=6):
    # Exclude 'Unknown' (older submissions predate these questions); lump a long tail into 'Other'.
    c = [(k, v) for k, v in collections.Counter(r[field] for r in valid).most_common() if k != 'Unknown']
    reported = sum(v for _, v in c)
    if len(c) > keep:
        head = c[:keep]
        tail = sum(v for _, v in c[keep:])
        if tail:
            head.append(('Other', tail))
        c = head
    return c, reported
soft_counts, soft_reported = _chart_counts('soft')
org_counts,  org_reported  = _chart_counts('org')
narpm_n = sum(1 for r in valid if r['narpm'])
biggest = valid[0]
footprint = max((r for r in valid if r['markets'] < 500), key=lambda x: x['markets'])
multi = sum(1 for r in valid if 1 < r['markets'] < 500)

# states with 3-10 clean entries -> mini rankings
by_state = collections.Counter(r['state'] for r in valid)
state_lists = []
for st, c in by_state.most_common():
    if st in STATE_NAME and c >= 3:   # any state with 3+ companies; show its top 10 (no upper cap)
        rows = sorted([r for r in valid if r['state'] == st], key=lambda x: -x['doors'])[:10]
        state_lists.append((st, rows))

def esc(s): return html.escape(s, quote=True)
def comma(x): return f"{x:,}"

WEBSITES_CSV = os.path.join(HERE, "data", "company-websites.csv")

def load_website_rows():
    """Company websites on file: data/company-websites.csv (company_name, website_url, source)."""
    rows = []
    if os.path.exists(WEBSITES_CSV):
        with open(WEBSITES_CSV, newline="") as f:
            rd = csv.reader(f); next(rd, None)
            for row in rd:
                if len(row) >= 2 and row[0].strip() and row[1].strip():
                    rows.append([row[0].strip(), row[1].strip(), (row[2].strip() if len(row) > 2 else "")])
    return rows
WEBSITE_ROWS = load_website_rows()
WEBSITES = {}
for _nm, _url, _src in WEBSITE_ROWS:
    WEBSITES.setdefault(_nm.lower(), _url)

def linked_name(r):
    """Company name, hyperlinked to its website when we have one on file (or auto-discovered)."""
    url = WEBSITES.get((r.get("raw_name") or r["name"]).lower()) or WEBSITES.get(r["name"].lower())
    nm = esc(r["name"])
    if url:
        return f'<a class="co-link" href="{esc(url)}" target="_blank" rel="noopener">{nm}</a>'
    return nm

# ---- real-time website discovery (from the submitter's company-domain email) ----
_SSL = ssl.create_default_context(); _SSL.check_hostname = False; _SSL.verify_mode = ssl.CERT_NONE
def _verify_site(domain):
    """Return the live final URL if the domain serves a real (non-parked) site, else None."""
    for cand in (f"https://www.{domain}", f"https://{domain}"):
        try:
            req = urllib.request.Request(cand, headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15) AppleWebKit/537.36"})
            r = urllib.request.urlopen(req, timeout=8, context=_SSL)
            if r.getcode() >= 400:
                continue
            head = r.read(20000).decode("utf-8", "ignore").lower()
            if any(k in head for k in ("domain is for sale", "buy this domain", "is parked", "this domain may be for sale", "godaddy.com/domainsearch")):
                continue
            return r.geturl().rstrip("/")
        except Exception:
            continue
    return None

def discover_and_cache_websites(companies):
    """For companies not already on file, derive the website from the submitter's
    company-domain email, verify it's live, hyperlink it, and cache it to the CSV so it
    isn't re-checked next build. Verified sites only -> no dead/parked links go live."""
    todo, seen = [], set()
    for r in companies:
        k, rk = r["name"].lower(), (r.get("raw_name") or "").lower()
        if k in WEBSITES or rk in WEBSITES or k in seen:
            continue
        dom = r.get("email_domain")
        if dom:
            todo.append((r["name"], dom)); seen.add(k)
    if not todo:
        return
    capped = todo[:80]  # bound build time; the rest get picked up on later builds
    with concurrent.futures.ThreadPoolExecutor(max_workers=24) as ex:
        results = list(ex.map(lambda t: (t[0], _verify_site(t[1])), capped))
    found = {nm: url for nm, url in results if url}
    if not found:
        print(f"Website discovery: checked {len(capped)} new companies, none verified live.")
        return
    for nm, url in found.items():
        WEBSITES.setdefault(nm.lower(), url)
        WEBSITE_ROWS.append([nm, url, "email-auto"])
    out, kseen = [], set()
    for nm, url, src in WEBSITE_ROWS:          # dedupe by name (existing/manual entries win), sorted
        kk = nm.lower()
        if kk in kseen:
            continue
        kseen.add(kk); out.append([nm, url, src])
    out.sort(key=lambda x: x[0].lower())
    with open(WEBSITES_CSV, "w", newline="") as f:
        w = csv.writer(f); w.writerow(["company_name", "website_url", "source"]); w.writerows(out)
    print(f"Website discovery: linked + cached {len(found)} new website(s) (of {len(capped)} checked).")

discover_and_cache_websites(valid)   # real-time: auto-find + link websites for new companies

# ---- build fragments ----
NAV_LINKS = """      <a href="index.html">About</a>
      <a href="newsletter.html">Newsletter</a>
      <a href="podcast.html">Podcast</a>
      <a href="largest-pm-companies.html" class="active">Largest PM Companies</a>
      <a href="blog.html">Blog</a>
      <a href="report/index.html" target="_blank" rel="noopener">M&amp;A Report</a>
      <a href="peterbot.html">PeterBot</a>
      <a href="products.html">Products</a>"""

FOOT_LINKS = """        <a href="index.html">About</a>
        <a href="newsletter.html">Newsletter</a>
        <a href="podcast.html">Podcast</a>
        <a href="largest-pm-companies.html">Largest PM Companies</a>
        <a href="blog.html">Blog</a>
        <a href="report/index.html" target="_blank" rel="noopener">M&amp;A Report</a>
        <a href="peterbot.html">PeterBot</a>
        <a href="products.html">Products</a>
        <a href="featured.html">Featured</a>
        <a href="contact.html">Contact</a>
        <a href="https://www.linkedin.com/in/pslohmann/" target="_blank" rel="noopener">LinkedIn</a>"""

# podium (top 3)
def pod(r, cls, badge_cls, num_txt):
    return f"""        <div class="pod {cls}">
          <div class="rank-badge {badge_cls} pod-badge"><span class="rb-label">RANK</span><span class="rb-num"><span class="rb-hash">#</span><span class="rb-digit">{num_txt}</span></span></div>
          <div class="pod-doors">{comma(r['doors'])}<small> doors</small></div>
          <div class="pod-co">{linked_name(r)}</div>
          <div class="pod-loc">{esc(r['loc'])}</div>
        </div>"""
podium = "\n".join([
    pod(valid[1], 'second', '', '2'),
    pod(valid[0], 'first', 'gold', '1'),
    pod(valid[2], 'third', '', '3'),
])

# ranking table rows (cap the displayed list at the top 40)
LIST_CAP = 40
# Small person glyph marking the highest-ranking executive (reused in the row + the caption key).
PERSON_SVG = ('<svg class="pico" viewBox="0 0 16 16" aria-hidden="true">'
              '<circle cx="8" cy="5" r="2.6" fill="none" stroke="currentColor" stroke-width="1.3"/>'
              '<path d="M3.2 13c0-2.6 2.1-4.2 4.8-4.2s4.8 1.6 4.8 4.2" fill="none" stroke="currentColor" stroke-width="1.3"/></svg>')
trows = []
for i, r in enumerate(valid[:LIST_CAP], 1):
    top = ' class="top1"' if i == 1 else ''
    NO = '<span class="chip-no">No</span>'
    chip = '<img src="images/narpm-logo.webp" alt="NARPM member" class="yn-logo" />' if r['narpm'] else NO
    crane_chip = '<img src="images/crane-icon.webp" alt="Crane member" class="yn-crane" />' if r['crane'] else NO
    boom_chip = '<img src="images/boom-logo.webp" alt="Boom customer" class="yn-logo" />' if r['boom'] else NO
    soft_txt = esc(r["soft"]) if r["soft"] != "Unknown" else '<span style="color:#9aa5ad">n/a</span>'
    org_txt  = esc(r["org"])  if r["org"]  != "Unknown" else '<span style="color:#9aa5ad">n/a</span>'
    d25 = r.get('doors_2025')
    if not d25:
        change_txt = '<span class="chg-na">N/A</span>'
    else:
        delta = r['doors'] - d25
        if delta > 0:
            change_txt = f'<span class="chg-up">+{comma(delta)}</span>'
        elif delta < 0:
            change_txt = f'<span class="chg-down">-{comma(abs(delta))}</span>'
        else:
            change_txt = '<span class="chg-flat">0</span>'
    exec_line = f'<div class="r-exec">{PERSON_SVG}<span>{esc(r["exec"])}</span></div>' if r.get("exec") else ''
    trows.append(
        f'          <tr{top}>'
        f'<td class="r-rank">{i}</td>'
        f'<td><div class="r-co">{linked_name(r)}</div><div class="r-loc">{esc(r["loc"])}</div>{exec_line}</td>'
        f'<td class="num r-doors">{comma(r["doors"])}</td>'
        f'<td class="chg">{change_txt}</td>'
        f'<td class="hide-sm">{soft_txt}</td>'
        f'<td class="hide-sm">{org_txt}</td>'
        f'<td class="yn">{chip}</td>'
        f'<td class="yn">{crane_chip}</td>'
        f'<td class="yn">{boom_chip}</td>'
        f'</tr>')
table_rows = "\n".join(trows)
shown = min(LIST_CAP, n)

# data bars
def bars(counts, klass_cycle, denom):
    out = []
    top = counts[0][1]
    for idx, (label, c) in enumerate(counts):
        pct = round(100 * c / denom)
        cls = klass_cycle[idx % len(klass_cycle)]
        out.append(
            f'        <div class="databar {cls}">'
            f'<div class="db-top"><span class="db-label">{esc(label)}</span>'
            f'<span class="db-val">{c} &middot; {pct}%</span></div>'
            f'<div class="db-track"><span class="db-fill" style="--w:{round(100*c/top)}%"></span></div></div>')
    return "\n".join(out)
soft_bars = bars(soft_counts, ['', 'c3', 'c4', 'c2'], soft_reported)
org_bars  = bars(org_counts, ['', 'c2', 'c4', 'c3'], org_reported)

# state cards
def top40_note(r):
    rk = overall_rank.get(r['name'])
    return f' <span class="sl-top40">(#{rk} on the top 40)</span>' if rk and rk <= LIST_CAP else ''

scards = []
for st, rows in state_lists:
    items = "\n".join(
        f'            <li><span class="sl-rank">{i}</span><span class="sl-co">{linked_name(r)}{top40_note(r)}</span>'
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
  Data source: live JotForm submissions (form 240037996931060), pulled by build-largest-list.py.
  Auto-refreshes daily via GitHub Actions; also runnable by hand: python3 build-largest-list.py
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
<link rel="stylesheet" href="styles.css?v=8" />
<style>
  /* Boom sponsor presentation (scoped to this page) */
  .presented-by{{ display:inline-flex; align-items:center; gap:12px; margin:-2px 0 14px;
    font-size:clamp(18px,2.2vw,22px); font-weight:400; color:var(--muted); text-decoration:none; }}
  .presented-by img{{ height:clamp(27px,3.3vw,35px); width:auto; display:block; transform:translateY(1px); }}
  .hero-rule{{ width:56px; height:3px; background:var(--primary); border-radius:2px; margin:0 0 18px; }}
  .presented-by:hover{{ text-decoration:none; opacity:.82; }}
  /* Uniform two-line, centered yes/no headers (NARPM / Crane / Boom Customer) */
  .rank-table th.yn-col{{ width:96px; text-align:center; line-height:1.18; vertical-align:bottom;
    padding-left:10px; padding-right:10px; border-left:1px solid var(--line); }}
  .rank-table td.yn{{ text-align:center; padding-left:10px; padding-right:10px; border-left:1px solid var(--line); }}
  /* Org logos: fit each into the same box so the square Crane mark and the wide
     Boom/NARPM wordmarks read at a consistent size. */
  .yn-col .hdr-logo{{ display:block; margin:0 auto 5px; height:24px; width:72px; object-fit:contain; }}
  .yn-col .cust{{ display:block; }}
  td.yn .yn-logo{{ display:block; margin:0 auto; height:30px; width:74px; object-fit:contain; }}
  td.yn .yn-crane{{ display:block; margin:0 auto; height:31px; width:auto; }}  /* cropped icon; ~as tall as NARPM */
  /* Podium rank badges: keep 'RANK', add '#' prefix, drop stars; center content in the shield body */
  .rank-badge{{ height:116px; padding-top:12px; padding-bottom:34px; }}   /* top space for RANK; centers content in the shield body */
  .rank-badge .rb-label{{ font-size:14px; font-weight:800; letter-spacing:.09em; opacity:.85; line-height:1; margin-bottom:5px; display:block; text-align:center; }}
  .rank-badge .rb-num{{ position:relative; display:inline-block; }}   /* digit centers; '#' hangs to its left */
  .rank-badge .rb-hash{{ position:absolute; right:100%; top:50%; transform:translateY(-46%); margin-right:3px; font-size:26px; font-weight:400; opacity:.7; }}
  .state-list .sl-top40{{ font-weight:400; font-size:12px; color:#9aa5ad; white-space:nowrap; }}
  /* Company website links (keep the name's color; underline on hover) */
  .co-link{{ color:inherit; text-decoration:none; }}
  .co-link:hover{{ text-decoration:underline; text-decoration-color:var(--primary); text-underline-offset:2px; }}
  /* Highest-ranking executive: quiet third line under the location, with a small person icon */
  .rank-table .r-exec{{ display:flex; align-items:center; gap:5px; margin-top:2px; color:#8493a0; font-size:12.5px; line-height:1.25; }}
  .rank-table .r-exec .pico{{ width:13px; height:13px; flex:none; color:#a4b0ba; }}
  .exec-key{{ display:inline-flex; align-items:center; gap:5px; white-space:nowrap; color:var(--muted); }}
  .exec-key .pico{{ width:14px; height:14px; flex:none; color:var(--primary-dark); }}
  /* Change from 2025 column */
  .rank-wrap{{ max-width:1200px; }}
  .rank-table th.chg-col{{ text-align:center; line-height:1.18; white-space:nowrap; }}
  .rank-table td.chg{{ text-align:center; white-space:nowrap; font-weight:700; font-variant-numeric:tabular-nums; }}
  .chg-up{{ color:#2f9e6b; }}
  .chg-down{{ color:#c0492f; }}
  .chg-flat{{ color:#9aa5ad; }}
  .chg-na{{ color:#9aa5ad; font-weight:400; }}
  /* reclaim a little room: tighten the roomy Software/Structure columns */
  .rank-table th.hide-sm, .rank-table td.hide-sm{{ padding-left:10px; padding-right:10px; }}
  .boom-sticky{{ position:fixed; right:18px; bottom:18px; z-index:60;
    display:inline-flex; align-items:center; gap:7px; padding:8px 13px;
    background:#fff; border:1px solid var(--line); border-radius:999px;
    box-shadow:0 6px 20px rgba(31,58,77,.16);
    font-size:12px; font-weight:600; letter-spacing:.01em; color:var(--muted); text-decoration:none;
    opacity:0; transform:translateY(12px); pointer-events:none;
    transition:opacity .35s ease, transform .35s ease; }}
  .boom-sticky.show{{ opacity:1; transform:translateY(0); pointer-events:auto; }}
  .boom-sticky img{{ height:18px; width:auto; display:block; }}
  .boom-sticky:hover{{ box-shadow:0 8px 26px rgba(31,58,77,.22); }}
  @media (max-width:600px){{ .boom-sticky{{ right:10px; bottom:10px; padding:7px 11px; }} .boom-sticky span{{ display:none; }} }}
</style>
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
      <a class="presented-by" href="https://www.boompay.app/" target="_blank" rel="noopener">Presented by <img src="images/boom-logo.webp" alt="Boom" /></a>
      <div class="hero-rule" aria-hidden="true"></div>
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
    <div class="wrap rank-wrap">
      <span class="kicker reveal">The Ranking</span>
      <h2 class="h-lead reveal">The full list.</h2>
      <p class="sub reveal" style="margin-bottom:22px;">By third-party doors under management. Self-reported. SFR and small multifamily (under 100 units). <span class="exec-key">{PERSON_SVG} = highest-ranking executive</span></p>
      <div class="table-scroll reveal">
        <table class="rank-table">
          <thead><tr><th class="num">#</th><th>Company</th><th class="num doors-col">Doors</th><th class="chg-col">Change<br>from 2025</th><th class="hide-sm">Software</th><th class="hide-sm">Structure</th><th class="yn-col"><img src="images/narpm-logo.webp" alt="NARPM" class="hdr-logo" /><span class="cust">member</span></th><th class="yn-col"><img src="images/crane-full-logo.webp" alt="Crane" class="hdr-logo" /><span class="cust">member</span></th><th class="yn-col boom-col"><img src="images/boom-logo.webp" alt="Boom" class="hdr-logo" /><span class="cust">Customer</span></th></tr></thead>
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
          <p style="color:var(--muted);font-size:14.5px;margin-bottom:18px;">What the largest operators run their books on. Based on the {soft_reported} companies that reported.</p>
          <div class="databars in">
{soft_bars}
          </div>
        </div>
        <div class="card reveal">
          <h3 style="margin-bottom:6px;">How they're organized</h3>
          <p style="color:var(--muted);font-size:14.5px;margin-bottom:18px;">Structure across the {org_reported} companies that reported.</p>
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
      <p class="sub reveal" style="margin-bottom:22px;">A sample of state-level top 10s. As more companies submit, these fill out and new states get added, the goal is a top 10 for every state (but we'll start with at least 3).</p>
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

<a class="boom-sticky" id="boomSticky" href="https://www.boompay.app/" target="_blank" rel="noopener" aria-label="Presented by Boom">
  <span>Presented by</span><img src="images/boom-logo.webp" alt="Boom" />
</a>

<script src="site.js?v=8"></script>
<script>
(function(){{
  var hero = document.querySelector('.page-hero'),
      badge = document.getElementById('boomSticky');
  if (!hero || !badge) return;
  if (!('IntersectionObserver' in window)) {{ badge.classList.add('show'); return; }}
  new IntersectionObserver(function(entries){{
    entries.forEach(function(e){{ badge.classList.toggle('show', !e.isIntersecting); }});
  }}, {{ threshold: 0 }}).observe(hero);
}})();
</script>
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
