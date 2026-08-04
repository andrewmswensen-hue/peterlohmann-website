# Header font rollout + copy tightening (log)

When we switched every header to **Bely Display** (Peter's logo serif) site-wide, we also
tightened a few of the longest sentence-style headers, since a display serif rewards short,
punchy headers. This is the running record of those copy edits so nothing changes silently.

## Type change (site-wide)
- All headers (`h1`–`h4`) now render in **Bely Display** via Peter's Adobe Fonts kit, set in the
  shared `styles.css` (one `@import` + a `--serif` token). Applies to every page and every blog post.
- **Carve-outs (deliberately NOT changed):**
  - The **Crane** wordmark on the homepage (`.crane-title`) stays in Inter, it's its own brand mark.
  - The entire **M&A report** (`/report/`, its own React app) is untouched, it doesn't use this stylesheet.
  - All the big **stat / rank / door numbers** stay in Inter (they use the `--display` token, not `--serif`),
    Bely only ships one weight and isn't built for tabular figures.

## Copy tightened (header text changed)
| Page | Before | After | Why |
|---|---|---|---|
| index.html (Resources section) | Resources to improve and grow your PM company. | **Resources to grow your PM company.** | "improve and" was filler; subhead already says "Everything I publish, in one place." |
| newsletter.html (hero) | Real-world insights from inside the trenches of property management. | **Real-world insights from the trenches.** | Nine words is a lot for a display-serif hero; "of property management" is obvious from the page, and "inside the trenches" is redundant with "trenches." |
| products.html (hero) | Tools and help for property management operators. | **Tools for property management operators.** | "and help" added nothing. |
| largest-pm-companies.html (Top 10 by State, from build-largest-list.py) | Where there's enough data, a state ranking. | **A ranking for every state.** | Shorter AND more accurate, we now list every state, not only ones "with enough data." The caveat still lives in the subhead. |

## Headers left as-is on purpose
Short, on-voice headers that already read well and didn't need trimming, e.g. "Let's connect.",
"Let's talk.", "Say hello.", "A few ways I can help.", "Meet PeterBot.", "The three businesses Peter runs."
Blog **post titles** and in-article headings were NOT touched (those are Peter's published, SEO-relevant content).
