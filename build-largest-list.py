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
# Absolute site origin, for per-state page canonical URLs + JSON-LD. CHANGE TO https://www.peterlohmann.com AT LAUNCH.
SITE_URL = "https://andrewmswensen-hue.github.io/peterlohmann-website"
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
    "movezen, inc",                              # duplicate of "MoveZen Property Management"
    "crofton perdue assoc. inc.",                # removed (also deleted from JotForm)
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

# --- Fastest-growing: rank by % growth vs the same company's 2025 self-report.
# Floor the 2025 base at 300 doors so a tiny company doubling from a small base doesn't dominate.
GROWTH_FLOOR_2025 = 300
_growers = []
for r in valid:
    d25 = r.get('doors_2025')
    if d25 and d25 >= GROWTH_FLOOR_2025 and r['doors'] > d25:
        _growers.append((r, d25, (r['doors'] - d25) / d25))
_growers.sort(key=lambda t: -t[2])
fastest = _growers[:10]

# --- Median door count by PM software / by org structure (groups with enough companies to be meaningful).
def _medians_by(field, min_n=4):
    groups = collections.defaultdict(list)
    for r in valid:
        if r[field] and r[field] != 'Unknown':
            groups[r[field]].append(r['doors'])
    out = []
    for k, arr in groups.items():
        if len(arr) >= min_n:
            arr.sort()
            out.append((k, arr[len(arr)//2], len(arr)))   # (label, median doors, company count)
    out.sort(key=lambda t: -t[1])
    return out
soft_medians = _medians_by('soft')
org_medians  = _medians_by('org')

# states with 3-10 clean entries -> mini rankings
by_state = collections.Counter(r['state'] for r in valid)
state_lists = []
for st, c in by_state.most_common():
    if st in STATE_NAME and c >= 1:   # every US state with at least one company; show its top 10
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
        <a href="https://www.linkedin.com/in/pslohmann/" target="_blank" rel="noopener">LinkedIn</a>
        <a href="financial-interest-disclosure.html">Disclosures</a>"""

FOOT_SOCIAL = """    <div class="foot-social" aria-label="Peter Lohmann on social media">
      <a href="https://www.youtube.com/@peterlohmann" target="_blank" rel="noopener" aria-label="YouTube"><svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M23.5 6.2a3 3 0 0 0-2.1-2.1C19.5 3.5 12 3.5 12 3.5s-7.5 0-9.4.6A3 3 0 0 0 .5 6.2 31 31 0 0 0 0 12a31 31 0 0 0 .5 5.8 3 3 0 0 0 2.1 2.1c1.9.6 9.4.6 9.4.6s7.5 0 9.4-.6a3 3 0 0 0 2.1-2.1A31 31 0 0 0 24 12a31 31 0 0 0-.5-5.8zM9.5 15.6V8.4l6.3 3.6-6.3 3.6z"/></svg></a>
      <a href="https://www.linkedin.com/in/pslohmann/" target="_blank" rel="noopener" aria-label="LinkedIn"><svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M20.5 2h-17A1.5 1.5 0 0 0 2 3.5v17A1.5 1.5 0 0 0 3.5 22h17a1.5 1.5 0 0 0 1.5-1.5v-17A1.5 1.5 0 0 0 20.5 2zM8 19H5v-9h3zM6.5 8.3a1.7 1.7 0 1 1 0-3.5 1.7 1.7 0 0 1 0 3.5zM19 19h-3v-4.4c0-1 0-2.4-1.5-2.4S13 13.4 13 14.5V19h-3v-9h2.9v1.2h.04a3.2 3.2 0 0 1 2.9-1.6c3.1 0 3.7 2 3.7 4.7z"/></svg></a>
      <a href="https://x.com/pslohmann" target="_blank" rel="noopener" aria-label="X (formerly Twitter)"><svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M18.9 2H22l-7.6 8.7L23.3 22h-6.9l-5.4-7-6.2 7H1.7l8.1-9.3L.9 2h7.1l4.9 6.5zM17.7 20h1.9L7.1 4H5.1z"/></svg></a>
      <a href="https://www.facebook.com/lohmann" target="_blank" rel="noopener" aria-label="Facebook"><svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M24 12a12 12 0 1 0-13.9 11.9v-8.4H7v-3.5h3.1V9.4c0-3 1.8-4.7 4.5-4.7 1.3 0 2.7.24 2.7.24v3H15.8c-1.5 0-2 .93-2 1.9v2.2h3.4l-.54 3.5h-2.9v8.4A12 12 0 0 0 24 12z"/></svg></a>
      <a href="https://www.instagram.com/peterlohmann_media/" target="_blank" rel="noopener" aria-label="Instagram"><svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M12 2.2c3.2 0 3.6 0 4.9.07 1.2.05 1.8.25 2.2.42.56.2.96.48 1.38.9.42.42.7.82.9 1.38.17.4.37 1 .42 2.2.06 1.3.07 1.7.07 4.9s0 3.6-.07 4.9c-.05 1.2-.25 1.8-.42 2.2a3.7 3.7 0 0 1-.9 1.38 3.7 3.7 0 0 1-1.38.9c-.4.17-1 .37-2.2.42-1.3.06-1.7.07-4.9.07s-3.6 0-4.9-.07c-1.2-.05-1.8-.25-2.2-.42a3.7 3.7 0 0 1-1.38-.9 3.7 3.7 0 0 1-.9-1.38c-.17-.4-.37-1-.42-2.2-.06-1.3-.07-1.7-.07-4.9s0-3.6.07-4.9c.05-1.2.25-1.8.42-2.2.2-.56.48-.96.9-1.38.42-.42.82-.7 1.38-.9.4-.17 1-.37 2.2-.42C8.4 2.2 8.8 2.2 12 2.2zm0 3.14A6.66 6.66 0 1 0 18.66 12 6.66 6.66 0 0 0 12 5.34zm0 10.98A4.32 4.32 0 1 1 16.32 12 4.32 4.32 0 0 1 12 16.32zm6.9-11.24a1.56 1.56 0 1 1-1.56-1.56 1.56 1.56 0 0 1 1.56 1.56z"/></svg></a>
    </div>"""

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
def id_subline(r):
    # location + highest-ranking exec on ONE line (dot-separated), so the company-name line can run wider
    loc = esc(r["loc"])
    exec_html = f'{PERSON_SVG}<span>{esc(r["exec"])}</span>' if r.get("exec") else ''
    if loc and exec_html:
        return f'<div class="r-sub"><span class="r-loc">{loc}</span><span class="r-dot">&middot;</span><span class="r-exec">{exec_html}</span></div>'
    if loc:
        return f'<div class="r-sub"><span class="r-loc">{loc}</span></div>'
    if exec_html:
        return f'<div class="r-sub"><span class="r-exec">{exec_html}</span></div>'
    return ''
def change_cell(r):
    # shared by the desktop table + the mobile cards
    d25 = r.get('doors_2025')
    if not d25:
        return '<span class="chg-na">N/A</span>'
    delta = r['doors'] - d25
    if delta > 0:
        return f'<span class="chg-up">+{comma(delta)}</span>'
    if delta < 0:
        return f'<span class="chg-down">-{comma(abs(delta))}</span>'
    return '<span class="chg-flat">0</span>'
def yn_badge(on, label):
    return (f'<span class="pmc-tag on"><svg viewBox="0 0 16 16" class="pmc-tick" aria-hidden="true"><path d="M3 8.5l3.2 3.2L13 4.5" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>{label}</span>'
            if on else f'<span class="pmc-tag off">{label}</span>')
NO_CHIP = '<span class="chip-no">No</span>'
def render_rows(subset):
    """(desktop table rows, mobile cards) for a list of companies, ranked 1..N in the given order.
    Shows a subtle national-rank note when a row's national position differs from its rank here
    (i.e. on the per-state pages). Reused by the main top-40 table and every state page."""
    tr, mc = [], []
    for i, r in enumerate(subset, 1):
        natrank = overall_rank.get(r['name'])
        natnote = f'<span class="r-nat">#{natrank} nationally</span>' if (natrank and natrank != i) else ''
        top1 = (natrank == 1)
        topcls = ' class="top1"' if top1 else ''
        cardtop = ' top1' if top1 else ''
        chip = '<img src="images/narpm-logo.webp" alt="NARPM member" class="yn-logo" />' if r['narpm'] else NO_CHIP
        crane_chip = '<img src="images/crane-icon.webp" alt="Crane member" class="yn-crane" />' if r['crane'] else NO_CHIP
        boom_chip = '<img src="images/boom-logo.webp" alt="Boom customer" class="yn-logo" />' if r['boom'] else NO_CHIP
        soft_txt = esc(r["soft"]) if r["soft"] != "Unknown" else '<span style="color:#9aa5ad">n/a</span>'
        org_txt  = esc(r["org"])  if r["org"]  != "Unknown" else '<span style="color:#9aa5ad">n/a</span>'
        soft_m = esc(r["soft"]) if r["soft"] != "Unknown" else 'n/a'
        org_m  = esc(r["org"])  if r["org"]  != "Unknown" else 'n/a'
        tr.append(
            f'          <tr{topcls}>'
            f'<td class="r-rank">{i}</td>'
            f'<td class="r-cell"><div class="r-co">{linked_name(r)}{natnote}</div>{id_subline(r)}</td>'
            f'<td class="num r-doors">{comma(r["doors"])}</td>'
            f'<td class="chg">{change_cell(r)}</td>'
            f'<td class="hide-sm">{soft_txt}</td>'
            f'<td class="hide-sm">{org_txt}</td>'
            f'<td class="yn">{chip}</td>'
            f'<td class="yn">{crane_chip}</td>'
            f'<td class="yn">{boom_chip}</td>'
            f'</tr>')
        mc.append(
            f'        <div class="pmcard{cardtop}">\n'
            f'          <div class="pmc-head">\n'
            f'            <span class="pmc-rank">{i}</span>\n'
            f'            <div class="pmc-id"><div class="pmc-name">{linked_name(r)}{natnote}</div>{id_subline(r)}</div>\n'
            f'            <div class="pmc-doors"><span class="pmc-dn">{comma(r["doors"])}</span><span class="pmc-dl">doors</span></div>\n'
            f'          </div>\n'
            f'          <div class="pmc-meta">\n'
            f'            <div class="pmc-mrow"><span class="pmc-k">Change from 2025</span><span class="pmc-v chg">{change_cell(r)}</span></div>\n'
            f'            <div class="pmc-mrow"><span class="pmc-k">Software</span><span class="pmc-v">{soft_m}</span></div>\n'
            f'            <div class="pmc-mrow"><span class="pmc-k">Structure</span><span class="pmc-v">{org_m}</span></div>\n'
            f'          </div>\n'
            f'          <div class="pmc-tags">{yn_badge(r["narpm"],"NARPM")}{yn_badge(r["crane"],"Crane")}{yn_badge(r["boom"],"Boom customer")}</div>\n'
            f'        </div>')
    return "\n".join(tr), "\n".join(mc)

table_rows, mobile_cards = render_rows(valid[:LIST_CAP])
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

# median-door bars (bar width scaled to the largest median in the set)
def median_bars(items, klass_cycle):
    if not items:
        return '        <p style="color:var(--muted);font-size:14px;margin:0;">Not enough data yet.</p>'
    top = items[0][1]
    out = []
    for idx, (label, med, cnt) in enumerate(items):
        cls = klass_cycle[idx % len(klass_cycle)]
        out.append(
            f'        <div class="databar {cls}">'
            f'<div class="db-top"><span class="db-label">{esc(label)}</span>'
            f'<span class="db-val">{comma(med)} <span class="db-n">({cnt})</span></span></div>'
            f'<div class="db-track"><span class="db-fill" style="--w:{round(100*med/top)}%"></span></div></div>')
    return "\n".join(out)
soft_median_bars = median_bars(soft_medians, ['', 'c3', 'c4', 'c2'])
org_median_bars  = median_bars(org_medians, ['', 'c2', 'c4', 'c3'])

# fastest-growing ranked list
if fastest:
    _gr = []
    for i, (r, d25, pct) in enumerate(fastest, 1):
        _gr.append(
            f'          <li><span class="gl-rank">{i}</span>'
            f'<span class="gl-co">{linked_name(r)}</span>'
            f'<span class="gl-pct">+{round(100*pct)}%</span>'
            f'<span class="gl-detail">{comma(d25)} &rarr; {comma(r["doors"])} doors</span></li>')
    fastest_list = "\n".join(_gr)
else:
    fastest_list = '          <li style="color:var(--muted)">Not enough year-over-year data yet.</li>'

# state cards
def top40_note(r):
    rk = overall_rank.get(r['name'])
    return f' <span class="sl-top40">(#{rk} on the top 40)</span>' if rk and rk <= LIST_CAP else ''

def state_slug(st):
    return STATE_NAME[st].lower().replace(' ', '-')
def state_page_filename(st):
    return f"pm-{state_slug(st)}.html"

scards = []
for st, rows in state_lists:
    items = "\n".join(
        f'            <li><span class="sl-rank">{i}</span><span class="sl-co">{linked_name(r)}{top40_note(r)}</span>'
        f'<span class="sl-doors">{comma(r["doors"])}</span></li>'
        for i, r in enumerate(rows, 1))
    total_in_state = by_state[st]
    more = (f'          <a class="state-more" href="{state_page_filename(st)}">All {total_in_state} in {esc(STATE_NAME[st])} &rarr;</a>\n'
            if total_in_state > len(rows) else
            f'          <a class="state-more" href="{state_page_filename(st)}">Open the {esc(STATE_NAME[st])} page &rarr;</a>\n')
    scards.append(
        f'        <div class="state-card">\n'
        f'          <h3><a class="co-link" href="{state_page_filename(st)}">{esc(STATE_NAME[st])}</a> <span class="st-count">{len(rows)} ranked</span></h3>\n'
        f'          <ul class="state-list">\n{items}\n          </ul>\n'
        f'{more}'
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
<link rel="stylesheet" href="styles.css?v=13" />
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
  /* Location + highest-ranking exec share ONE line (dot-separated), freeing width for the company name */
  .r-sub{{ display:flex; align-items:center; flex-wrap:wrap; gap:6px; margin-top:3px; color:var(--muted); font-size:13px; line-height:1.3; }}
  .r-sub .r-loc{{ color:var(--muted); }}
  .r-sub .r-dot{{ color:#c2ccd4; }}
  .r-sub .r-exec{{ display:inline-flex; align-items:center; gap:5px; color:#8493a0; font-size:12.5px; }}
  .r-sub .r-exec .pico{{ width:13px; height:13px; flex:none; color:#a4b0ba; }}
  .exec-key{{ display:inline-flex; align-items:center; gap:5px; white-space:nowrap; color:var(--muted); }}
  .exec-key .pico{{ width:14px; height:14px; flex:none; color:var(--primary-dark); }}
  /* Change from 2025 column */
  .rank-wrap{{ max-width:1320px; }}   /* ~10% wider table on desktop */
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

  /* Tighten the gap to the right of the rank number */
  .rank-table td.r-rank{{ width:28px; padding-right:2px; }}
  .rank-table thead th:first-child{{ padding-right:2px; }}
  .rank-table td.r-cell{{ padding-left:6px; }}
  .rank-table thead th:nth-child(2){{ padding-left:6px; }}
  /* Bigger company name, closer in size to the door count */
  .rank-table .r-co{{ font-size:18px; line-height:1.2; }}
  /* Faint vertical dividers between every column (matches the NARPM/Crane/Boom borders) */
  .rank-table tbody td + td, .rank-table thead th + th{{ border-left:1px solid var(--line); }}
  .db-n{{ opacity:.6; font-weight:600; }}

  /* Fastest-growing list (two columns on desktop, one on mobile) */
  .grow-list{{ list-style:none; margin:0; padding:0; display:grid; grid-template-columns:1fr 1fr; gap:6px 30px; }}
  .grow-list li{{ display:flex; align-items:baseline; flex-wrap:wrap; gap:10px; padding:9px 0; border-bottom:1px solid var(--line); }}
  .grow-list .gl-rank{{ font-family:var(--display); font-weight:900; color:var(--primary-dark); min-width:20px; font-size:14px; }}
  .grow-list .gl-co{{ font-weight:700; color:var(--navy); flex:1; min-width:0; }}
  .grow-list .gl-pct{{ font-weight:800; color:#2f9e6b; font-variant-numeric:tabular-nums; white-space:nowrap; }}
  .grow-list .gl-detail{{ flex-basis:100%; margin-left:30px; color:var(--muted); font-size:12.5px; font-variant-numeric:tabular-nums; }}

  /* ---- Mobile: swap the horizontal-scroll table for stacked full-width cards ---- */
  .rank-cards{{ display:none; }}
  .pmcard{{ border:1px solid var(--line); border-radius:14px; background:#fff; box-shadow:var(--shadow); padding:16px; }}
  .pmcard.top1{{ border-color:#e4cf93; box-shadow:0 0 0 2px #f4e9c8 inset, var(--shadow); }}
  .pmc-head{{ display:flex; align-items:flex-start; gap:12px; }}
  .pmc-rank{{ font-family:var(--display); font-weight:900; font-size:20px; color:var(--primary-dark); min-width:24px; line-height:1.15; }}
  .pmcard.top1 .pmc-rank{{ color:#bea060; }}
  .pmc-id{{ flex:1; min-width:0; }}
  .pmc-name{{ font-weight:700; color:var(--navy); font-size:17px; line-height:1.22; }}
  .pmc-doors{{ text-align:right; line-height:1.05; flex:none; }}
  .pmc-dn{{ font-family:var(--display); font-weight:900; font-size:20px; color:var(--navy); font-variant-numeric:tabular-nums; display:block; }}
  .pmc-dl{{ font-size:11px; color:var(--muted); text-transform:uppercase; letter-spacing:.05em; }}
  .pmc-meta{{ margin-top:12px; border-top:1px solid var(--line); padding-top:10px; display:flex; flex-direction:column; gap:7px; }}
  .pmc-mrow{{ display:flex; justify-content:space-between; align-items:center; gap:12px; font-size:14px; }}
  .pmc-k{{ color:var(--muted); }}
  .pmc-v{{ color:var(--navy); font-weight:600; text-align:right; }}
  .pmc-tags{{ display:flex; flex-wrap:wrap; gap:7px; margin-top:12px; }}
  .pmc-tag{{ display:inline-flex; align-items:center; gap:5px; font-size:12px; font-weight:700; padding:4px 10px; border-radius:999px; }}
  .pmc-tag.on{{ background:var(--wash); color:var(--primary-dark); }}
  .pmc-tag.off{{ background:#f0f3f6; color:#9aa5ad; border:1px solid #e2e8ee; }}
  .pmc-tick{{ width:12px; height:12px; }}
  @media (max-width:760px){{
    .table-scroll{{ display:none; }}
    .rank-cards{{ display:grid; gap:14px; }}
    .grow-list{{ grid-template-columns:1fr; }}
  }}
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
      <div class="rank-cards reveal" aria-label="Company ranking (mobile)">
{mobile_cards}
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
      <div class="split mt-lg" style="align-items:start;">
        <div class="card reveal">
          <h3 style="margin-bottom:6px;">Median size by software</h3>
          <p style="color:var(--muted);font-size:14.5px;margin-bottom:18px;">Typical (median) door count among companies on each platform. Count in parentheses.</p>
          <div class="databars in">
{soft_median_bars}
          </div>
        </div>
        <div class="card reveal">
          <h3 style="margin-bottom:6px;">Median size by structure</h3>
          <p style="color:var(--muted);font-size:14.5px;margin-bottom:18px;">Typical (median) door count by how the company is organized. Count in parentheses.</p>
          <div class="databars in">
{org_median_bars}
          </div>
        </div>
      </div>
      <div class="card reveal mt-lg grow-card">
        <h3 style="margin-bottom:6px;">Fastest-growing</h3>
        <p style="color:var(--muted);font-size:14.5px;margin-bottom:18px;">Biggest year-over-year jump in self-reported doors, among companies that submitted in both 2025 and 2026 (2025 base of {GROWTH_FLOOR_2025}+ doors).</p>
        <ol class="grow-list">
{fastest_list}
        </ol>
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
      <h2 class="h-lead reveal">A ranking for every state.</h2>
      <p class="sub reveal" style="margin-bottom:22px;">State-level top 10s. Every state with at least one submission is listed, and the smaller ones fill out as more companies add themselves. The goal is a full top 10 for all 50.</p>
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
{FOOT_SOCIAL}
    <p class="disc">The content of this website is for informational purposes only and does not constitute professional advice. I may have consulting agreements with, or financial interests in, companies mentioned on this website. Additionally, some of the links across this site may be affiliate links, meaning I may earn a commission if you make a purchase through those links. Always perform your own due diligence before making any financial or business decisions.</p>
  </div>
</footer>

<a class="boom-sticky" id="boomSticky" href="https://www.boompay.app/" target="_blank" rel="noopener" aria-label="Presented by Boom">
  <span>Presented by</span><img src="images/boom-logo.webp" alt="Boom" />
</a>

<script src="site.js?v=13"></script>
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

# ============================ PER-STATE PAGES ============================
# One real, crawlable/indexable HTML page per US state (SEO + AI-citation foundation;
# the interactive map/modal, Phase 2, will link + progressively enhance these).
THEAD = ('<thead><tr><th class="num">#</th><th>Company</th><th class="num doors-col">Doors</th>'
         '<th class="chg-col">Change<br>from 2025</th><th class="hide-sm">Software</th><th class="hide-sm">Structure</th>'
         '<th class="yn-col"><img src="images/narpm-logo.webp" alt="NARPM" class="hdr-logo" /><span class="cust">member</span></th>'
         '<th class="yn-col"><img src="images/crane-full-logo.webp" alt="Crane" class="hdr-logo" /><span class="cust">member</span></th>'
         '<th class="yn-col boom-col"><img src="images/boom-logo.webp" alt="Boom" class="hdr-logo" /><span class="cust">Customer</span></th></tr></thead>')

# all companies per US state, highest doors first (state pages show everyone, not just the top 10)
state_all = {}
for _st in by_state:
    if _st in STATE_NAME:
        state_all[_st] = sorted([r for r in valid if r['state'] == _st], key=lambda x: -x['doors'])

def render_state_page(st, rows):
    name = STATE_NAME[st]
    url = f"{SITE_URL}/{state_page_filename(st)}"
    st_rows, st_cards = render_rows(rows)
    cnt = len(rows)
    tot = sum(r['doors'] for r in rows)
    med = sorted(r['doors'] for r in rows)[cnt//2] if cnt else 0
    jsonld = json.dumps({
        "@context": "https://schema.org", "@type": "ItemList",
        "name": f"Largest Property Management Companies in {name} (2026)",
        "url": url, "numberOfItems": cnt,
        "itemListElement": [
            {"@type": "ListItem", "position": i,
             "item": {"@type": "Organization", "name": r["name"],
                      "address": {"@type": "PostalAddress", "addressLocality": r["loc"]}}}
            for i, r in enumerate(rows, 1)],
    })
    plural = "company" if cnt == 1 else "companies"
    lead = (f"The largest residential property management companies in {name}, ranked by third-party "
            f"doors under management. {cnt} {plural} listed so far"
            + (f", managing {comma(tot)} doors combined." if cnt > 1 else "."))
    quick = ('' if cnt < 2 else
        '      <div class="stats stats-color g3 reveal mt-md" aria-label="At a glance">\n'
        f'        <div class="stat"><div class="v">{cnt}</div><div class="k">Companies in {esc(name)}</div></div>\n'
        f'        <div class="stat"><div class="v">{comma(round(tot, -2))}+</div><div class="k">Doors under management</div></div>\n'
        f'        <div class="stat"><div class="v">{comma(med)}</div><div class="k">Median doors</div></div>\n'
        '      </div>\n')
    return f"""<!-- GENERATED per-state page. Do not hand-edit; produced by build-largest-list.py. -->
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>The {cnt} Largest Property Management Companies in {esc(name)} (2026) &middot; Peter Lohmann</title>
<meta name="description" content="The largest residential property management companies in {esc(name)} for 2026, ranked by third-party doors under management, with software, structure, and NARPM, Crane, and Boom status." />
<link rel="canonical" href="{url}" />
<link rel="icon" type="image/svg+xml" href="favicon.svg" />
<link rel="icon" type="image/png" sizes="32x32" href="favicon-32.png" />
<link rel="apple-touch-icon" href="favicon.png" />
<link rel="stylesheet" href="styles.css?v=13" />
<script type="application/ld+json">{jsonld}</script>
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
      <a class="back-link" href="largest-pm-companies.html">&larr; All states &amp; the national list</a>
      <span class="kicker">Largest PM Companies &middot; {esc(name)}</span>
      <h1>The Largest Property Management Companies in {esc(name)}</h1>
      <p class="lead">{esc(lead)}</p>
    </div>
  </header>
  <section class="band tight">
    <div class="wrap rank-wrap">
{quick}      <p class="sub reveal" style="margin:22px 0;">By third-party doors under management. Self-reported. SFR and small multifamily (under 100 units). <span class="exec-key">{PERSON_SVG} = highest-ranking executive</span></p>
      <div class="table-scroll reveal">
        <table class="rank-table">
          {THEAD}
          <tbody>
{st_rows}
          </tbody>
        </table>
      </div>
      <div class="rank-cards reveal" aria-label="Company ranking (mobile)">
{st_cards}
      </div>
      <p class="rank-note">{esc(name)}'s ranking updates automatically as companies submit. <a href="https://www.peterlohmann.com/largest-pm-companies" target="_blank" rel="noopener">Add your company &rarr;</a></p>
    </div>
  </section>
  <section class="band tight wash">
    <div class="wrap center">
      <h2 class="h-lead">See the rest of the country.</h2>
      <p class="sub" style="margin:8px auto 18px;">This is the {esc(name)} cut of the national ranking of the largest residential PM companies.</p>
      <a class="btn btn-primary" href="largest-pm-companies.html">The national list &amp; every state</a>
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
{FOOT_SOCIAL}
    <p class="disc">The content of this website is for informational purposes only and does not constitute professional advice. I may have consulting agreements with, or financial interests in, companies mentioned on this website. Additionally, some of the links across this site may be affiliate links, meaning I may earn a commission if you make a purchase through those links. Always perform your own due diligence before making any financial or business decisions.</p>
  </div>
</footer>
<script src="site.js?v=13"></script>
</body>
</html>
"""

_sp = 0
for _st, _rows in state_all.items():
    with open(os.path.join(HERE, state_page_filename(_st)), "w") as f:
        f.write(render_state_page(_st, _rows))
    _sp += 1
print(f"Wrote {_sp} per-state pages.")
print(f"companies={n}  total_doors={total_doors}  median={median}  states={len(us_states)} canada={has_canada}")
print(f"software={soft_counts}")
print(f"org={org_counts}")
print(f"narpm={narpm_n}/{n}  state_lists={[(s,len(r)) for s,r in state_lists]}")
