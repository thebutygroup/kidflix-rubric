"""
score_movies_api.py — repeatable rubric scoring via the Claude API.

Usage (batch-first: every run is a bulk run at 50% cost, not time-sensitive):
  export ANTHROPIC_API_KEY=sk-ant-...          # same key as the HomePod project
  python scripts/score_movies_api.py --file new_titles.txt --out data/movies.csv
  python scripts/score_movies_api.py --file new_titles.txt --no-wait   # submit & exit
  python scripts/score_movies_api.py --resume msgbatch_xxx --out data/movies.csv
  python scripts/score_movies_api.py "The Sandlot" --year 1993 --sync  # spot check

Repeatability design:
  * temperature=0 (most deterministic sampling; NOT a full determinism guarantee —
    Anthropic documents residual non-determinism even at 0)
  * pinned MODEL string — never use a floating alias in production runs
  * the rubric prompt below is the spec; keep it byte-identical between runs
    (it is hashed into each result row so drift is detectable)
  * optional --runs N: score N times and take the per-dimension MEDIAN, which
    absorbs the residual non-determinism
  * NOTE: temperature/top_p/top_k are rejected (400) by Claude Opus 4.7+;
    use Sonnet or Haiku for this pipeline.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import statistics
import sys
import time
from pathlib import Path

import anthropic
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent

# Reads ANTHROPIC_API_KEY from the environment first; falls back to the .env
# used by the HomePod bot so the key lives in exactly one place.
ENV_FILE = Path(os.environ.get("KIDFLIX_ENV", r"c:/stack/bot/app/.env"))
if not os.environ.get("ANTHROPIC_API_KEY") and ENV_FILE.exists():
    for _line in ENV_FILE.read_text().splitlines():
        _line = _line.strip()
        if _line.startswith("ANTHROPIC_API_KEY="):
            os.environ["ANTHROPIC_API_KEY"] = _line.split("=", 1)[1].strip().strip('"').strip("'")
            break

MODEL = os.environ.get("KIDFLIX_MODEL", "claude-sonnet-4-6")  # pin a dated snapshot for production
TEMPERATURE = 0.0
MAX_TOKENS = 1500

DIM_MAX = {"wealth": 40, "agency": 17, "core": 17,
           "music": 10, "inclusion": 10, "romance": 6}

RUBRIC_PROMPT = """\
You are scoring a film against the Kidflix Rubric: an opinionated, values-based
rubric measuring what a film's STRUCTURE teaches a child viewer, from one specific
parenting angle. You are not rating quality, craft, or enjoyment. Apply the bands
exactly as written; when torn between two bands, pick the lower one and say why.

DIMENSION 1 — INHERITED SPECIALNESS & WEALTH (0-40). Question: does the protagonist
matter because of what they DO, or what they were BORN AS / INTO — and is
wealth/status the story's endorsed reward? Self-made ascension scores as low as
inherited ascension: the rubric penalises the endorsed outcome, not the pursuit of
a livelihood.
  40 = genuinely ordinary protagonist; the story could happen to any kid
       (anchors: Coco 36, Inside Out 40, Spirited Away 40)
  35 = modest born-into status doing narrative work (Moana 35, chief's daughter)
  30 = wealth/status exists but is critiqued as hollow (Encanto 28, Cars-style
       critique with residual glorification lands 20-30)
  20 = born-into greatness, unexamined; no depicted grind (Cars 20)
  16 = royal-but-burdened; status as isolation, still the source of specialness
       (Frozen 16)
  0-8 = status ascension is the endorsed reward, born or climbed
       (Cinderella 0, Aladdin 5, The Lion King 4, Goodfellas 6, Scarface 4,
        Wolf of Wall Street 2)

DIMENSION 2 — PROTAGONIST AGENCY (0-17).
  17 = solves their own story through their own choices (Moana, Anna in Frozen)
  13-15 = strong but split, diluted, or destiny-assisted
  8 = luck-heavy or shared solving
  0-4 = passive; rescued at their own climax (Sleeping Beauty 0, Snow White 2,
        The Little Mermaid 4 — Eric kills the villain)

DIMENSION 3 — EMOTIONAL CORE (0-17). What the story is about UNDER the plot.
  17 = deep honest core: grief, identity, belonging, fear-vs-love
       (Inside Out, Coco, Up, Frozen)
  13-15 = real substance, simpler arc (Cars 15)
  8 = standard adventure/friendship beats
  0-4 = core is status, validation, or being chosen (Sleeping Beauty 0)

DIMENSION 4 — MUSIC (0-10).
  10 = original songs that carry story (Moana, Frozen, Coco)
  8-9 = strong songs with gaps, or performance-central diegetic music
  5-6 = score only, or licensed soundtrack (Cars 5, Inside Out 5)
  0-3 = actively grating or hollow

DIMENSION 5 — INCLUSIVENESS & ANTI-PREJUDICE (0-10). Distinguish PASSIVE ABSENCE
from ACTIVE HARM:
  10 = inclusion/anti-prejudice IS the lesson; prejudice-as-plot
       (Zootopia, The Land Before Time, Shrek, Mulan)
  8-9 = strong inclusion content, secondary to the main arc (Lilo & Stitch 8)
  7 = meaningful representation; not the lesson (Moana 7, Soul 7)
  5-6 = neutral: nothing taught, no group harmed (non-human casts, Toy Story 5)
  4 = homogeneous world presented as default; passive exclusion; missed
      opportunity (the classic princess canon: Cinderella 4, Sleeping Beauty 4)
  2-3 = harmful stereotyping or othering PRESENT in the text
       (Aladdin 2 orientalist caricature, The Lion King 2 hyena underclass,
        Scarface 2, The Godfather 2, Wizard of Oz 2 wicked-because-ugly)
  0-1 = active degradation or othering AS SPECTACLE
       (Wolf of Wall Street 0 women-as-commodities, Peter Pan 0 the
        'What Made the Red Man Red' number)

DIMENSION 6 — ROMANCE FRAMING (0-6).
  6 = absent, or actively subverted (Frozen 6, Brave 6)
  3-5 = present but balanced
  0-2 = marriage/being-chosen is the prize (Little Mermaid 0 — her voice for a
        man; Cinderella 0 — identified by shoe size)

OUTPUT: respond with ONLY a JSON object, no markdown fences, no preamble:
{
  "title": "<film>",
  "year": <int>,
  "wealth": <0-40>, "agency": <0-17>, "core": <0-17>,
  "music": <0-10>, "inclusion": <0-10>, "romance": <0-6>,
  "commentary": {
    "overall": "<2-3 sentence justification of the whole profile>",
    "wealth": "<1 sentence, cite the band logic>",
    "agency": "<1 sentence>",
    "core": "<1 sentence>",
    "music": "<1 sentence>",
    "inclusion": "Band <score>/10 (<band name>): <1 sentence reason>",
    "romance": "<1 sentence>"
  }
}
If you do not know the film well enough to score it honestly, return
{"error": "insufficient knowledge", "title": "<film>"} instead of guessing.
"""

PROMPT_HASH = hashlib.sha256(RUBRIC_PROMPT.encode()).hexdigest()[:12]


def build_params(title: str, year: int | None) -> dict:
    ask = f"Score this film: {title}" + (f" ({year})" if year else "")
    return {
        "model": MODEL,
        "max_tokens": MAX_TOKENS,
        "temperature": TEMPERATURE,
        "system": RUBRIC_PROMPT,
        "messages": [{"role": "user", "content": ask}],
    }


def parse_response(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`").removeprefix("json").strip()
    data = json.loads(text)
    if "error" in data:
        return data
    for dim, mx in DIM_MAX.items():
        v = data[dim]
        if not (isinstance(v, int) and 0 <= v <= mx):
            raise ValueError(f"{dim}={v} out of 0-{mx}")
    return data


# ---------------------------------------------------------------------------
# Batch path (default): 50% cheaper, processed within a 24h window.
# ---------------------------------------------------------------------------
def submit_batch(client: anthropic.Anthropic,
                 jobs: list[tuple[str, int | None]], runs: int) -> str:
    requests = []
    for idx, (title, year) in enumerate(jobs):
        for run in range(runs):
            requests.append({
                "custom_id": f"m{idx}_r{run}",       # 1-64 chars, [a-zA-Z0-9_-]
                "params": build_params(title, year),
            })
    batch = client.messages.batches.create(requests=requests)
    manifest = {
        "batch_id": batch.id, "model": MODEL, "prompt_hash": PROMPT_HASH,
        "runs": runs, "jobs": [{"idx": i, "title": t, "year": y}
                               for i, (t, y) in enumerate(jobs)],
    }
    mpath = ROOT / f"batch_{batch.id}.json"
    mpath.write_text(json.dumps(manifest, indent=2))
    print(f"Submitted batch {batch.id} "
          f"({len(requests)} requests = {len(jobs)} films x {runs} runs)")
    print(f"Manifest saved to {mpath.name} — resume anytime with:")
    print(f"  python scripts/score_movies_api.py --resume {batch.id} --out data/movies.csv")
    return batch.id


def collect_batch(client: anthropic.Anthropic, batch_id: str,
                  wait: bool) -> list[dict] | None:
    batch = client.messages.batches.retrieve(batch_id)
    while batch.processing_status != "ended":
        if not wait:
            print(f"Batch {batch_id} status: {batch.processing_status} — "
                  f"not finished yet; re-run with --resume later.")
            return None
        print(f"  status={batch.processing_status}, checking again in 60s "
              f"(batches complete within 24h, usually much faster)")
        time.sleep(60)
        batch = client.messages.batches.retrieve(batch_id)

    manifest = json.loads((ROOT / f"batch_{batch_id}.json").read_text())
    by_idx = {j["idx"]: j for j in manifest["jobs"]}
    runs_by_film: dict[int, list[dict]] = {}
    failures = 0
    for entry in client.messages.batches.results(batch_id):
        idx, _run = entry.custom_id[1:].split("_r")
        idx = int(idx)
        if entry.result.type != "succeeded":
            print(f"  {by_idx[idx]['title']}: request {entry.result.type}", file=sys.stderr)
            failures += 1
            continue
        text = "".join(b.text for b in entry.result.message.content
                       if b.type == "text")
        try:
            data = parse_response(text)
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            print(f"  {by_idx[idx]['title']}: bad response ({e})", file=sys.stderr)
            failures += 1
            continue
        if "error" in data:
            print(f"  {by_idx[idx]['title']}: SKIPPED ({data['error']})")
            continue
        runs_by_film.setdefault(idx, []).append(data)

    finals = []
    for idx, results in sorted(runs_by_film.items()):
        final = dict(results[0])          # commentary from the first run
        final["title"] = by_idx[idx]["title"]
        final["year"] = by_idx[idx]["year"]
        if len(results) > 1:
            spread = {}
            for dim in DIM_MAX:
                vals = [r[dim] for r in results]
                final[dim] = int(statistics.median(vals))
                spread[dim] = max(vals) - min(vals)
            final["run_spread"] = spread   # 0 everywhere = perfectly repeatable
        final["model"] = manifest["model"]
        final["prompt_hash"] = manifest["prompt_hash"]
        final["runs"] = len(results)
        finals.append(final)
    if failures:
        print(f"{failures} request(s) failed — rerun those films individually.")
    return finals


# ---------------------------------------------------------------------------
# Synchronous path (--sync): full price, immediate; for one-off spot checks.
# ---------------------------------------------------------------------------
def score_sync(client: anthropic.Anthropic, title: str, year: int | None,
               runs: int) -> dict:
    results = []
    for i in range(runs):
        for attempt in range(4):
            try:
                msg = client.messages.create(**build_params(title, year))
                data = parse_response(
                    "".join(b.text for b in msg.content if b.type == "text"))
                break
            except (anthropic.APIStatusError, anthropic.APIConnectionError) as e:
                wait = 2 ** attempt
                print(f"  API error ({e.__class__.__name__}), retry in {wait}s",
                      file=sys.stderr)
                time.sleep(wait)
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                print(f"  bad response ({e}), retrying", file=sys.stderr)
        else:
            raise RuntimeError(f"failed to score {title!r}")
        if "error" in data:
            return data
        results.append(data)
    final = dict(results[0])
    if runs > 1:
        spread = {}
        for dim in DIM_MAX:
            vals = [r[dim] for r in results]
            final[dim] = int(statistics.median(vals))
            spread[dim] = max(vals) - min(vals)
        final["run_spread"] = spread
    final.update(model=MODEL, prompt_hash=PROMPT_HASH, runs=runs)
    return final


def write_rows(rows: list[dict], out: str) -> None:
    outp = Path(out)
    df = pd.read_csv(outp) if outp.exists() else pd.DataFrame()
    for r in rows:
        row = {
            "title": r["title"], "year": r.get("year"),
            "mpaa": "", **{d: r[d] for d in DIM_MAX},
            "rt_critic": "", "rt_audience": "",
            "revenue_musd": "", "revenue_adj_musd": "", "icon": "",
            "commentary": json.dumps(r["commentary"], ensure_ascii=False),
        }
        df = df[df["title"] != r["title"]] if len(df) else df
        df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    df.to_csv(outp, index=False)
    print(f"Wrote {len(rows)} row(s) to {outp} "
          f"(fill mpaa/RT/revenue manually, then run analysis.py)")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("title", nargs="?")
    ap.add_argument("--year", type=int)
    ap.add_argument("--file", help="text file, one 'Title,year' per line")
    ap.add_argument("--runs", type=int, default=3,
                    help="score N times, keep per-dimension median (default 3)")
    ap.add_argument("--out", help="CSV to append/update (e.g. data/movies.csv)")
    ap.add_argument("--resume", metavar="BATCH_ID",
                    help="collect results of a previously submitted batch")
    ap.add_argument("--no-wait", action="store_true",
                    help="submit the batch and exit instead of polling")
    ap.add_argument("--sync", action="store_true",
                    help="score synchronously at full price (spot checks only)")
    args = ap.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("Set ANTHROPIC_API_KEY (same env var as the HomePod project).")
    client = anthropic.Anthropic()

    if args.resume:
        rows = collect_batch(client, args.resume, wait=not args.no_wait)
        if rows:
            for r in rows:
                total = sum(r[d] for d in DIM_MAX)
                print(f"  {r['title']}: total {total} | "
                      + " ".join(f"{d}={r[d]}" for d in DIM_MAX)
                      + (f" | spread {r['run_spread']}" if r.get("run_spread") else ""))
            if args.out:
                write_rows(rows, args.out)
        return

    jobs: list[tuple[str, int | None]] = []
    if args.file:
        for line in Path(args.file).read_text().splitlines():
            if line.strip():
                t, _, y = line.partition(",")
                jobs.append((t.strip(), int(y) if y.strip() else None))
    elif args.title:
        jobs.append((args.title, args.year))
    else:
        ap.error("give a title, --file, or --resume BATCH_ID")

    if args.sync:
        rows = []
        for title, year in jobs:
            print(f"Scoring {title} [sync, model={MODEL}, temp={TEMPERATURE}, "
                  f"runs={args.runs}]")
            r = score_sync(client, title, year, args.runs)
            if "error" in r:
                print(f"  SKIPPED: {r['error']}")
                continue
            total = sum(r[d] for d in DIM_MAX)
            print(f"  -> total {total}")
            rows.append(r)
        if args.out and rows:
            write_rows(rows, args.out)
        return

    # default: everything is a bulk run via the Batch API (50% cheaper)
    batch_id = submit_batch(client, jobs, args.runs)
    rows = collect_batch(client, batch_id, wait=not args.no_wait)
    if rows and args.out:
        write_rows(rows, args.out)


if __name__ == "__main__":
    main()
