"""
Kidflix Rubric Analysis
=======================
Loads data/movies.csv, computes rubric totals and tiers, and produces:
  - output/movies_scored.csv  (input + computed total + tier)
  - output/scatter_critic.png    (full view: critic Tomatometer vs rubric, quadrant-framed)
  - output/scatter_audience.png  (full view: audience Popcornmeter vs rubric, quadrant-framed)
  - output/scatter_zoom.png      (zoom on the audience-score safe-bet corner)
  - output/divergence.csv        (critic minus audience gaps, sorted)

Icon support: drop a PNG at icons/<slug>.png (slug = lowercased title,
non-alphanumerics -> underscores, e.g. icons/the_lion_king.png) OR set the
`icon` column in the CSV to a path. If present, the icon is drawn at the
movie's point; otherwise a coloured dot + label is used.
"""

from __future__ import annotations

import re
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import textalloc as ta
from adjustText import adjust_text  # fallback
from matplotlib.offsetbox import AnnotationBbox, OffsetImage

ROOT = Path(__file__).parent
DATA = ROOT / "data" / "movies.csv"
ICONS = ROOT / "icons"
OUT = ROOT / "output"

# ---------------------------------------------------------------------------
# Rubric definition — loaded from rubric.json (THE single source of truth).
# Edit rubric.json to change dimensions, weights, or tiers; every script and
# the API prompt derive from it. Weights must sum to 100.
# ---------------------------------------------------------------------------
import json as _json
RUBRIC = _json.loads((ROOT / "rubric.json").read_text())
DIMENSIONS = {k: v["max"] for k, v in RUBRIC["dimensions"].items()}
DIM_LABELS = {k: v["label"] for k, v in RUBRIC["dimensions"].items()}
assert sum(DIMENSIONS.values()) == 100, "rubric.json weights must sum to 100"

_TIER_COLOURS = ["#2e7d32", "#7cb342", "#fbc02d", "#fb8c00", "#e64a19", "#b71c1c"]
TIERS = [(name, lo, _TIER_COLOURS[i % len(_TIER_COLOURS)])
         for i, (name, lo) in enumerate(RUBRIC["tiers"])]

# Quadrant thresholds default to the dataset medians so each axis splits 50/50
# and the crosshair sits at the centre of the data (set to numbers to fix them).
RT_THRESHOLD = None      # None -> median of the x column
RUBRIC_THRESHOLD = None  # None -> median of rubric total



def place_labels(ax, xs, ys, labels, fontsize=8, scatter_sizes=None):
    """Guaranteed-non-overlapping labels via textalloc: allocates each label in
    free canvas space, aware of every point and every other label, drawing a
    thin leader line when a label had to move. Falls back to adjustText only
    if allocation errors out."""
    try:
        ta.allocate(
            ax, np.asarray(xs, float), np.asarray(ys, float), labels,
            x_scatter=np.asarray(xs, float), y_scatter=np.asarray(ys, float),
            scatter_sizes=scatter_sizes,
            textsize=fontsize,
            linecolor="gray", linewidth=0.5,
            min_distance=0.008, max_distance=0.2,
            margin=0.006, nbr_candidates=400,
            draw_lines=True, avoid_label_lines_overlap=True,
        )
    except Exception as e:  # pragma: no cover
        print(f"textalloc failed ({e}); falling back to adjustText")
        texts = [ax.text(x, y, l, fontsize=fontsize) for x, y, l in zip(xs, ys, labels)]
        adjust_text(texts, ax=ax, expand=(1.6, 2.2), force_text=(0.4, 0.9),
                    arrowprops=dict(arrowstyle="-", color="gray", lw=0.5, alpha=0.6))


def slugify(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_")


def tier_for(score: float) -> str:
    for name, lower, _ in TIERS:
        if score >= lower:
            return name
    return "F"


def tier_colour(tier: str) -> str:
    return next(c for name, _, c in TIERS if name == tier)


def load_and_score(data_path: Path = DATA) -> pd.DataFrame:
    df = pd.read_csv(data_path)
    for dim, max_pts in DIMENSIONS.items():
        bad = df[(df[dim] < 0) | (df[dim] > max_pts)]
        if not bad.empty:
            raise ValueError(f"{dim} out of range 0-{max_pts}: {bad['title'].tolist()}")
    df["total"] = df[list(DIMENSIONS)].sum(axis=1)
    df["tier"] = df["total"].apply(tier_for)
    return df.sort_values("total", ascending=False).reset_index(drop=True)


def resolve_icon(row: pd.Series) -> Path | None:
    if isinstance(row.get("icon"), str) and row["icon"].strip():
        p = ROOT / row["icon"]
        if p.exists():
            return p
    p = ICONS / f"{slugify(row['title'])}.png"
    return p if p.exists() else None


def _draw(df: pd.DataFrame, ax, label_fontsize: float, icon_zoom: float,
          x_col: str = "rt_critic") -> None:
    """Scatter points (or icons) plus non-overlapping labels."""
    xs, ys, labels = [], [], []
    for _, row in df.iterrows():
        x, y = row[x_col], row["total"]
        icon = resolve_icon(row)
        if icon is not None:
            img = plt.imread(icon)
            ab = AnnotationBbox(OffsetImage(img, zoom=icon_zoom), (x, y), frameon=False)
            ax.add_artist(ab)
        else:
            ax.scatter(x, y, s=70, color=tier_colour(row["tier"]),
                       edgecolors="black", linewidths=0.5, zorder=3)
        xs.append(x); ys.append(y); labels.append(row["title"])
    place_labels(ax, xs, ys, labels, fontsize=label_fontsize,
                 scatter_sizes=np.full(len(xs), 70.0))


def _tier_bands(ax, x_for_letter: float) -> None:
    upper = 104
    for name, lower, colour in TIERS:
        ax.axhspan(lower, upper, color=colour, alpha=0.06)
        ax.text(x_for_letter, (lower + upper) / 2, name, fontsize=20,
                fontweight="bold", color=colour, alpha=0.45, va="center")
        upper = lower


def _plotable(df: pd.DataFrame, x_col: str) -> pd.DataFrame:
    d = df.dropna(subset=[x_col, "total"])
    if len(d) < len(df):
        print(f"  note: {len(df)-len(d)} film(s) missing {x_col}; "
              f"scored but not plotted until metadata is filled")
    return d


def plot_full(df: pd.DataFrame, x_col: str = "rt_critic",
              x_label: str = "Rotten Tomatoes — critics (Tomatometer %)",
              fname: str = "scatter_critic.png") -> Path:
    df = _plotable(df, x_col)
    fig, ax = plt.subplots(figsize=(19, 13))
    _tier_bands(ax, x_for_letter=1.5)

    # quadrant crosshairs at the data medians (or fixed thresholds if set)
    tx = RT_THRESHOLD if RT_THRESHOLD is not None else df[x_col].median()
    ty = RUBRIC_THRESHOLD if RUBRIC_THRESHOLD is not None else df["total"].median()
    ax.axvline(tx, color="gray", ls="--", lw=1.2, alpha=0.7)
    ax.axhline(ty, color="gray", ls="--", lw=1.2, alpha=0.7)

    # centre the view on the crosshair: pad so the crosshair is the visual centre,
    # without clipping any data
    x_lo, x_hi = df[x_col].min(), df[x_col].max()
    y_lo, y_hi = df["total"].min(), df["total"].max()
    dx = max(tx - x_lo, x_hi - tx) + 4
    dy = max(ty - y_lo, y_hi - ty) + 5
    ax.set_xlim(tx - dx, tx + dx)
    ax.set_ylim(max(ty - dy, -2), min(ty + dy, 104))

    # label each quadrant at the centre of its region, with its share of the data
    n = len(df)
    counts = {
        "safe": ((df[x_col] >= tx) & (df["total"] >= ty)).sum(),
        "gems": ((df[x_col] < tx) & (df["total"] >= ty)).sum(),
        "corr": ((df[x_col] >= tx) & (df["total"] < ty)).sum(),
        "skip": ((df[x_col] < tx) & (df["total"] < ty)).sum(),
    }
    q_style = dict(fontsize=12, fontweight="bold", alpha=0.6,
                   ha="center", va="center",
                   bbox=dict(boxstyle="round,pad=0.45", fc="white", ec="gray", alpha=0.75))
    x_left, x_right = tx - dx / 2, tx + dx / 2
    y_top = min(ty + dy, 104) - (min(ty + dy, 104) - ty) / 2
    y_bot = max(ty - dy, -2) + (ty - max(ty - dy, -2)) / 2
    ax.text(x_right, y_top, f"SAFE BETS ({counts['safe']}/{n})\nkids love it, values intact",
            color="#2e7d32", zorder=1, **q_style)
    ax.text(x_left, y_top, f"HIDDEN GEMS ({counts['gems']}/{n})\ngreat values, less acclaimed",
            color="#1565c0", zorder=1, **q_style)
    ax.text(x_right, y_bot, f"BELOVED BUT CORROSIVE ({counts['corr']}/{n})\nacclaimed, values-poor",
            color="#b71c1c", zorder=1, **q_style)
    ax.text(x_left, y_bot, f"SKIP ({counts['skip']}/{n})\nneither", color="#616161",
            zorder=1, **q_style)

    _draw(df, ax, label_fontsize=10, icon_zoom=0.35, x_col=x_col)

    ax.set_xlabel(x_label, fontsize=12)
    ax.set_ylabel("Rubric score (/100)", fontsize=12)
    ax.set_title("Critical acclaim vs. what it actually teaches your kid", fontsize=15, pad=14)
    ax.grid(alpha=0.2)

    OUT.mkdir(exist_ok=True)
    out = OUT / fname
    fig.tight_layout()
    fig.savefig(out, dpi=200)
    plt.close(fig)
    return out


def plot_zoom(df: pd.DataFrame, rt_min: int = 78, rubric_min: int = 72,
              x_col: str = "rt_audience", fname: str = "scatter_zoom.png") -> Path:
    sub = _plotable(df, x_col)
    sub = sub[(sub[x_col] >= rt_min) & (sub["total"] >= rubric_min)]
    fig, ax = plt.subplots(figsize=(15, 10))
    _tier_bands(ax, x_for_letter=rt_min + 0.4)
    _draw(sub, ax, label_fontsize=11, icon_zoom=0.45, x_col=x_col)
    ax.set_xlabel("Rotten Tomatoes — audience (Popcornmeter %)", fontsize=12)
    ax.set_ylabel("Rubric score (/100)", fontsize=12)
    ax.set_title(f"Zoom: the safe-bet corner (audience ≥ {rt_min}, rubric ≥ {rubric_min})",
                 fontsize=15, pad=14)
    ax.set_xlim(rt_min - 1, 102)
    ax.set_ylim(rubric_min - 1, 100)
    ax.grid(alpha=0.2)

    out = OUT / fname
    fig.tight_layout()
    fig.savefig(out, dpi=200)
    plt.close(fig)
    return out


def plot_rank(df: pd.DataFrame, x_col: str = "rt_audience",
              fname: str = "scatter_rank.png") -> Path:
    """Rank-vs-rank view: strips away the score distributions and shows the pure
    ordinal relationship. Rank 1 = best. Points on the diagonal are movies the
    audience and the rubric agree about; distance from the diagonal = disagreement."""
    d = _plotable(df, x_col).copy()
    n = len(d)
    d["x_rank"] = d[x_col].rank(ascending=False, method="min")
    d["y_rank"] = d["total"].rank(ascending=False, method="min")

    fig, ax = plt.subplots(figsize=(19, 19))

    # agreement diagonal + disagreement shading
    ax.plot([1, n], [1, n], color="gray", lw=1.5, alpha=0.6, ls="-")
    ax.fill_between([1, n], [1 - n * 0.25, n * 0.75], [1 + n * 0.25, n * 1.25],
                    color="gray", alpha=0.06)

    # quadrant crosshairs at the rank midpoint -> guaranteed 50/50 per axis
    mid = (n + 1) / 2
    ax.axvline(mid, color="gray", ls="--", lw=1.2, alpha=0.7)
    ax.axhline(mid, color="gray", ls="--", lw=1.2, alpha=0.7)

    q_style = dict(fontsize=12, fontweight="bold", alpha=0.6, ha="center",
                   va="center", zorder=1,
                   bbox=dict(boxstyle="round,pad=0.45", fc="white", ec="gray", alpha=0.75))
    lo, hi = mid / 2, mid + (n - mid) / 2
    ax.text(lo, lo, "SAFE BETS\ntop half on both", color="#2e7d32", **q_style)
    ax.text(hi, lo, "HIDDEN GEMS\nrubric loves, audience shrugs", color="#1565c0", **q_style)
    ax.text(lo, hi, "BELOVED BUT CORROSIVE\naudience loves, rubric objects", color="#b71c1c", **q_style)
    ax.text(hi, hi, "SKIP\nbottom half on both", color="#616161", **q_style)

    xs, ys, labels = [], [], []
    for _, row in d.iterrows():
        x, y = row["x_rank"], row["y_rank"]
        icon = resolve_icon(row)
        if icon is not None:
            img = plt.imread(icon)
            ab = AnnotationBbox(OffsetImage(img, zoom=0.35), (x, y), frameon=False)
            ax.add_artist(ab)
        else:
            ax.scatter(x, y, s=70, color=tier_colour(row["tier"]),
                       edgecolors="black", linewidths=0.5, zorder=3)
        xs.append(x); ys.append(y); labels.append(row["title"])
    # set limits BEFORE allocation so textalloc sees the final canvas
    ax.set_xlim(n + 2, -1)
    ax.set_ylim(n + 2, -1)
    place_labels(ax, xs, ys, labels, fontsize=10,
                 scatter_sizes=np.full(len(xs), 70.0))

    # rank 1 at top-right so "best on both" reads as up-and-right
    ax.set_xlabel(f"Audience rank (1 = most loved of {n})", fontsize=12)
    ax.set_ylabel(f"Rubric rank (1 = best values of {n})", fontsize=12)
    rho = d[x_col].corr(d["total"], method="spearman")
    ax.set_title(f"Rank vs rank: audience love vs rubric values (Spearman ρ = {rho:.2f})",
                 fontsize=15, pad=14)
    ax.grid(alpha=0.2)
    ax.set_aspect("equal")

    out = OUT / fname
    fig.tight_layout()
    fig.savefig(out, dpi=200)
    plt.close(fig)
    return out


def run(data_path: Path, prefix: str = "") -> pd.DataFrame:
    """Full pipeline for one dataset. prefix namespaces every output file so
    datasets never mix: '' -> kids (default), 'adult_' -> the adult set."""
    df = load_and_score(data_path)
    OUT.mkdir(exist_ok=True)
    df["critic_minus_audience"] = df["rt_critic"] - df["rt_audience"]
    df["safe_bet_index"] = df["rt_audience"] * df["total"]
    df.to_csv(OUT / f"{prefix}movies_scored.csv", index=False)
    print(f"Wrote {OUT / (prefix + 'movies_scored.csv')}")
    print(f"Wrote {plot_full(df, fname=f'{prefix}scatter_critic.png')}")
    print(f"Wrote {plot_full(df, x_col='rt_audience', fname=f'{prefix}scatter_audience.png', x_label='Rotten Tomatoes — audience (Popcornmeter %)')}")
    print(f"Wrote {plot_zoom(df, fname=f'{prefix}scatter_zoom.png')}")
    print(f"Wrote {plot_rank(df, fname=f'{prefix}scatter_rank.png')}")
    div = df[["title", "rt_critic", "rt_audience", "critic_minus_audience", "total", "tier"]] \
        .sort_values("critic_minus_audience", ascending=False)
    div.to_csv(OUT / f"{prefix}divergence.csv", index=False)
    print(f"{len(df)} movies | Spearman(audience, rubric) = "
          f"{df['rt_audience'].corr(df['total'], method='spearman'):.2f}")
    return df




def run_comparison(kids: pd.DataFrame, adult: pd.DataFrame) -> None:
    """Cross-segment comparison. Every output here is prefixed compare_ and
    exists ONLY for the kids-vs-adult question; the per-segment outputs above
    remain the filtered, single-genre reports."""
    kids = kids.assign(segment="kids")
    adult = adult.assign(segment="adult")
    both = pd.concat([kids, adult], ignore_index=True)
    both.to_csv(OUT / "compare_combined_scored.csv", index=False)

    # --- dimension profile: mean score as % of each dimension's maximum ---
    prof = {}
    for seg, d in both.groupby("segment"):
        prof[seg] = {dim: 100 * d[dim].mean() / mx for dim, mx in DIMENSIONS.items()}
        prof[seg]["TOTAL"] = d["total"].mean()
    prof_df = pd.DataFrame(prof)
    prof_df.to_csv(OUT / "compare_dimension_profile.csv")

    dims = list(DIMENSIONS)
    labels = [DIM_LABELS[d].replace(" & ", " &\n").replace(" ", "\n", 1) for d in dims]
    x = range(len(dims))
    w = 0.38
    fig, ax = plt.subplots(figsize=(13, 7))
    kvals = [prof["kids"][d] for d in dims]
    avals = [prof["adult"][d] for d in dims]
    ax.bar([i - w / 2 for i in x], kvals, w, label=f"Kids films (n={len(kids)})",
           color="#7cb342", edgecolor="black", linewidth=0.5)
    ax.bar([i + w / 2 for i in x], avals, w, label=f"Adult films (n={len(adult)})",
           color="#5c6bc0", edgecolor="black", linewidth=0.5)
    for i, (k, a) in enumerate(zip(kvals, avals)):
        ax.text(i - w / 2, k + 1.2, f"{k:.0f}", ha="center", fontsize=9)
        ax.text(i + w / 2, a + 1.2, f"{a:.0f}", ha="center", fontsize=9)
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels)
    ax.set_ylabel("Mean score, % of dimension maximum")
    ax.set_ylim(0, 105)
    ax.set_title("What each genre actually teaches: rubric dimension profile, kids vs adult films")
    ax.legend()
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(OUT / "compare_dimensions.png", dpi=200)
    plt.close(fig)
    print(f"Wrote {OUT / 'compare_dimensions.png'}")

    # --- combined rank view coloured by segment ---
    n = len(both)
    both["x_rank"] = both["rt_audience"].rank(ascending=False, method="min")
    both["y_rank"] = both["total"].rank(ascending=False, method="min")
    fig, ax = plt.subplots(figsize=(19, 19))
    ax.plot([1, n], [1, n], color="gray", lw=1.5, alpha=0.6)
    mid = (n + 1) / 2
    ax.axvline(mid, color="gray", ls="--", lw=1.2, alpha=0.7)
    ax.axhline(mid, color="gray", ls="--", lw=1.2, alpha=0.7)
    xs, ys, labels = [], [], []
    for _, row in both.iterrows():
        colour = "#7cb342" if row["segment"] == "kids" else "#5c6bc0"
        marker = "o" if row["segment"] == "kids" else "s"
        ax.scatter(row["x_rank"], row["y_rank"], s=75, color=colour, marker=marker,
                   edgecolors="black", linewidths=0.5, zorder=3)
        xs.append(row["x_rank"]); ys.append(row["y_rank"]); labels.append(row["title"])
    ax.set_xlim(n + 2, -1)
    ax.set_ylim(n + 2, -1)
    place_labels(ax, xs, ys, labels, fontsize=10,
                 scatter_sizes=np.full(len(xs), 75.0))
    ax.scatter([], [], color="#7cb342", marker="o", label="Kids film")
    ax.scatter([], [], color="#5c6bc0", marker="s", label="Adult film")
    ax.legend(fontsize=12, loc="lower left")
    ax.set_xlabel(f"Audience rank (1 = most loved of {n})", fontsize=12)
    ax.set_ylabel(f"Rubric rank (1 = best values of {n})", fontsize=12)
    ax.set_title("Combined rank view: do we hold kids' stories to a lower values bar?",
                 fontsize=15, pad=14)
    ax.grid(alpha=0.2)
    ax.set_aspect("equal")
    fig.tight_layout()
    fig.savefig(OUT / "compare_rank.png", dpi=200)
    plt.close(fig)
    print(f"Wrote {OUT / 'compare_rank.png'}")

    # --- headline stats ---
    print("\nDimension profile (mean % of max):")
    print(prof_df.round(1).to_string())


def plot_top_revenue(kids: pd.DataFrame, adult: pd.DataFrame, n: int = 10) -> Path:
    """Absolute-values scatter of the top-n highest-grossing films per segment:
    audience score vs raw rubric total, point size ~ worldwide revenue."""
    k = kids.nlargest(n, "revenue_adj_musd").assign(segment="kids")
    a = adult.nlargest(n, "revenue_adj_musd").assign(segment="adult")
    both = pd.concat([k, a], ignore_index=True)
    both.to_csv(OUT / "compare_top_revenue.csv", index=False)

    fig, ax = plt.subplots(figsize=(15, 11))
    _tier_bands(ax, x_for_letter=41)

    xs, ys, labels, sizes = [], [], [], []
    for _, row in both.iterrows():
        colour = "#7cb342" if row["segment"] == "kids" else "#5c6bc0"
        marker = "o" if row["segment"] == "kids" else "s"
        size = 60 + row["revenue_adj_musd"] / 6  # bubble area tracks revenue
        ax.scatter(row["rt_audience"], row["total"], s=size, color=colour,
                   marker=marker, edgecolors="black", linewidths=0.7,
                   alpha=0.85, zorder=3)
        xs.append(row["rt_audience"]); ys.append(row["total"])
        labels.append(f"{row['title']} (${row['revenue_adj_musd']:.0f}M adj)")
        sizes.append(size)
    ax.set_xlim(40, 103)
    ax.set_ylim(0, 104)
    place_labels(ax, xs, ys, labels, fontsize=11,
                 scatter_sizes=np.asarray(sizes, float))

    ax.scatter([], [], color="#7cb342", marker="o", s=100, label="Kids film (top 10 by revenue)")
    ax.scatter([], [], color="#5c6bc0", marker="s", s=100, label="Adult film (top 10 by revenue)")
    ax.legend(fontsize=11, loc="lower left")
    ax.set_xlabel("Rotten Tomatoes — audience (Popcornmeter %)", fontsize=12)
    ax.set_ylabel("Rubric score (/100)", fontsize=12)
    ax.set_title("The 10 biggest earners per segment: absolute scores, bubble size = worldwide gross, inflation-adjusted to 2026 USD",
                 fontsize=14, pad=14)
    ax.grid(alpha=0.2)

    out = OUT / "compare_top_revenue.png"
    fig.tight_layout()
    fig.savefig(out, dpi=200)
    plt.close(fig)
    return out


def main() -> None:
    print("=== Kids dataset ===")
    run(DATA)

    kids_df = load_and_score(DATA)
    adult_path = ROOT / "data" / "movies_adult.csv"
    if adult_path.exists():
        print("\n=== Adult / cult-classic dataset (separate report) ===")
        adult_df = run(adult_path, prefix="adult_")
        print("\n=== Cross-segment comparison (compare_ outputs only) ===")
        run_comparison(kids_df, adult_df)
        print(f"Wrote {plot_top_revenue(kids_df, adult_df)}")


if __name__ == "__main__":
    main()
