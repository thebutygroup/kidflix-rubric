"""
build_site.py — assemble the deployable static site under docs/.

Layout produced (GitHub Pages serves docs/ at https://analysis.thebutygroup.com):

docs/
  CNAME                      -> custom-domain binding for GitHub Pages
  index.html                 -> tiny landing page linking to the charts
  ranked_chart/index.html    -> interactive rank view (uses ../kids-movies/plotly.min.js)
  kids-movies/
    index.html               -> interactive scores view
    plotly.min.js            -> self-hosted, pinned plotly (no CDN dependency)
    charts/*.png             -> the curated static analysis charts
    data/*.csv               -> full datasets + computed outputs

Run: python build_site.py   (regenerates the interactive pages first)
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

# Output filenames emitted by interactive.py. If interactive.py names its
# rank page differently, fix RANK_HTML here (verify with:
#   findstr /C:".html" interactive.py).
SCORES_HTML = "interactive.html"
RANK_HTML = "interactive_rank.html"

LANDING_TEMPLATE = ROOT / "landing.html"  # marker: landing-v2 weighted-band


def render_landing() -> str:
    """Fill landing.html placeholders with live stats from data/movies.csv.

    Uses the same completeness criteria as interactive.load(): a film is
    "on the chart" only if rt_audience, rt_critic and revenue_adj_musd are
    all present. Spearman rho is computed as pearson-of-ranks so scipy is
    not required.
    """
    import pandas as pd

    df = pd.read_csv(ROOT / "data" / "movies.csv")
    dims = ["wealth", "agency", "core", "music", "inclusion", "romance"]
    df["total"] = df[dims].sum(axis=1)
    on_chart = df.dropna(subset=["rt_audience", "rt_critic", "revenue_adj_musd"])
    rho = on_chart["total"].rank().corr(on_chart["rt_audience"].rank())

    html = LANDING_TEMPLATE.read_text(encoding="utf-8")
    for key, val in {
        "{{N_SCORED}}": str(len(df)),
        "{{N_CHART}}": str(len(on_chart)),
        "{{N_PENDING}}": str(len(df) - len(on_chart)),
        "{{RHO}}": f"{rho:.2f}",
    }.items():
        html = html.replace(key, val)
    if "{{" in html:
        raise SystemExit("landing.html contains an unfilled {{placeholder}} — "
                         "refusing to publish a broken landing page.")
    return html

def main() -> None:
    # 1. regenerate the interactive pages from current data
    subprocess.run([sys.executable, str(ROOT / "interactive.py")], check=True)

    # 2. assemble docs/
    if KM.exists():
        shutil.rmtree(KM)
    (KM / "charts").mkdir(parents=True)
    (KM / "data").mkdir()

    (DOCS / "CNAME").write_text(DOMAIN + "\n", encoding="utf-8")
    (DOCS / "index.html").write_text(render_landing(), encoding="utf-8")
    (DOCS / "robots.txt").write_text(
        "User-agent: *\nAllow: /\nSitemap: https://analysis.thebutygroup.com/sitemap.xml\n",
        encoding="utf-8")
    (DOCS / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        '  <url><loc>https://analysis.thebutygroup.com/</loc></url>\n'
        '  <url><loc>https://analysis.thebutygroup.com/kids-movies/</loc></url>\n'
        '  <url><loc>https://analysis.thebutygroup.com/ranked_chart/</loc></url>\n'
        '</urlset>\n', encoding="utf-8")

    # interactive pages
    shutil.copy(ROOT / "output" / SCORES_HTML, KM / "index.html")
    rc = DOCS / "ranked_chart"
    if rc.exists():
        shutil.rmtree(rc)
    rc.mkdir()
    rank_src = ROOT / "output" / RANK_HTML
    if rank_src.exists():
        shutil.copy(rank_src, rc / "index.html")
    else:
        raise SystemExit(f"output/{RANK_HTML} not found — interactive.py did "
                         f"not emit the rank view; refusing to build a broken "
                         f"/ranked_chart page.")

    # self-hosted plotly, shared by both interactive pages
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