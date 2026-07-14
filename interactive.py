"""
Interactive (Plotly) pages: one template, multiple views.

Emits:
  output/interactive.html       scores view  -> served at /kids-movies/
  output/interactive_rank.html  rank view    -> served at /ranked_chart/

Shared behaviour (written once, applied to every view):
  - zoom-adaptive labels: ~14 highest-rubric films labelled at full zoom-out,
    the budget grows as the viewport shrinks (JS on plotly_relayout, no server)
  - hover cards rendering the per-dimension commentary JSON
  - adult films as a legendonly trace (hidden until clicked)
  - scrollZoom: mouse wheel zooms, centred on the cursor
  - rows missing RT or revenue metadata excluded, with a console note

Adding a chart = one view function + one entry in VIEWS + one build_site.py
landing-page list item.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go

ROOT = Path(__file__).parent
OUT = ROOT / "output"

RUBRIC = json.loads((ROOT / "rubric.json").read_text(encoding="utf-8"))
DIM_MAX = {k: v["max"] for k, v in RUBRIC["dimensions"].items()}


def load(path: Path, segment: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["total"] = df[list(DIM_MAX)].sum(axis=1)
    df["segment"] = segment
    n = len(df)
    df = df.dropna(subset=["rt_audience", "rt_critic", "revenue_adj_musd"])
    if len(df) < n:
        print(f"  {segment}: {n - len(df)} film(s) scored but awaiting "
              f"RT/revenue metadata; excluded from the interactive chart")
    return df.reset_index(drop=True)


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


BASE_LABELS = 45   # labels at full zoom-out; the budget grows as you zoom in


def tier_colour_for(total: float) -> str:
    for _, lo, hi, colour in TIERS:
        if lo <= total < hi or (hi == 104 and total >= lo):
            return colour
    return "#b71c1c"


def make_trace(df: pd.DataFrame, xs, ys, name: str, colour, symbol: str,
               visible=True, initial_labels: int = BASE_LABELS) -> go.Scatter:
    """One segment as a trace. xs/ys are the view's coordinates. Label
    priority (customdata[1]) is inflation-adjusted gross: the biggest-spend
    films get named first when the budget forces a reduction. `colour` may be
    a single colour or a per-point list (tier colouring on the rank view)."""
    prio = df["revenue_adj_musd"]
    if visible is True and initial_labels:
        cutoff = prio.nlargest(min(initial_labels, len(df))).min()
        text = [t if p >= cutoff else "" for t, p in zip(df["title"], prio)]
    else:
        text = [""] * len(df)
    return go.Scatter(
        visible=visible,
        x=list(xs), y=list(ys),
        mode="markers+text",
        name=name,
        text=text,                                # top-N at load; JS refines on zoom
        textposition="top center",
        textfont=dict(size=11),
        hovertext=[hover_text(r) for _, r in df.iterrows()],
        hoverinfo="text",
        hoverlabel=dict(align="left", font_size=11),
        marker=dict(
            size=((df["revenue_adj_musd"].clip(lower=20) ** 0.5) / 1.6 + 7).tolist(),
            color=list(colour) if not isinstance(colour, str) else colour,
            symbol=symbol,
            line=dict(width=1, color="black"), opacity=0.85,
        ),
        customdata=[[t, float(p)] for t, p in zip(df["title"], prio)],
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
    var areaFrac = Math.max(1e-6, Math.abs(
        ((xr[1]-xr[0]) * (yr[1]-yr[0])) /
        ((FULL.x[1]-FULL.x[0]) * (FULL.y[1]-FULL.y[0]))));
    // label budget: ~45 fully zoomed out, growing as the viewport shrinks
    var budget = Math.round(45 / areaFrac);

    // gather visible points across traces with their priority
    var vis = [];
    var src = gd._fullData || gd.data;
    src.forEach(function(ftr, ti) {
        var tr = gd.data[ti];
        if (!tr.customdata) return;   // legend-key traces carry no points
        if (ftr.visible === 'legendonly' || ftr.visible === false) return;
        var txs = Array.from(ftr.x), tys = Array.from(ftr.y);
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

    var newText = (gd._fullData || gd.data).map(function(ftr, ti) {
        var tr = gd.data[ti];
        if (!tr.customdata) return [];
        var arr = [];
        for (var i = 0; i < ftr.x.length; i++) {
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

TIERS = [("S", 90, 104, "#2e7d32"), ("A", 75, 90, "#7cb342"),
         ("B", 60, 75, "#fbc02d"), ("C", 45, 60, "#fb8c00"),
         ("D", 30, 45, "#e64a19"), ("F", 0, 30, "#b71c1c")]


def scores_view(kids: pd.DataFrame, adult: pd.DataFrame) -> go.Figure:
    """Audience % (x) vs rubric total (y), tier bands, bubble = adj. gross."""
    fig = go.Figure([
        make_trace(kids, kids["rt_audience"], [int(t) for t in kids["total"]],
                   f"Kids films (n={len(kids)})", "#7cb342", "circle"),
        make_trace(adult, adult["rt_audience"], [int(t) for t in adult["total"]],
                   f"Adult films (n={len(adult)}) — click to show", "#5c6bc0",
                   "square", visible="legendonly"),
    ])
    for name, lo, hi, colour in TIERS:
        fig.add_hrect(y0=lo, y1=hi, fillcolor=colour, opacity=0.05, line_width=0)
        fig.add_annotation(x=22, y=(lo + hi) / 2, text=f"<b>{name}</b>",
                           showarrow=False, font=dict(size=20, color=colour),
                           opacity=0.5)
    fig.update_layout(
        title="Kidflix rubric — audience love vs. what the film teaches "
              "(scroll to zoom for more labels; bubble = inflation-adjusted gross; "
              "adult films hidden by default — click the legend to show them)",
        xaxis=dict(title="Rotten Tomatoes — audience (Popcornmeter %)",
                   range=[20, 103]),
        yaxis=dict(title="Rubric score (/100)", range=[0, 104]),
        template="plotly_white",
        height=820,
        legend=dict(x=0.01, y=0.01, bgcolor="rgba(255,255,255,0.7)"),
        hovermode="closest",
    )
    return fig


def rank_view(kids: pd.DataFrame, adult: pd.DataFrame) -> go.Figure:
    """Audience rank (x) vs rubric rank (y). Ranks are computed across the
    combined pool so toggling adult films on shows their true positions in
    the same coordinate system. Rank 1 at top-right; diagonal = agreement."""
    both = pd.concat([kids, adult], ignore_index=True)
    n = len(both)
    both["x_rank"] = both["rt_audience"].rank(ascending=False, method="first").astype(int)
    both["y_rank"] = both["total"].rank(ascending=False, method="first").astype(int)
    k = both[both["segment"] == "kids"]
    a = both[both["segment"] == "adult"]

    fig = go.Figure([
        make_trace(k, k["x_rank"], k["y_rank"],
                   f"Kids films (n={len(k)}, colour = tier)",
                   [tier_colour_for(t) for t in k["total"]], "circle"),
        make_trace(a, a["x_rank"], a["y_rank"],
                   f"Adult films (n={len(a)}) — click to show",
                   [tier_colour_for(t) for t in a["total"]],
                   "square", visible="legendonly"),
    ])
    # tier colour key (display-only legend entries, no data points)
    for tname, lo, hi, colour in TIERS:
        fig.add_trace(go.Scatter(
            x=[None], y=[None], mode="markers", hoverinfo="skip",
            marker=dict(size=10, color=colour, symbol="circle",
                        line=dict(width=1, color="black")),
            name=f"{tname} tier ({lo}-{hi if hi < 104 else 100})",
            showlegend=True))
    # diagonal: audience and rubric agree
    fig.add_shape(type="line", x0=0, y0=0, x1=n + 1, y1=n + 1,
                  line=dict(color="gray", width=1, dash="dot"), layer="below")
    # quadrant crosshairs at the rank midpoint + the four quadrant readings
    mid = (n + 1) / 2
    fig.add_shape(type="line", x0=mid, y0=-1, x1=mid, y1=n + 2,
                  line=dict(color="gray", width=1, dash="dash"), opacity=0.6,
                  layer="below")
    fig.add_shape(type="line", x0=-1, y0=mid, x1=n + 2, y1=mid,
                  line=dict(color="gray", width=1, dash="dash"), opacity=0.6,
                  layer="below")
    lo_q, hi_q = mid / 2, mid + (n - mid) / 2
    for x, y, txt, colour in [
        (lo_q, lo_q, "<b>SAFE BETS</b><br>top half on both", "#2e7d32"),
        (hi_q, lo_q, "<b>HIDDEN GEMS</b><br>rubric loves, audience shrugs", "#1565c0"),
        (lo_q, hi_q, "<b>BELOVED BUT CORROSIVE</b><br>audience loves, rubric objects", "#b71c1c"),
        (hi_q, hi_q, "<b>SKIP</b><br>bottom half on both", "#616161"),
    ]:
        fig.add_annotation(x=x, y=y, text=txt, showarrow=False,
                           font=dict(size=13, color=colour), opacity=0.65,
                           bgcolor="rgba(255,255,255,0.75)",
                           bordercolor="gray", borderwidth=1)
    fig.update_layout(
        title=f"Kidflix rubric — audience rank vs. rubric rank "
              f"(1 = best; ranks computed across all {n} films; scroll to zoom "
              f"for more labels; dotted line = audience and rubric agree)",
        xaxis=dict(title=f"Audience rank (1 = most loved of {n})",
                   range=[n + 2, -1]),        # reversed: rank 1 at the right
        yaxis=dict(title=f"Rubric rank (1 = best values of {n})",
                   range=[n + 2, -1]),        # reversed: rank 1 at the top
        template="plotly_white",
        height=820,
        legend=dict(x=0.01, y=0.01, bgcolor="rgba(255,255,255,0.7)"),
        hovermode="closest",
    )
    return fig


# view builder, output filename, plotly.min.js src relative to the page's
# final address on the site (see build_site.py for where each page lands)
VIEWS = [
    (scores_view, "interactive.html",      "plotly.min.js"),
    (rank_view,   "interactive_rank.html", "../kids-movies/plotly.min.js"),
]


def main() -> None:
    kids = load(ROOT / "data" / "movies.csv", "kids")
    adult = load(ROOT / "data" / "movies_adult.csv", "adult")

    OUT.mkdir(exist_ok=True)
    for build, name, pjs in VIEWS:
        fig = build(kids, adult)
        out = OUT / name
        fig.write_html(out, include_plotlyjs=pjs, post_script=POST_SCRIPT,
                       full_html=True, config={"scrollZoom": True})
        print(f"Wrote {out}")


if __name__ == "__main__":
    main()