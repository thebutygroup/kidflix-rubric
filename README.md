# Kidflix Rubric

**What children's movies actually teach, scored — and compared against critical acclaim,
audience love, box office, and adult cinema.**

Live at: **https://analysis.thebutygroup.com/kids-movies/**

**Project status:** 90 films hand-scored and published · scoring pipeline live on
the Claude API (batch, temperature 0, median-of-3) · validation of API scores
against the hand calibration in progress.

![Audience love vs rubric values](docs/kids-movies/charts/scatter_audience.png)

---

## ⚠️ Read this first: subjectivity disclaimer

This is an **opinionated, values-based rubric, not an objective measure of film quality.**
Every dimension — especially the heavily weighted *Inherited Specialness & Wealth*
criterion — encodes a specific parenting concern: that stories teaching children
*"you matter because of what you were born as, and wealth/status is the reward for
goodness"* are a harmful paradigm to absorb young. Reasonable people disagree with
that premise, with the 40% weight it receives, and with individual film scores.

Concretely, this rubric will rank *The Land Before Time* far above *The Lion King*
and put *Cinderella* in F tier despite its craft and cultural stature. That is the
rubric working as designed, not a claim that these are bad films. Scores measure
**what a film's structure teaches**, from one parenting angle — nothing more.

The per-film scores were assigned through structured human judgment (film by film,
dimension by dimension, with written justifications) rather than any automated
process. The `commentary` column preserves the reasoning so every score can be
audited and contested. Contest them — that's the point of publishing the data.

---

## The rubric

<!-- RUBRIC:START -->
**Kidflix Rubric** — Opinionated, values-based rubric measuring what a film's structure teaches a child viewer. Weights must sum to 100.

| Dimension | Weight | Question |
|---|---:|---|
| **Inherited Specialness & Wealth** | 40 | Does the protagonist matter because of what they DO, or what they were BORN AS / INTO — and is wealth/status the story's endorsed reward? Self-made ascension scores as low as inherited ascension: penalise the endorsed outcome, not the pursuit of a livelihood. |
| **Protagonist Agency** | 17 | Do they solve their own story, or is rescue assembled around them? |
| **Emotional Core** | 17 | What is the story about UNDER the plot? |
| **Music** | 10 | Do songs carry the story? |
| **Inclusiveness & Anti-Prejudice** | 10 | Distinguish PASSIVE ABSENCE from ACTIVE HARM. |
| **Romance Framing** | 6 | Is marriage/being-chosen the prize? |

**Tiers:** S ≥ 90 · A ≥ 75 · B ≥ 60 · C ≥ 45 · D ≥ 30 · F < prev

<details><summary><b>Scoring bands per dimension (click to expand)</b></summary>


**Inherited Specialness & Wealth (0–40)**

- `40` — genuinely ordinary protagonist; the story could happen to any kid (anchors: Coco 36, Inside Out 40, Spirited Away 40)
- `35` — modest born-into status doing narrative work (Moana 35, chief's daughter)
- `30` — wealth/status exists but is critiqued as hollow (Encanto 28; critique with residual glorification lands 20-30)
- `20` — born-into greatness, unexamined; no depicted grind (Cars 20)
- `16` — royal-but-burdened; status as isolation, still the source of specialness (Frozen 16)
- `0` — status ascension is the endorsed reward, born or climbed (Cinderella 0, Aladdin 5, The Lion King 4, Goodfellas 6, Scarface 4, Wolf of Wall Street 2)

**Protagonist Agency (0–17)**

- `17` — solves their own story through their own choices (Moana, Anna in Frozen)
- `13` — strong but split, diluted, or destiny-assisted
- `8` — luck-heavy or shared solving
- `0` — passive; rescued at their own climax (Sleeping Beauty 0, Snow White 2, The Little Mermaid 4 — Eric kills the villain)

**Emotional Core (0–17)**

- `17` — deep honest core: grief, identity, belonging, fear-vs-love (Inside Out, Coco, Up, Frozen)
- `13` — real substance, simpler arc (Cars 15)
- `8` — standard adventure/friendship beats
- `0` — core is status, validation, or being chosen (Sleeping Beauty 0)

**Music (0–10)**

- `10` — original songs that carry story (Moana, Frozen, Coco)
- `8` — strong songs with gaps, or performance-central diegetic music
- `5` — score only, or licensed soundtrack (Cars 5, Inside Out 5)
- `0` — actively grating or hollow

**Inclusiveness & Anti-Prejudice (0–10)**

- `10` — inclusion/anti-prejudice IS the lesson; prejudice-as-plot (Zootopia, The Land Before Time, Shrek, Mulan)
- `8` — strong inclusion content, secondary to the main arc (Lilo & Stitch 8)
- `7` — meaningful representation; not the lesson (Moana 7, Soul 7)
- `5` — neutral: nothing taught, no group harmed (non-human casts, Toy Story 5)
- `4` — homogeneous world presented as default; passive exclusion; missed opportunity (Cinderella 4, Sleeping Beauty 4)
- `2` — harmful stereotyping or othering PRESENT in the text (Aladdin 2, The Lion King 2, Scarface 2, The Godfather 2, Wizard of Oz 2)
- `0` — active degradation or othering AS SPECTACLE (Wolf of Wall Street 0, Peter Pan 0)

**Romance Framing (0–6)**

- `6` — absent, or actively subverted (Frozen 6, Brave 6)
- `3` — present but balanced
- `0` — marriage/being-chosen is the prize (Little Mermaid 0 — her voice for a man; Cinderella 0 — identified by shoe size)

</details>
<!-- RUBRIC:END -->

Totals and tiers are always computed by `analysis.py`, never hand-entered. The
block above is generated from `rubric.json` by `python scripts/render_rubric.py
--inject` — edit the JSON, rerun, and the README stays truthful.

## Create your own rubric in five steps

1. **Write down the lessons you care about.** Not genres, not quality — lessons.
   "I don't want stories where wealth is the reward." "I want protagonists who
   solve their own problems." Aim for 4–7 of them; more than that and none of
   them matter.
2. **Weight them to sum to 100.** This is the uncomfortable step and the most
   valuable one: it forces you to say which value wins when they conflict.
3. **Write scoring bands for each dimension** — what full marks looks like, what
   zero looks like, and 2–4 levels between. Every band needs at least one anchor
   film you know cold, with the score you'd give it. Anchors are what make the
   rubric applicable by someone (or something) other than you.
4. **Calibrate on five films before scoring at scale.** Score them by hand
   against your bands. When a result offends your intuition, the fix is almost
   never "change that film's number" — it's "a band is drawn in the wrong
   place," followed by rescoring everything the fix touches. Iterate until five
   films in a row land where your gut agrees.
5. **Pressure-test the edge cases.** Ours: does self-made wealth ascension score
   like inherited? (Yes — the endorsed outcome is what a viewer absorbs.) Does a
   film that merely *lacks* diversity score like one that actively degrades a
   group? (No — passive absence is not active harm.) Your edge cases will be
   different, but you'll know them when a score makes you argue out loud.

## Run the whole thing yourself, end to end

```bash
# 1. Fork/clone and install
git clone https://github.com/thebutygroup/kidflix-rubric.git && cd kidflix-rubric
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 2. Make the rubric yours
#    Edit rubric.json: your dimensions, weights (sum to 100), bands, anchors,
#    tier names. Then refresh the README table:
python scripts/render_rubric.py --inject

# 3. Reset the data to your rubric
#    Give data/movies.csv one column per dimension key plus the metadata
#    columns (title,year,mpaa,<dims...>,rt_critic,rt_audience,revenue_musd,
#    revenue_adj_musd,icon,commentary). Start empty except headers if you're
#    scoring from scratch.

# 4. Score a catalogue via the Claude API (batch = 50% price, overnight)
export ANTHROPIC_API_KEY=sk-ant-...
python scripts/score_movies_api.py --file new_titles.txt --out data/movies.csv
#    The prompt is generated from YOUR rubric.json automatically.
#    Spot-check one film first: add --sync and a single title.

# 5. Fill in the manual columns
#    mpaa, RT critic/audience, revenue (nominal + inflation-adjusted) — sources
#    and caveats in the data dictionary below.

# 6. Build charts + interactive page + deployable site
python analysis.py
python interactive.py
python build_site.py

# 7. Publish
#    GitHub Pages: Settings -> Pages -> branch main, folder /docs.
#    Custom domain: put yours in docs/CNAME (or delete the file) and add a
#    DNS CNAME record at your registrar. Enforce HTTPS once the cert issues.
```

Costs, for planning: scoring ~100 films at 3 runs each is a few hundred batch
requests — well under a dollar on Sonnet. Everything else is free static
hosting.

## The rubric, rendered

| Dimension | Weight | The question it asks | Full marks | Zero |
|---|---:|---|---|---|
| **Inherited Specialness & Wealth** | 40 | Does the protagonist matter for what they do, or what they were born as? Is wealth the endorsed reward? | Genuinely ordinary kid (*Coco*, *Spirited Away*) | Status ascension as the reward, born or climbed (*Cinderella*, *The Lion King*, *Scarface*) |
| **Protagonist Agency** | 17 | Do they solve their own story? | Own choices carry the climax (*Moana*) | Rescued at their own climax (*Sleeping Beauty*) |
| **Emotional Core** | 17 | What is the story about underneath the plot? | Grief, identity, belonging (*Inside Out*, *Up*) | Status, validation, being chosen |
| **Music** | 10 | Do songs carry the story? | Story-carrying original songs (*Moana*) | Grating or hollow |
| **Inclusiveness & Anti-Prejudice** | 10 | Passive absence vs active harm | Prejudice-as-plot, refuted (*Zootopia*) | Degradation as spectacle (*Wolf of Wall Street*, *Peter Pan*'s number) |
| **Romance Framing** | 6 | Is marriage the prize? | Absent or subverted (*Frozen*) | Her voice for a man (*The Little Mermaid*) |

Full band definitions with all anchor scores live in [`rubric.json`](rubric.json) —
that file is the single source of truth; everything below derives from it.

## Create your own rubric

The system is built to run on *your* values, not these. Five steps:

1. **List the lessons you care about** — what you want the stories in your house
   to teach, and what you don't. Aim for 4–7 dimensions; more than that and no
   single one can matter.
2. **Weight them to sum to 100.** This is deliberately uncomfortable: it forces
   you to say what matters *most*. The build fails loudly if they don't sum.
3. **Write scoring bands for each dimension** in `rubric.json`: what full marks
   looks like, what zero looks like, and 2–4 levels between. Every band needs at
   least one **anchor film** you know cold, with the score you'd give it — the
   anchors are what make an LLM apply your bands instead of its own instincts.
4. **Calibrate on five films before scoring at scale.** Score them by hand
   against your bands, then via the API (`--sync` mode, a cent each). Where the
   scores feel wrong, fix the *band wording*, never the individual number, and
   rescore. Two or three iterations is normal — this is the real work, and it's
   genuinely clarifying.
5. **Sense-test the edges.** Ask your rubric hard questions: does self-made
   ascension score like inherited? Does passive absence score like active harm?
   Every inconsistency you find now is a hundred bad scores you prevent later.

Mechanically, a custom rubric means: edit `rubric.json` (dimension keys, `max`
weights, `label`, `question`, `bands`, tier names), give your CSV one column per
dimension key, and run the unchanged pipeline — the analysis, the interactive
chart, and the Claude scoring prompt are all generated from `rubric.json`.

## Run the whole thing yourself

From zero to your own live tier list:

```bash
# 1. get the code
git clone https://github.com/thebutygroup/kidflix-rubric.git && cd kidflix-rubric
python -m venv .venv && source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 2. make it yours
#    edit rubric.json (see "Create your own rubric" above)
#    put your films in a titles file, one "Title,year" per line
cp new_titles.txt my_titles.txt

# 3. score via the Claude API (batch = 50% price, fine for overnight)
export ANTHROPIC_API_KEY=sk-ant-...                  # from console.anthropic.com
python scripts/score_movies_api.py --file my_titles.txt --runs 3 --out data/movies.csv

# 4. fill metadata for the new rows (rt_critic, rt_audience, revenue, mpaa)
#    scores work without it, but films only appear on charts once RT is filled

# 5. build charts + interactive page + deployable site
python analysis.py
python build_site.py

# 6. publish (optional): push to GitHub, enable Pages on /docs,
#    point a CNAME at <username>.github.io  — see Deployment below
```

Cost for a 100-film catalogue at 3 runs each: under a dollar. Time: minutes of
yours, up to a few hours of the batch queue's.

## Datasets

Two deliberately separate files — segment reports never mix; only `compare_*`
outputs combine them:

- `data/movies.csv` — 72 kids/family films (G/PG)
- `data/movies_adult.csv` — 18 adult cult classics / influentials (R/PG-13)

### Data dictionary

| Column | Meaning |
|---|---|
| `title`, `year`, `mpaa` | Film, release year, MPAA rating |
| `wealth, agency, core, music, inclusion, romance` | Rubric dimension scores (max 40/17/17/10/10/6) |
| `rt_critic` | Rotten Tomatoes Tomatometer % (manual snapshot, July 2026) |
| `rt_audience` | RT Popcornmeter % (**approximate** — drifts over time; verify before publishing conclusions) |
| `revenue_musd` | Worldwide lifetime gross, nominal USD millions (approximate) |
| `revenue_adj_musd` | Inflation-adjusted to 2026 USD. Post-1980: CPI multiplier on release year. Pre-1980: published adjusted-gross estimates, because CPI-adjusting lifetime grosses that include decades of re-releases would badly overstate |
| `icon` | Optional path to a point icon (see icon note under Security) |
| `commentary` | JSON: `{"overall", "wealth", "agency", "core", "music", "inclusion", "romance"}` — the written justification per dimension. Source of truth: `scripts/commentary.py` |

RT has no public API and scraping violates their ToS; refresh scores via the
[OMDb API](https://www.omdbapi.com/) (free key, returns RT ratings). Keep the key
in an environment variable — never in the repo.

## Outputs (`python analysis.py`)

Per segment (kids unprefixed, adult as `adult_*`): scored CSV, critic and audience
scatters (quadrant-framed at dataset medians), a zoom on the safe-bet corner, a
rank-vs-rank view (pure ordinal relationship, Spearman ρ in the title), and a
critic-minus-audience divergence CSV.

Cross-segment (`compare_*` only): dimension-profile bar chart, combined rank view,
and the top-10-by-adjusted-revenue absolute scatter.

Interactive (`python interactive.py` → `output/interactive.html`): audience score vs
rubric, kids/adult filterable via legend, hover shows per-dimension scores plus
commentary, and **zoom-adaptive labels** (label budget grows as you zoom in,
highest-rubric films labelled first).

## Scoring via the Claude API (repeatable pipeline)

`scripts/score_movies_api.py` scores films against the rubric through the Claude
API instead of by hand, using the same `ANTHROPIC_API_KEY` env var as any other
Anthropic SDK project. **Every run is a bulk run by default**: requests are
submitted through the Message Batches API, which costs 50% of synchronous pricing
and completes within a 24-hour window (usually much faster) — the right trade for
a task that is never time-sensitive.

```bash
export ANTHROPIC_API_KEY=sk-ant-...

# submit a batch (default runs=3 per film) and poll until done:
python scripts/score_movies_api.py --file new_titles.txt --out data/movies.csv

# or submit and walk away, then collect later:
python scripts/score_movies_api.py --file new_titles.txt --no-wait
python scripts/score_movies_api.py --resume msgbatch_xxx --out data/movies.csv

# synchronous spot check (full price, immediate):
python scripts/score_movies_api.py "The Sandlot" --year 1993 --sync
```

Each submission writes a `batch_<id>.json` manifest (film list, model, prompt
hash) so results can be collected on any machine with the repo and the key.

Repeatability measures (and their honest limits):
- **`temperature=0`** — the most deterministic sampling setting. Anthropic's docs
  note that even at 0, outputs are *not fully deterministic* across calls, so:
- **`--runs N`** (default 3) scores each film N times and keeps the per-dimension **median**,
  reporting the max-min spread per dimension (0 everywhere = perfectly stable).
- **Pinned model**: set `KIDFLIX_MODEL` to a dated snapshot string rather than a
  floating alias; every result records the model used.
- **Prompt hashing**: the rubric prompt (which encodes every band with anchor
  scores from this repo's calibration) is SHA-hashed into each result, so any
  prompt drift between runs is detectable.
- **Model constraint**: `temperature` is rejected (HTTP 400) by Claude Opus 4.7+
  models — use Sonnet or Haiku for this pipeline.
- The model is instructed to refuse (`{"error": "insufficient knowledge"}`)
  rather than guess when it doesn't know a film.

API-scored rows land with empty `mpaa`/RT/revenue columns for manual fill, then
`analysis.py` recomputes totals and tiers as usual. Human-assigned and API-assigned
scores should not be silently mixed in published claims — note provenance.

### Validating the API against the hand calibration

Before trusting the API on new films, rescore the existing catalogue and diff:

```bash
python scripts/make_validation_titles.py     # 90 titles from both datasets
python scripts/score_movies_api.py --file validation_titles.txt --runs 3 --out validation_scores.csv
python scripts/validate_diff.py              # per-dimension deltas + biggest disagreements
```

`validate_diff.py` reports mean absolute delta per dimension, direction of bias,
and the largest per-film disagreements (written to `validation_diff.csv`). Large
systematic deltas mean the rubric prompt needs another anchor example, not that
either score set is "wrong" — the hand scores are the calibration standard.

### Operational workflow (two machines)

Code moves between machines only via git; scoring runs only where the API key
lives. On the scoring box, `run_batch.ps1` wraps the whole loop:
pull → batch-score `new_titles.txt` → commit scores → push. The development
machine pulls, fills `mpaa`/RT/revenue, runs `analysis.py` and `build_site.py`,
and pushes — which, once GitHub Pages is enabled on `/docs`, is also the deploy.

## Deployment

The site is fully static and lives in `docs/`, built by `python build_site.py`
(landing page, interactive chart with self-hosted `plotly.min.js`, all charts and
CSVs, and a `CNAME` file for the custom domain).

**GitHub Pages (recommended):** repo Settings → Pages → deploy from branch `main`,
folder `/docs`, then at your DNS provider add a `CNAME` record for
`analysis.thebutygroup.com` → `<username>.github.io`, and tick **Enforce HTTPS**
once the certificate issues. The chart is then at
`https://analysis.thebutygroup.com/kids-movies/`.

**PythonAnywhere alternative:** upload `docs/` and add a static-files mapping
(URL `/` → the docs directory) on a web app bound to the subdomain (custom domains
need a paid plan; add the CNAME they specify).

## Security & publication notes

- **Keep it static.** No forms, no server code, no cookies — the attack surface is
  essentially the hosting platform's.
- **Supply chain:** `plotly.min.js` is self-hosted and version-pinned rather than
  loaded from a CDN, so a CDN compromise can't inject script into the page. If you
  ever switch back to a CDN, add a Subresource Integrity (SRI) hash.
- **XSS:** the hover cards render the `commentary` JSON as HTML. Today that data is
  first-party and hand-written; if any external source (OMDb, scraped text, user
  submissions) ever flows into `commentary` or `title`, **HTML-escape it on ingest**
  — treat the CSVs as untrusted input to the build.
- **Secrets:** the repo contains none and must stay that way. The OMDb key for the
  refresh script belongs in an env var; `.env` is git-ignored. Check git *history*
  before publishing, not just the working tree.
- **Copyright:** do **not** commit or host movie posters/stills in `icons/` on the
  public site — poster art is copyrighted. Use original icons or leave dots. RT
  scores and revenue figures are facts, cited with attribution and marked
  approximate.
- **Defamation-adjacent caution:** the commentary criticises films, which is
  protected opinion; keep it about the *works*, not living individuals.
- **Subdomain hygiene:** if you ever decommission the Pages site, delete the DNS
  CNAME record too — a dangling CNAME pointing at `github.io` is a subdomain-takeover
  vector.
- **Privacy:** no analytics are included. If you add any, you're serving UK/EU
  visitors — mind consent requirements.

## Repo layout

```
data/movies.csv              kids dataset (source of truth)
data/movies_adult.csv        adult dataset (separate, never mixed into kids reports)
scripts/commentary.py        editable per-dimension commentary -> JSON at build
analysis.py                  scoring, tiers, all static charts, divergence
interactive.py               zoom-adaptive Plotly page
build_site.py                assembles docs/ for deployment
docs/                        deployable static site (GitHub Pages)
output/                      generated artifacts
```

## License & attribution

Scores and commentary are original opinion, released as-is. Rotten Tomatoes scores
© Fandango, quoted as factual data points. Revenue figures approximate, various
public sources. No affiliation with any studio.
