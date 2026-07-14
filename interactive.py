"""
Interactive (Plotly) version of the values-vs-audience scatter.

Produces output/interactive.html — a single self-contained page suitable for
static hosting (GitHub Pages, PythonAnywhere static dir, etc.).

Zoom-adaptive labels: at full zoom-out only the highest-priority points are
labelled (priority = rubric total); zooming in reveals progressively more
labels until every visible point is named. Implemented with a small JS
handler on plotly_relayout, so it needs no server.

Filtering: kids and adult films are separate traces — click the legend to
isolate either segment (double-click to solo). Hover shows the per-dimension
scores and JSON commentary.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go

ROOT = Path(__file__).parent
OUT = ROOT / "output"

RUBRIC = json.loads((ROOT / "rubric.json").read_text())
DIM_MAX = {k: v["max"] for k, v in RUBRIC["dimensions"].items()}


def load(path: Path, segment: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["total"] = df[list(DIM_MAX)].sum(axis=1)
    df["segment"] = segment
    return df


def hover_text(row: pd.Series) -> str:
    c = json.loads(row["commentary"])
    lines = [
        f"<b>{row['title']}</b> ({row['year']}, {row['mpaa']})",
        f"Rubric <b>{row['total']}</b>/100 | Audience {row['rt_audience']}% | "
        f"Critics {row['rt_critic']}% | ${row['revenue_adj_musd']:.0f}M adj",
        f"<i>{c['overall']}</i>",
        "",
    ]
    for dim, mx in DIM_MAX.items():
        lines.append(f"<b>{dim.title()} {row[dim]}/{mx}</b>: {c[dim]}")
    # soft-wrap long lines for the hover box
    wrapped = []
    for ln in lines:
        while len(ln) > 90:
            cut = ln.rfind(" ", 0, 90)
            cut = cut if cut > 0 else 90
            wrapped.append(ln[:cut])
            ln = ln[cut:].lstrip()
        wrapped.append(ln)
    return "<br>".join(wrapped)


def make_trace(df: pd.DataFrame, name: str, colour: str, symbol: str,
               visible=True) -> go.Scatter:
    return go.Scatter(
        visible=visible,
        x=df["rt_audience"], y=df["total"],
        mode="markers+text",
        name=name,
        text=[""] * len(df),                      # filled dynamically by JS
        textposition="top center",
        textfont=dict(size=11),
        hovertext=[hover_text(r) for _, r in df.iterrows()],
        hoverinfo="text",
        hoverlabel=dict(align="left", font_size=11),
        marker=dict(
            size=(df["revenue_adj_musd"].clip(lower=20) ** 0.5) / 1.6 + 7,
            color=colour, symbol=symbol,
            line=dict(width=1, color="black"), opacity=0.85,
        ),
        customdata=list(zip(df["title"], df["total"])),  # [label, priority]
    )


POST_SCRIPT = """
var gd = document.getElementById('{plot_id}');

function fullRanges() {
    var fl = gd._fullLayout;
    return {x: fl.xaxis.range.slice(), y: fl.yaxis.range.slice()};
}
var FULL = null;

function updateLabels() {
    if (!FULL) FULL = fullRanges();
    var fl = gd._fullLayout;
    var xr = fl.xaxis.range, yr = fl.yaxis.range;
    var areaFrac = Math.max(1e-6,
        ((xr[1]-xr[0]) * (yr[1]-yr[0])) /
        ((FULL.x[1]-FULL.x[0]) * (FULL.y[1]-FULL.y[0])));
    // label budget: ~14 fully zoomed out, growing as the viewport shrinks
    var budget = Math.round(14 / areaFrac);

    // gather visible points across traces with their priority
    var vis = [];
    gd.data.forEach(function(tr, ti) {
        if (tr.visible === 'legendonly') return;
        var txs = Array.from(tr.x), tys = Array.from(tr.y);
        for (var i = 0; i < txs.length; i++) {
            if (txs[i] >= Math.min(xr[0],xr[1]) && txs[i] <= Math.max(xr[0],xr[1]) &&
                tys[i] >= Math.min(yr[0],yr[1]) && tys[i] <= Math.max(yr[0],yr[1])) {
                vis.push({ti: ti, i: i, prio: tr.customdata[i][1]});
            }
        }
    });
    vis.sort(function(a, b) { return b.prio - a.prio; });
    var chosen = {};
    vis.slice(0, budget).forEach(function(p) {
        (chosen[p.ti] = chosen[p.ti] || {})[p.i] = true;
    });

    var newText = gd.data.map(function(tr, ti) {
        var arr = [];
        for (var i = 0; i < tr.x.length; i++) {
            arr.push((chosen[ti] && chosen[ti][i]) ? String(tr.customdata[i][0]) : '');
        }
        return arr;
    });
    Plotly.restyle(gd, {text: newText});
}

gd.on('plotly_relayout', function(e) {
    if (e['xaxis.autorange'] || e['yaxis.autorange']) FULL = fullRanges();
    updateLabels();
});
gd.on('plotly_restyle', function(e) {
    // legend toggling changes trace visibility -> recompute
    if (e && e[0] && 'visible' in e[0]) updateLabels();
});
updateLabels();
"""


def main() -> None:
    kids = load(ROOT / "data" / "movies.csv", "kids")
    adult = load(ROOT / "data" / "movies_adult.csv", "adult")

    fig = go.Figure([
        make_trace(kids, f"Kids films (n={len(kids)})", "#7cb342", "circle"),
        make_trace(adult, f"Adult films (n={len(adult)}) — click to show", "#5c6bc0",
                   "square", visible="legendonly"),
    ])

    # tier bands
    tiers = [("S", 90, 104, "#2e7d32"), ("A", 75, 90, "#7cb342"),
             ("B", 60, 75, "#fbc02d"), ("C", 45, 60, "#fb8c00"),
             ("D", 30, 45, "#e64a19"), ("F", 0, 30, "#b71c1c")]
    for name, lo, hi, colour in tiers:
        fig.add_hrect(y0=lo, y1=hi, fillcolor=colour, opacity=0.05, line_width=0)
        fig.add_annotation(x=22, y=(lo + hi) / 2, text=f"<b>{name}</b>",
                           showarrow=False, font=dict(size=20, color=colour),
                           opacity=0.5)

    fig.update_layout(
        title="Kidflix rubric — audience love vs. what the film teaches "
              "(zoom in for more labels; bubble = inflation-adjusted gross; "
              "adult films hidden by default — click the legend to show them)",
        xaxis=dict(title="Rotten Tomatoes — audience (Popcornmeter %)",
                   range=[20, 103]),
        yaxis=dict(title="Rubric score (/100)", range=[0, 104]),
        template="plotly_white",
        height=820,
        legend=dict(x=0.01, y=0.01, bgcolor="rgba(255,255,255,0.7)"),
        hovermode="closest",
    )

    OUT.mkdir(exist_ok=True)
    out = OUT / "interactive.html"
    fig.write_html(out, include_plotlyjs="plotly.min.js", post_script=POST_SCRIPT,
                   full_html=True)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
