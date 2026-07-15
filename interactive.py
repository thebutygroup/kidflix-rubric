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
        customdata=[[t, float(p), int(tot)]
                    for t, p, tot in zip(df["title"], prio, df["total"])],
    )


POST_SCRIPT = r"""
var gd = document.getElementById('{plot_id}');

function fullRanges() {
    var fl = gd._fullLayout;
    return {x: fl.xaxis.range.slice(), y: fl.yaxis.range.slice()};
}
var FULL = null;
var STICKY = {};
var PREV_AREA = null;

function updateLabels() {
    if (!FULL) FULL = fullRanges();
    var fl = gd._fullLayout;
    var xr = fl.xaxis.range, yr = fl.yaxis.range;
    var area = Math.abs((xr[1]-xr[0]) * (yr[1]-yr[0]));
    var fullArea = Math.abs((FULL.x[1]-FULL.x[0]) * (FULL.y[1]-FULL.y[0]));
    var areaFrac = Math.max(1e-6, area / fullArea);
    // label budget: ~45 fully zoomed out, growing as the viewport shrinks
    var budget = Math.round(45 / areaFrac);

    // Sticky labels: a label placed at a wider zoom is a landmark. It is
    // only removed when (a) its point leaves the viewport, or (b) the user
    // zooms OUT (viewport area grows), which re-selects from scratch.
    var zoomedOut = (PREV_AREA !== null && area > PREV_AREA * 1.001);
    PREV_AREA = area;
    if (zoomedOut) STICKY = {};

    // gather visible points across traces with their priority
    var vis = [], visSet = {};
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
                visSet[ti + ':' + i] = true;
            }
        }
    });

    // keep every sticky label whose point is still visible (never trimmed
    // on zoom-in, even past the budget)
    var chosen = {}, count = 0;
    for (var fkey in FORCED) {
        if (visSet[fkey]) { chosen[fkey] = true; count++; }
    }
    for (var key in STICKY) {
        if (visSet[key] && !chosen[key]) { chosen[key] = true; count++; }
    }
    // fill the remaining budget with the highest-priority visible points
    vis.sort(function(a, b) { return b.prio - a.prio; });
    for (var j = 0; j < vis.length && count < budget; j++) {
        var kk = vis[j].ti + ':' + vis[j].i;
        if (!chosen[kk]) { chosen[kk] = true; count++; }
    }
    STICKY = chosen;

    var newText = (gd._fullData || gd.data).map(function(ftr, ti) {
        var tr = gd.data[ti];
        if (!tr.customdata) return [];
        var arr = [];
        for (var i = 0; i < ftr.x.length; i++) {
            arr.push(chosen[ti + ':' + i] ? String(tr.customdata[i][0]) : '');
        }
        return arr;
    });
    Plotly.restyle(gd, {text: newText});
}

// ---- film search ----
var FORCED = {};   // labels the user searched for; always shown while visible
var sbox = document.createElement('div');
sbox.style.cssText = 'position:fixed;top:10px;left:10px;z-index:1000;' +
    'background:#fff;padding:8px;border:1px solid #bbb;border-radius:6px;' +
    'box-shadow:0 1px 4px rgba(0,0,0,0.2);font-family:sans-serif';
sbox.innerHTML = '<input id="film-search" list="film-titles" ' +
    'placeholder="Find a film..." style="width:230px;padding:4px">' +
    '<datalist id="film-titles"></datalist>' +
    '<div id="film-result" style="font-size:12px;margin-top:4px;color:#333"></div>';
document.body.appendChild(sbox);

var TITLES = [];
gd.data.forEach(function(tr, ti) {
    if (!tr.customdata) return;
    tr.customdata.forEach(function(cd, i) {
        TITLES.push({t: String(cd[0]), ti: ti, i: i, score: cd[2]});
    });
});
TITLES.sort(function(a, b) { return a.t.localeCompare(b.t); });
var dl = document.getElementById('film-titles');
TITLES.forEach(function(o) {
    var opt = document.createElement('option');
    opt.value = o.t;
    dl.appendChild(opt);
});

function lev(a, b) {
    var m = a.length, n = b.length;
    var row = [];
    for (var j = 0; j <= n; j++) row.push(j);
    for (var i = 1; i <= m; i++) {
        var prev = row[0]; row[0] = i;
        for (var k = 1; k <= n; k++) {
            var tmp = row[k];
            row[k] = Math.min(row[k] + 1, row[k - 1] + 1,
                              prev + (a[i - 1] === b[k - 1] ? 0 : 1));
            prev = tmp;
        }
    }
    return row[n];
}

function fuzzyHit(q) {
    // closest word-span of any title, tolerating ~1 typo per 3 characters
    var best = null, bestD = Math.max(2, Math.ceil(q.length * 0.34));
    TITLES.forEach(function(o) {
        var words = o.t.toLowerCase().split(/\s+/);
        for (var i = 0; i < words.length; i++) {
            var span = '';
            for (var j = i; j < words.length; j++) {
                span = span ? span + ' ' + words[j] : words[j];
                var d = lev(q, span);
                if (d < bestD) { bestD = d; best = o; }
            }
        }
    });
    return best;
}

function doSearch(q) {
    q = q.trim().toLowerCase();
    var res = document.getElementById('film-result');
    if (!q) { res.textContent = ''; return; }
    var fuzzy = false;
    var hit = TITLES.find(function(o) { return o.t.toLowerCase() === q; }) ||
              TITLES.find(function(o) { return o.t.toLowerCase().indexOf(q) === 0; }) ||
              TITLES.find(function(o) { return o.t.toLowerCase().indexOf(q) >= 0; });
    if (!hit) { hit = fuzzyHit(q); fuzzy = !!hit; }
    if (!hit) {
        res.textContent = 'Not on this chart: "' + q + '"';
        return;
    }
    res.textContent = (fuzzy ? 'Closest match: ' : '') +
        hit.t + ' \u2014 rubric ' + hit.score + '/100';
    var key = hit.ti + ':' + hit.i;
    FORCED = {};
    FORCED[key] = true;
    var ftr = (gd._fullData || gd.data)[hit.ti];
    var pre = (ftr.visible === 'legendonly')
        ? Plotly.restyle(gd, {visible: true}, [hit.ti])
        : Promise.resolve();
    pre.then(function() {
        var fd = (gd._fullData || gd.data)[hit.ti];
        var fx = Array.from(fd.x)[hit.i], fy = Array.from(fd.y)[hit.i];
        if (!FULL) FULL = fullRanges();
        var dx = (FULL.x[1] - FULL.x[0]) * 0.10;
        var dy = (FULL.y[1] - FULL.y[0]) * 0.10;
        return Plotly.relayout(gd, {'xaxis.range': [fx - dx, fx + dx],
                                    'yaxis.range': [fy - dy, fy + dy]});
    }).then(function() {
        Plotly.Fx.hover(gd, [{curveNumber: hit.ti, pointNumber: hit.i}]);
    });
}
document.getElementById('film-search').addEventListener('change', function(e) {
    doSearch(e.target.value);
});
document.getElementById('film-search').addEventListener('keydown', function(e) {
    if (e.key === 'Enter') doSearch(e.target.value);
});

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
        legend=dict(x=1.01, y=1, xanchor="left", yanchor="top"),
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
    rho = both["x_rank"].corr(both["y_rank"])   # pearson of ranks = spearman

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
    # diagonal: audience and rubric agree, with the +/-25% disagreement band
    fig.add_shape(type="path",
                  path=(f"M 0,{-n * 0.25} L {n},{n * 0.75} "
                        f"L {n},{n * 1.25} L 0,{n * 0.25} Z"),
                  fillcolor="gray", opacity=0.06, line_width=0, layer="below")
    fig.add_shape(type="line", x0=0, y0=0, x1=n + 1, y1=n + 1,
                  line=dict(color="gray", width=1.5), opacity=0.6, layer="below")
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
        title=f"Rank vs rank: audience love vs rubric values "
              f"(Spearman \u03c1 = {rho:.2f}) — 1 = best, ranks across all "
              f"{n} films; scroll to zoom for more labels; diagonal = agreement",
        xaxis=dict(title=f"Audience rank (1 = most loved of {n})",
                   range=[n + 2, -1]),        # reversed: rank 1 at the right
        yaxis=dict(title=f"Rubric rank (1 = best values of {n})",
                   range=[n + 2, -1]),        # reversed: rank 1 at the top
        template="plotly_white",
        height=820,
        legend=dict(x=1.01, y=1, xanchor="left", yanchor="top"),
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
