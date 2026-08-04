# Largest PM Companies — pre-launch audit log

Running record of every **manual data decision and page change** for `largest-pm-companies.html`,
so we can do a final review before go-live (target: the 18th). The list itself rebuilds from live
JotForm every day; everything below is a **human override** layered on top (all lives in
`build-largest-list.py`). Audit each one — a wrong override is the main risk on a public list.

---

## 1. Companies removed (EXCLUDE_COMPANIES) — verify each should be off the list
| Company | Reason |
|---|---|
| The Storage Mall Management Group | Not residential PM (storage units); was inflating the top of the list |
| Galaxy Strategy Inc. (Stockton, CA) | Opt-out request. NOTE: name we were given was "Galaxy PM Ink" — confirm this is the same company |
| Rosenbaum Realty Group (Gilbert, AZ) | Opt-out request (Daniel@rosenbaumrealtygroup.com) |
| Windermere Signature Properties (1,500) | Duplicate of "Windermere Signature Property Management" (1,558, the real one) |
| MoveZen, Inc | Duplicate of "MoveZen Property Management" (the real one) |
| Crofton Perdue Assoc. Inc. (Pittsford, NY) | Removed at request; also deleted from JotForm |

## 2. Name corrections (NAME_FIXES) — display name differs from what was submitted
| Submitted | Shown as | Why |
|---|---|---|
| PMI | PMI Indianapolis | Disambiguate the bare "PMI" |
| PMI MIdwest | PMI Midwest | Capital-I typo |
| Pacific Shpre Property Management | Pacific Shore Property Management | "Shpre" typo |
| TurboTenant | TurboTenant "Autopilot" | Use their product name (per Andrew) |

## 3. Crane members (CRANE_MEMBERS_FORCE) — flagged Crane despite the form
Confirmed by Andrew/Peter or a prior submission: On Q, Stratton Vantage, Colorado Realty & Property
Management, Auben Realty, Pacific Shore, Grove, Tiner Properties, CapVest LLC, Darwin Homes,
Grace Property Management & Real Estate, GC Realty & Development, Evernest.
*(Others show Crane from their own form answer — not listed here.)*

## 4. Boom customers (BOOM_CUSTOMERS) — sponsor "Boom Customer" = Yes
On Q, JWB, Good Life, Stratton Vantage, PMI Midwest, Tiner Properties.
*(Everyone else shows "No" until the customer list grows.)*

## 5. "Change from 2025" overrides (PRIOR_YEAR_DOORS) — name changed year-over-year
| 2026 company | 2025 doors used | 2025 name |
|---|---|---|
| Renosy by Renters Warehouse | 11,827 | "Renters Warehouse" |
| JWB | 5,300 | "JWB PROPERTY MANAGEMENT" |
*(Watch: Evernest matched on its own name → shows a large −8,985; from its own 2025 submission. Sanity-check before launch.)*

## 6. Location clean-ups
- Per-company fixes (LOCATION_FIXES): Marblestone → Chicago, IL · SJA → Redmond, WA · Marchant → Greenville, SC · JWB → Jacksonville, FL · Henderson Properites → Charlotte, NC · Sureway → Marlton, NJ · Home365 → Las Vegas, NV.
- Typos/unresolved cities added to the city→state map: Indianpolis → IN · Toledo → OH · Norman → OK.
- One still ambiguous and left blank: **"Anderson"** (no state given — could be IN or SC). Decide before launch.
- All locations auto-normalize to "City, ST" (case, full names, etc.).

## 7. Company websites
- Auto-discovered from each submitter's company-domain email, verified live, and cached to
  `data/company-websites.csv`. Verified-only, so no dead/parked links.
- **Manually researched/corrected** (source `verified-search` / `user-provided` in the CSV) — worth a spot-check:
  West USA → westusa.com/property-management.html · 360 Management → 360managementservices.com ·
  Neighborhood PM → neighborhoodpm.com · Choice Properties → irentforyoucharlotte.com · Darwin Homes → darwinhomes.com ·
  Bridgestream Property Management → bridgestreampropertymanagement.com (was submitted as "Michael Mefferd"; now correctly named in the form).
- ~6% with generic emails (gmail, etc.) have no auto-link; can be researched on request.
- **WJL HomeServices** (wjlhomeservices.com) has an expired SSL cert — decide keep/unlink before launch.

## 8. Structural / feature changes to the page (for review)
- Presented-by-Boom hero + sticky corner badge; "Boom Customer" column.
- "Change from 2025" column; NARPM/Crane/Boom shown as logos; highest-ranking-exec third line (person icon + caption key).
- Company names hyperlink to their websites.
- Top-10-by-State shows every US state with at least one submission (44 currently), even 1-2 company states.
- Year filter: 2026 submissions only (SUBMISSION_YEAR). Daily auto-refresh via GitHub Action.
- Headers now render in **Bely Display** (site-wide serif; all the stat/rank/door numbers stay in Inter). The "Top 10 by State" header was tightened: "Where there's enough data, a state ranking." → "A ranking for every state." (see HEADER-COPY-CHANGES.md).
- **Table redesign (Aug):** ~10% wider on desktop; tighter rank-number spacing; larger company name; faint vertical dividers between all columns; location + highest-ranking exec now share one line (was stacked). Dedicated **mobile view**: horizontal-scroll table is replaced by stacked full-width cards (one per company) that still show doors, YoY change, software, structure, and NARPM/Crane/Boom status.
- **Per-state pages + interactive map (Aug):** 46 real crawlable pages (`pm-<state>.html`), one per state with submissions, each with its own title/meta, canonical URL, JSON-LD `ItemList`, quick stats, and the full rich table/cards. An interactive **tile-grid map** (choropleth by company count) sits atop the "Top 10 by State" band; clicking a state opens a modal (top 10 + NARPM/Crane/Boom badges + link to the full state page). ⚠️ **LAUNCH TODO:** `SITE_URL` in build-largest-list.py is set to the github.io origin for canonical/JSON-LD, **change it to `https://www.peterlohmann.com` at launch**. Also add a sitemap.xml listing the state pages (not yet done).
- **New "What the data says" cuts:** Median door count by software; median by org structure; and a **Fastest-growing** top-10. ⚠️ *Fastest-growing methodology to confirm before launch:* ranked by **% growth** vs the company's own 2025 self-report, filtered to a **2025 base of 300+ doors** (keeps tiny-base noise out). Current top 10 looks clean (JWB +40%, On Q +29%, Darwin +24%, …). If Peter prefers **absolute doors added** instead of %, it's a one-line change. Same year-over-year data caveats as the "Change from 2025" column apply (self-reported, name-matched).

---

## Removals process (reference)
- Peter **deletes** opt-outs from JotForm → they drop off automatically on the next refresh.
- If an opt-out is still in the form, it goes in EXCLUDE_COMPANIES (section 1) to remove it now.
- A deletion check (site vs live JotForm) can be run anytime to catch anything stale.
