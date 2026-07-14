"""
build_site.py — assemble the deployable static site under docs/.

Layout produced (GitHub Pages serves docs/ at https://analysis.thebutygroup.com):

docs/
  CNAME                      -> custom-domain binding for GitHub Pages
  index.html                 -> tiny landing page linking to /kids-movies/
  kids-movies/
    index.html               -> the interactive chart (self-contained data)
    plotly.min.js            -> self-hosted, pinned plotly (no CDN dependency)
    charts/*.png             -> the static analysis charts
    data/*.csv               -> full datasets + computed outputs

Run: python build_site.py   (regenerates the interactive chart first)
"""

from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).parent
DOCS = ROOT / "docs"
KM = DOCS / "kids-movies"

DOMAIN = "analysis.thebutygroup.com"

LANDING = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>The Buty Group — Analysis</title>
<style>body{{font-family:system-ui,sans-serif;max-width:42rem;margin:4rem auto;
padding:0 1rem;color:#222}}a{{color:#2e7d32}}</style></head>
<body>
<h1>Analysis</h1>
<ul>
  <li><a href="/kids-movies/">Kids' movies: what they actually teach</a> —
      a values rubric vs. audience scores, interactive.</li>
</ul>
</body></html>
"""


def main() -> None:
    # 1. regenerate the interactive chart from current data
    subprocess.run([sys.executable, str(ROOT / "interactive.py")], check=True)

    # 2. assemble docs/
    if KM.exists():
        shutil.rmtree(KM)
    (KM / "charts").mkdir(parents=True)
    (KM / "data").mkdir()

    (DOCS / "CNAME").write_text(DOMAIN + "\n")
    (DOCS / "index.html").write_text(LANDING)

    shutil.copy(ROOT / "output" / "interactive.html", KM / "index.html")

    import plotly
    pjs = pathlib.Path(plotly.__file__).parent / "package_data" / "plotly.min.js"
    shutil.copy(pjs, KM / "plotly.min.js")

    # Curated charts only: each earns its place in the story.
    CHARTS = [
        "scatter_audience.png",     # headline: audience love vs values, quadrants
        "scatter_rank.png",         # the pure ordinal relationship
        "compare_dimensions.png",   # kids vs adult dimension profile
        "compare_top_revenue.png",  # the biggest earners, absolute scores
    ]
    for name in CHARTS:
        shutil.copy(ROOT / "output" / name, KM / "charts" / name)

    for csv in [*(ROOT / "data").glob("*.csv"),
                *(ROOT / "output").glob("*_scored.csv"),
                ROOT / "output" / "divergence.csv",
                ROOT / "output" / "compare_top_revenue.csv"]:
        if csv.exists():
            shutil.copy(csv, KM / "data" / csv.name)

    n = sum(1 for _ in KM.rglob("*") if _.is_file())
    print(f"docs/ assembled: {n} files under kids-movies/, CNAME={DOMAIN}")


if __name__ == "__main__":
    main()
