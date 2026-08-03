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
  Neighborhood PM → neighborhoodpm.com · Choice Properties → irentforyoucharlotte.com · Darwin Homes → darwinhomes.com.
- ~6% with generic emails (gmail, etc.) have no auto-link; can be researched on request.
- **WJL HomeServices** (wjlhomeservices.com) has an expired SSL cert — decide keep/unlink before launch.

## 8. Structural / feature changes to the page (for review)
- Presented-by-Boom hero + sticky corner badge; "Boom Customer" column.
- "Change from 2025" column; NARPM/Crane/Boom shown as logos; highest-ranking-exec third line (person icon + caption key).
- Company names hyperlink to their websites.
- Top-10-by-State now shows every state with 3+ companies (was silently capped/dropping states like UT, PA).
- Year filter: 2026 submissions only (SUBMISSION_YEAR). Daily auto-refresh via GitHub Action.

---

## Removals process (reference)
- Peter **deletes** opt-outs from JotForm → they drop off automatically on the next refresh.
- If an opt-out is still in the form, it goes in EXCLUDE_COMPANIES (section 1) to remove it now.
- A deletion check (site vs live JotForm) can be run anytime to catch anything stale.
