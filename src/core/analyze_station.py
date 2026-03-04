"""Station analysis script — run statistical analysis on zooplankton release NetCDFs.

Usage:
    python src/core/analyze_station.py hot
    python src/core/analyze_station.py bats
    python src/core/analyze_station.py papa_P26
    python src/core/analyze_station.py all
"""

import argparse
import sys
from pathlib import Path
from textwrap import dedent

import numpy as np
import pandas as pd

from analysis import (
    compute_anomalies,
    day_night_bias,
    depth_category_bias,
    detect_outliers_iqr,
    load_release_as_dataframe,
    monthly_climatology,
    temporal_coverage,
    trend_theilsen,
)
from analysis_plots import (
    plot_anomalies,
    plot_day_night_comparison,
    plot_depth_category_comparison,
    plot_outlier_timeseries,
    plot_seasonal_climatology,
    plot_temporal_heatmap,
    plot_trend,
)

ROOT = Path(__file__).resolve().parent.parent.parent

# ── Station registry ──────────────────────────────────────────────────────────

PAPA_STATIONS = ["P08", "P12", "P16", "P20", "P26", "LBP7", "CS01"]


def _build_registry() -> dict:
    """Build the station registry mapping station_id → config."""
    registry = {
        "hot": {
            "nc_path": ROOT / "src/hot/release/hot_zooplankton_obs.nc",
            "reports_dir": ROOT / "src/hot/reports",
            "biomass_var": "biomass_dry",
            "label": "HOT (Hawaii Ocean Time-series)",
            "extra_vars": ["biomass_carbon", "biomass_nitrogen"],
            "fig_prefix": "",
        },
        "bats": {
            "nc_path": ROOT / "src/bats/release/bats_zooplankton_obs.nc",
            "reports_dir": ROOT / "src/bats/reports",
            "biomass_var": "biomass_dry",
            "label": "BATS (Bermuda Atlantic Time-series)",
            "extra_vars": ["biomass_wet"],
            "fig_prefix": "",
        },
    }

    # PAPA per-station entries
    for sid in PAPA_STATIONS:
        registry[f"papa_{sid}"] = {
            "nc_path": ROOT / f"src/papa/release/papa_{sid}_obs.nc",
            "reports_dir": ROOT / "src/papa/reports",
            "biomass_var": "biomass_dry",
            "label": f"PAPA {sid}",
            "extra_vars": [],
            "fig_prefix": f"{sid}_",
        }

    return registry


REGISTRY = _build_registry()


# ── Report generation ─────────────────────────────────────────────────────────


def _fmt(val, fmt=".4f"):
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return "N/A"
    return f"{val:{fmt}}"


def _pval(p):
    if p is None or (isinstance(p, float) and np.isnan(p)):
        return "N/A (test skipped, n < 5)"
    if p < 0.001:
        return f"{p:.2e} (**)"
    if p < 0.05:
        return f"{p:.4f} (*)"
    return f"{p:.4f}"


def generate_report(
    station_id: str,
    config: dict,
    df: pd.DataFrame,
    outlier_mask: pd.Series,
    cov: dict,
    dn_bias: dict,
    dc_bias: dict,
    clim: pd.DataFrame,
    trend: dict,
    extra_analyses: list[dict],
) -> str:
    """Generate a Markdown analysis report."""
    label = config["label"]
    fig_prefix = config["fig_prefix"]
    fig_dir = f"figures/analysis"

    lines = [
        f"# Statistical Analysis — {label}",
        "",
        f"**Station**: {station_id}  ",
        f"**Source**: `{config['nc_path'].name}`  ",
        f"**Observations**: {len(df)} (after dropping NaN biomass)  ",
        f"**Period**: {df['time'].min().strftime('%Y-%m-%d')} to {df['time'].max().strftime('%Y-%m-%d')}  ",
        "",
        "---",
        "",
        "## 1. Outlier Detection (IQR × 1.5)",
        "",
        f"- Total observations: {len(df)}",
        f"- Outliers detected: {outlier_mask.sum()}",
        f"- Outlier fraction: {outlier_mask.mean():.1%}",
        f"- Biomass Q1: {_fmt(df['biomass'].quantile(0.25))} mg/m³",
        f"- Biomass Q3: {_fmt(df['biomass'].quantile(0.75))} mg/m³",
        "",
        f"![Outliers]({fig_dir}/{fig_prefix}outliers.png)",
        "",
        "## 2. Temporal Coverage",
        "",
        f"- Year range: {cov['year_range'][0]}–{cov['year_range'][1]}",
        f"- Months with 0 observations (gaps): {cov['n_gaps']}",
        f"- Median monthly observation count: {_fmt(cov['median_monthly_obs'], '.1f')}",
        "",
        f"![Temporal heatmap]({fig_dir}/{fig_prefix}temporal_heatmap.png)",
        "",
        "## 3. Day/Night Bias",
        "",
        f"| Metric | Day | Night |",
        f"|--------|-----|-------|",
        f"| N | {dn_bias['day_n']} | {dn_bias['night_n']} |",
        f"| Median (mg/m³) | {_fmt(dn_bias['day_median'])} | {_fmt(dn_bias['night_median'])} |",
        f"| Mean (mg/m³) | {_fmt(dn_bias['day_mean'])} | {_fmt(dn_bias['night_mean'])} |",
        "",
        f"- Night/Day median ratio: {_fmt(dn_bias['median_ratio_night_day'], '.2f')}",
        f"- Mann-Whitney U p-value: {_pval(dn_bias['mannwhitney_p'])}",
        "",
        f"![Day/Night]({fig_dir}/{fig_prefix}day_night.png)",
        "",
        "## 4. Depth Category Bias",
        "",
        f"| Metric | Epipelagic only | Epi + Mesopelagic |",
        f"|--------|----------------|-------------------|",
        f"| N | {dc_bias['epipelagic_n']} | {dc_bias['mesopelagic_n']} |",
        f"| Median (mg/m³) | {_fmt(dc_bias['epipelagic_median'])} | {_fmt(dc_bias['mesopelagic_median'])} |",
        f"| Mean (mg/m³) | {_fmt(dc_bias['epipelagic_mean'])} | {_fmt(dc_bias['mesopelagic_mean'])} |",
        "",
        f"- Meso/Epi median ratio: {_fmt(dc_bias['median_ratio_meso_epi'], '.2f')}",
        f"- Mann-Whitney U p-value: {_pval(dc_bias['mannwhitney_p'])}",
        "",
        f"![Depth categories]({fig_dir}/{fig_prefix}depth_category.png)",
        "",
        "## 5. Seasonal Climatology",
        "",
        "Monthly median biomass (mg/m³):",
        "",
        "| Month | Median | Q25 | Q75 | N |",
        "|-------|--------|-----|-----|---|",
    ]

    month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                   "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    for m in range(1, 13):
        if m in clim.index and pd.notna(clim.loc[m, "median"]):
            lines.append(
                f"| {month_names[m-1]} | {_fmt(clim.loc[m, 'median'])} | "
                f"{_fmt(clim.loc[m, 'q25'])} | {_fmt(clim.loc[m, 'q75'])} | "
                f"{int(clim.loc[m, 'count'])} |"
            )
        else:
            lines.append(f"| {month_names[m-1]} | N/A | N/A | N/A | 0 |")

    lines.extend([
        "",
        f"![Seasonal climatology]({fig_dir}/{fig_prefix}seasonal_climatology.png)",
        "",
        f"![Anomalies]({fig_dir}/{fig_prefix}anomalies.png)",
        "",
        "## 6. Long-term Trend",
        "",
        f"- Number of years: {trend['n_years']}",
    ])

    if trend["test_performed"]:
        lines.extend([
            f"- Theil-Sen slope: {_fmt(trend['slope'], '+.4f')} mg/m³/year",
            f"- Mann-Kendall τ: {_fmt(trend['mk_tau'], '.3f')}",
            f"- Mann-Kendall p-value: {_pval(trend['mk_p'])}",
        ])
    else:
        lines.append("- *Trend test skipped (fewer than 5 years of data)*")

    lines.extend([
        "",
        f"![Trend]({fig_dir}/{fig_prefix}trend.png)",
    ])

    # Extra biomass variable analyses
    for extra in extra_analyses:
        lines.extend([
            "",
            f"## Extra — {extra['var_label']}",
            "",
            f"- Observations: {extra['n']}",
            f"- Median: {_fmt(extra['median'])} mg/m³",
            f"- Mean: {_fmt(extra['mean'])} mg/m³",
        ])
        if extra["trend"]["test_performed"]:
            lines.extend([
                f"- Theil-Sen slope: {_fmt(extra['trend']['slope'], '+.4f')} mg/m³/year",
                f"- Mann-Kendall p-value: {_pval(extra['trend']['mk_p'])}",
            ])
        else:
            lines.append("- *Trend test skipped (fewer than 5 years of data)*")

    lines.extend([
        "",
        "---",
        "",
        "*Report generated by `src/core/analyze_station.py`*",
    ])

    return "\n".join(lines)


# ── Pipeline ──────────────────────────────────────────────────────────────────


def analyze_station(station_id: str) -> None:
    """Run the full analysis pipeline for a single station."""
    config = REGISTRY[station_id]
    label = config["label"]
    fig_prefix = config["fig_prefix"]

    print(f"\n{'='*60}")
    print(f"  Analyzing {label}")
    print(f"{'='*60}")

    nc_path = config["nc_path"]
    if not nc_path.exists():
        print(f"  SKIP: NetCDF not found at {nc_path}")
        return

    reports_dir = config["reports_dir"]
    fig_dir = reports_dir / "figures" / "analysis"
    fig_dir.mkdir(parents=True, exist_ok=True)

    # 1. Load data
    print("  [1/7] Loading data...")
    df = load_release_as_dataframe(
        str(nc_path),
        biomass_var=config["biomass_var"],
        extra_vars=config["extra_vars"],
    )
    print(f"        → {len(df)} observations loaded")

    if df.empty:
        print("  SKIP: No valid observations.")
        return

    # 2. Outlier detection
    print("  [2/7] Detecting outliers...")
    outlier_mask = detect_outliers_iqr(df["biomass"])
    print(f"        → {outlier_mask.sum()} outliers ({outlier_mask.mean():.1%})")
    plot_outlier_timeseries(df, outlier_mask, label, fig_dir / f"{fig_prefix}outliers.png")

    # 3. Temporal coverage
    print("  [3/7] Temporal coverage...")
    cov = temporal_coverage(df)
    print(f"        → {cov['year_range'][0]}–{cov['year_range'][1]}, {cov['n_gaps']} month-gaps")
    plot_temporal_heatmap(cov["matrix"], label, fig_dir / f"{fig_prefix}temporal_heatmap.png")

    # 4. Day/night bias
    print("  [4/7] Day/night bias...")
    dn = day_night_bias(df)
    if dn["test_performed"]:
        print(f"        → night/day ratio={_fmt(dn['median_ratio_night_day'], '.2f')}, p={_fmt(dn['mannwhitney_p'])}")
    else:
        print("        → test skipped (n < 5 in one group)")
    plot_day_night_comparison(df, label, fig_dir / f"{fig_prefix}day_night.png")

    # 5. Depth category bias
    print("  [5/7] Depth category bias...")
    dc = depth_category_bias(df)
    if dc["test_performed"]:
        print(f"        → meso/epi ratio={_fmt(dc['median_ratio_meso_epi'], '.2f')}, p={_fmt(dc['mannwhitney_p'])}")
    else:
        print("        → test skipped (n < 5 in one group)")
    plot_depth_category_comparison(df, label, fig_dir / f"{fig_prefix}depth_category.png")

    # 6. Climatology + anomalies
    print("  [6/7] Seasonal climatology & anomalies...")
    clim = monthly_climatology(df)
    df_anom = compute_anomalies(df, clim)
    plot_seasonal_climatology(clim, label, fig_dir / f"{fig_prefix}seasonal_climatology.png")
    plot_anomalies(df_anom, label, fig_dir / f"{fig_prefix}anomalies.png")

    # 7. Long-term trend
    print("  [7/7] Long-term trend...")
    t = trend_theilsen(df["time"], df["biomass"])
    if t["test_performed"]:
        print(f"        → slope={t['slope']:+.4f} mg/m³/yr, τ={t['mk_tau']:.3f}, p={_fmt(t['mk_p'])}")
    else:
        print("        → trend skipped (< 5 years)")

    if t["test_performed"] and len(t["annual_medians"]) > 0:
        plot_trend(t["annual_medians"], t["slope"], t["intercept"],
                   t["mk_tau"], t["mk_p"], label,
                   fig_dir / f"{fig_prefix}trend.png")
    elif len(t["annual_medians"]) > 0:
        # Still plot the annual medians even without trend line
        plot_trend(t["annual_medians"], 0, float(t["annual_medians"].mean()),
                   0, 1.0, label, fig_dir / f"{fig_prefix}trend.png")

    # Extra variable analyses (HOT: carbon/nitrogen, BATS: wet)
    extra_analyses = []
    for extra_var in config.get("extra_vars", []):
        if extra_var in df.columns:
            ev = df[extra_var].dropna()
            if len(ev) < 2:
                continue
            ev_trend = trend_theilsen(df.loc[ev.index, "time"], ev)
            var_label = extra_var.replace("biomass_", "Biomass ").title()
            extra_analyses.append({
                "var_label": var_label,
                "n": len(ev),
                "median": float(ev.median()),
                "mean": float(ev.mean()),
                "trend": ev_trend,
            })
            print(f"        Extra: {var_label} — n={len(ev)}, median={ev.median():.4f}")

    # Write report
    report_filename = f"analysis_{station_id.replace('papa_', '')}.md" if station_id.startswith("papa_") else "analysis_report.md"
    report_path = reports_dir / report_filename

    report = generate_report(
        station_id, config, df, outlier_mask, cov, dn, dc, clim, t, extra_analyses,
    )
    report_path.write_text(report)
    print(f"  Report written to {report_path}")


# ── Main ──────────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(description="Analyze zooplankton station data.")
    parser.add_argument(
        "station",
        help="Station ID (hot, bats, papa_P26, ...) or 'all'",
    )
    args = parser.parse_args()

    target = args.station.lower()

    if target == "all":
        stations = list(REGISTRY.keys())
    elif target in REGISTRY:
        stations = [target]
    else:
        print(f"Unknown station: {target}")
        print(f"Available: {', '.join(REGISTRY.keys())}, all")
        sys.exit(1)

    for sid in stations:
        analyze_station(sid)

    print(f"\nDone — {len(stations)} station(s) analyzed.")


if __name__ == "__main__":
    main()
