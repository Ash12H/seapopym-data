"""Inter-station comparison of zooplankton biomass.

Usage:
    python src/core/compare_stations.py

Loads all release NetCDFs (HOT, BATS, 7 PAPA stations), normalises biomass
(z-score), and generates comparative figures and a report.
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from analysis import (
    load_release_as_dataframe,
    monthly_climatology,
    trend_theilsen,
)

sns.set_theme(style="whitegrid")

ROOT = Path(__file__).resolve().parent.parent.parent

# ── Station definitions ───────────────────────────────────────────────────────

STATIONS = {
    "HOT": {
        "nc_path": ROOT / "src/hot/release/hot_zooplankton_obs.nc",
        "biomass_var": "biomass_dry",
        "color": "#e41a1c",
    },
    "BATS": {
        "nc_path": ROOT / "src/bats/release/bats_zooplankton_obs.nc",
        "biomass_var": "biomass_dry",
        "color": "#377eb8",
    },
}

PAPA_IDS = ["P08", "P12", "P16", "P20", "P26", "LBP7", "CS01"]
_PAPA_COLORS = ["#4daf4a", "#984ea3", "#ff7f00", "#a65628", "#f781bf", "#999999", "#66c2a5"]

for i, sid in enumerate(PAPA_IDS):
    STATIONS[f"PAPA {sid}"] = {
        "nc_path": ROOT / f"src/papa/release/papa_{sid}_obs.nc",
        "biomass_var": "biomass_dry",
        "color": _PAPA_COLORS[i],
    }

OUTPUT_DIR = ROOT / "src/comparison/reports"
FIG_DIR = OUTPUT_DIR / "figures"


# ── Helpers ───────────────────────────────────────────────────────────────────


def _savefig(fig: plt.Figure, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved {path}")


def load_all_stations() -> dict[str, pd.DataFrame]:
    """Load all stations into a dict of DataFrames."""
    data = {}
    for name, cfg in STATIONS.items():
        if not cfg["nc_path"].exists():
            print(f"  SKIP: {name} — file not found")
            continue
        df = load_release_as_dataframe(str(cfg["nc_path"]), cfg["biomass_var"])
        if df.empty:
            print(f"  SKIP: {name} — no valid observations")
            continue
        df["station"] = name
        data[name] = df
        print(f"  Loaded {name}: {len(df)} obs")
    return data


# ── Figures ───────────────────────────────────────────────────────────────────


def plot_normalized_timeseries(data: dict[str, pd.DataFrame]) -> None:
    """Overlay z-score normalized annual median biomass for all stations."""
    fig, ax = plt.subplots(figsize=(14, 6))

    for name, df in data.items():
        annual = df.groupby(df["time"].dt.year)["biomass"].median()
        if len(annual) < 3:
            continue
        z = (annual - annual.mean()) / annual.std() if annual.std() > 0 else annual * 0
        color = STATIONS[name]["color"]
        ax.plot(z.index, z.values, "o-", label=name, color=color, markersize=4, alpha=0.8)

    ax.axhline(0, color="black", linewidth=0.5)
    ax.set_title("Normalized biomass trends (z-score of annual medians)")
    ax.set_xlabel("Year")
    ax.set_ylabel("Z-score")
    ax.legend(fontsize=8, ncol=3, loc="upper left")
    _savefig(fig, FIG_DIR / "normalized_timeseries.png")


def plot_seasonal_comparison(data: dict[str, pd.DataFrame]) -> None:
    """Overlay monthly climatologies for all stations."""
    fig, ax = plt.subplots(figsize=(12, 6))

    month_labels = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    for name, df in data.items():
        clim = monthly_climatology(df)
        color = STATIONS[name]["color"]
        ax.plot(clim.index, clim["median"], "o-", label=name, color=color, markersize=4, alpha=0.8)

    ax.set_xticks(range(1, 13))
    ax.set_xticklabels(month_labels)
    ax.set_title("Seasonal climatology comparison (monthly median biomass)")
    ax.set_xlabel("Month")
    ax.set_ylabel("Biomass dry (mg/m³)")
    ax.legend(fontsize=8, ncol=3, loc="upper left")
    _savefig(fig, FIG_DIR / "seasonal_comparison.png")


def plot_trend_comparison(trends: dict[str, dict]) -> None:
    """Bar chart of Theil-Sen slopes with significance markers."""
    # Filter to stations with valid trends
    valid = {k: v for k, v in trends.items() if v["test_performed"]}
    if not valid:
        print("  No valid trends to compare.")
        return

    names = list(valid.keys())
    slopes = [valid[n]["slope"] for n in names]
    p_values = [valid[n]["mk_p"] for n in names]
    colors = [STATIONS[n]["color"] for n in names]

    fig, ax = plt.subplots(figsize=(12, 6))
    bars = ax.bar(range(len(names)), slopes, color=colors, alpha=0.8)

    # Add significance markers
    for i, (bar, p) in enumerate(zip(bars, p_values)):
        marker = "**" if p < 0.01 else "*" if p < 0.05 else ""
        if marker:
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(),
                    marker, ha="center", va="bottom", fontsize=12, fontweight="bold")

    ax.set_xticks(range(len(names)))
    ax.set_xticklabels(names, rotation=45, ha="right", fontsize=9)
    ax.axhline(0, color="black", linewidth=0.5)
    ax.set_title("Theil-Sen trend slopes comparison (* p<0.05, ** p<0.01)")
    ax.set_ylabel("Slope (mg/m³/year)")
    fig.tight_layout()
    _savefig(fig, FIG_DIR / "trend_comparison.png")


def plot_biomass_distributions(data: dict[str, pd.DataFrame]) -> None:
    """Box plots of raw biomass distributions across stations."""
    all_df = pd.concat(data.values(), ignore_index=True)

    fig, ax = plt.subplots(figsize=(14, 6))
    order = list(data.keys())
    palette = {name: STATIONS[name]["color"] for name in order}

    sns.boxplot(data=all_df, x="station", y="biomass", hue="station", order=order,
                palette=palette, ax=ax, showfliers=False, legend=False)
    ax.set_title("Biomass distribution by station (outliers hidden)")
    ax.set_xlabel("")
    ax.set_ylabel("Biomass dry (mg/m³)")
    ax.tick_params(axis="x", rotation=45)
    for label in ax.get_xticklabels():
        label.set_ha("right")
        label.set_fontsize(9)
    fig.tight_layout()
    _savefig(fig, FIG_DIR / "biomass_distributions.png")


# ── Report ────────────────────────────────────────────────────────────────────


def generate_comparison_report(
    data: dict[str, pd.DataFrame],
    trends: dict[str, dict],
) -> str:
    lines = [
        "# Inter-Station Comparison Report",
        "",
        f"**Stations analyzed**: {len(data)}  ",
        "",
        "---",
        "",
        "## 1. Station Summary",
        "",
        "| Station | N obs | Period | Median biomass (mg/m³) | Mean biomass (mg/m³) |",
        "|---------|-------|--------|----------------------|---------------------|",
    ]

    for name, df in data.items():
        period = f"{df['time'].min().strftime('%Y')}–{df['time'].max().strftime('%Y')}"
        lines.append(
            f"| {name} | {len(df)} | {period} | "
            f"{df['biomass'].median():.2f} | {df['biomass'].mean():.2f} |"
        )

    lines.extend([
        "",
        "![Biomass distributions](figures/biomass_distributions.png)",
        "",
        "## 2. Normalized Time Series",
        "",
        "Annual median biomass normalized to z-scores for cross-station comparison.",
        "",
        "![Normalized time series](figures/normalized_timeseries.png)",
        "",
        "## 3. Seasonal Climatology Comparison",
        "",
        "![Seasonal comparison](figures/seasonal_comparison.png)",
        "",
        "## 4. Trend Comparison",
        "",
        "| Station | Theil-Sen slope | Mann-Kendall τ | p-value | N years |",
        "|---------|----------------|---------------|---------|---------|",
    ])

    for name in data:
        t = trends.get(name, {})
        if t.get("test_performed"):
            sig = "**" if t["mk_p"] < 0.01 else "*" if t["mk_p"] < 0.05 else ""
            p_str = f"{t['mk_p']:.4f}" if t["mk_p"] >= 0.001 else f"{t['mk_p']:.2e}"
            lines.append(
                f"| {name} | {t['slope']:+.4f} | {t['mk_tau']:.3f} | "
                f"{p_str} {sig} | {t['n_years']} |"
            )
        else:
            lines.append(f"| {name} | N/A | N/A | N/A | {t.get('n_years', 0)} |")

    lines.extend([
        "",
        "![Trend comparison](figures/trend_comparison.png)",
        "",
        "---",
        "",
        "*Report generated by `src/core/compare_stations.py`*",
    ])

    return "\n".join(lines)


# ── Main ──────────────────────────────────────────────────────────────────────


def main():
    print("Loading all stations...")
    data = load_all_stations()

    if not data:
        print("No stations loaded. Exiting.")
        return

    FIG_DIR.mkdir(parents=True, exist_ok=True)

    # Compute trends for all stations
    print("\nComputing trends...")
    trends = {}
    for name, df in data.items():
        t = trend_theilsen(df["time"], df["biomass"])
        trends[name] = t
        if t["test_performed"]:
            print(f"  {name}: slope={t['slope']:+.4f}, τ={t['mk_tau']:.3f}, p={t['mk_p']:.4f}")
        else:
            print(f"  {name}: trend skipped (< 5 years)")

    # Generate figures
    print("\nGenerating figures...")
    plot_normalized_timeseries(data)
    plot_seasonal_comparison(data)
    plot_trend_comparison(trends)
    plot_biomass_distributions(data)

    # Write report
    report = generate_comparison_report(data, trends)
    report_path = OUTPUT_DIR / "comparison_report.md"
    report_path.write_text(report)
    print(f"\nReport written to {report_path}")

    print(f"\nDone — {len(data)} stations compared.")


if __name__ == "__main__":
    main()
