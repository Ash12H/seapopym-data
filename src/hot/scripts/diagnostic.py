"""
HOT Observation Diagnostic Script
Produces 4 diagnostic figures for the HOT zooplankton Parquet release.

1. Tow depth vs pelagic layer depths (coverage diagnostic)
2. Day/night biomass conditioned on layer coverage
3. Monthly climatology with std envelope
4. Functional group decomposition (G0/G1) from day/night × layer concentrations
"""

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
FIGURES_DIR = PROJECT_ROOT / "src" / "hot" / "reports" / "figures"
PARQUET = PROJECT_ROOT / "src" / "hot" / "release" / "hot_zooplankton_obs.parquet"


def load():
    df = pd.read_parquet(PARQUET)
    df["time"] = pd.to_datetime(df["time"])
    df["month"] = df["time"].dt.month
    df["year"] = df["time"].dt.year
    return df


# ---------------------------------------------------------------------------
# Figure 1: Tow depth vs pelagic layer boundaries
# ---------------------------------------------------------------------------
def fig_tow_vs_layers(df: pd.DataFrame):
    """Scatter of tow_depth_max over time with layer depth boundaries."""
    valid = df.dropna(subset=["zeu"]).sort_values("time")

    fig, ax = plt.subplots(figsize=(14, 5))

    # Tow depths as scatter
    colors = {"day": "#F59E0B", "night": "#3B82F6"}
    for dn in ["day", "night"]:
        sub = valid[valid["day_night"] == dn]
        ax.scatter(
            sub["time"], sub["tow_depth_max"],
            c=colors[dn], s=8, alpha=0.5, label=f"tow ({dn})", zorder=3,
        )

    # Layer boundaries as lines
    ax.plot(valid["time"], valid["layer_depth_surface"], "k-", lw=1.2, label="layer surface (1.5×Zeu)")
    ax.plot(valid["time"], valid["layer_depth_migrant"], "k--", lw=0.8, alpha=0.5, label="layer migrant (4.5×Zeu)")

    # Fill zones
    ax.fill_between(
        valid["time"], 0, valid["layer_depth_surface"],
        alpha=0.08, color="green", label="surface layer",
    )
    ax.fill_between(
        valid["time"], valid["layer_depth_surface"], valid["layer_depth_migrant"],
        alpha=0.05, color="blue", label="migrant layer",
    )

    ax.invert_yaxis()
    ax.set_ylabel("Depth (m)")
    ax.set_xlabel("Date")
    ax.set_title("HOT — Tow depth vs pelagic layer boundaries", fontweight="bold")
    ax.legend(loc="lower right", fontsize=8, ncol=3)
    ax.grid(True, alpha=0.2)

    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "diag_tow_vs_layers.png", dpi=150)
    plt.close(fig)
    print("  1. diag_tow_vs_layers.png")


# ---------------------------------------------------------------------------
# Figure 2: Day/night boxplot conditioned on coverage
# ---------------------------------------------------------------------------
def fig_day_night_by_coverage(df: pd.DataFrame):
    """Boxplot of biomass day vs night, split by whether tow reaches migrant layer."""
    valid = df.dropna(subset=["zeu"]).copy()

    valid["coverage"] = np.where(
        valid["tow_depth_max"] < valid["layer_depth_surface"],
        "surface only",
        "surface + migrant",
    )

    fig, axes = plt.subplots(1, 2, figsize=(12, 5), sharey=True)

    for i, cov in enumerate(["surface only", "surface + migrant"]):
        ax = axes[i]
        sub = valid[valid["coverage"] == cov]

        data_day = sub.loc[sub["day_night"] == "day", "biomass_dry"]
        data_night = sub.loc[sub["day_night"] == "night", "biomass_dry"]

        bp = ax.boxplot(
            [data_day.dropna(), data_night.dropna()],
            tick_labels=["day", "night"],
            patch_artist=True,
            widths=0.5,
            showfliers=True,
            flierprops=dict(marker=".", markersize=3, alpha=0.3),
        )
        bp["boxes"][0].set_facecolor("#F59E0B")
        bp["boxes"][0].set_alpha(0.6)
        bp["boxes"][1].set_facecolor("#3B82F6")
        bp["boxes"][1].set_alpha(0.6)

        n_day, n_night = len(data_day), len(data_night)
        med_day, med_night = data_day.median(), data_night.median()
        ratio = med_night / med_day if med_day > 0 else float("nan")

        ax.set_title(f"{cov}\n(n={n_day}d/{n_night}n, ratio N/D={ratio:.2f})", fontsize=10)
        ax.set_ylabel("Biomass dry (mg/m³)" if i == 0 else "")
        ax.grid(True, alpha=0.2, axis="y")

    fig.suptitle("HOT — Day/night biomass by tow coverage", fontweight="bold", y=1.02)
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "diag_day_night_coverage.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("  2. diag_day_night_coverage.png")


# ---------------------------------------------------------------------------
# Figure 3: Monthly climatology + std envelope + sampling heatmap
# ---------------------------------------------------------------------------
def fig_climatology(df: pd.DataFrame):
    """Monthly climatology with std envelope and sampling heatmap."""
    fig, axes = plt.subplots(2, 1, figsize=(12, 8), gridspec_kw={"height_ratios": [3, 1]})

    # --- Top: climatology ---
    ax = axes[0]
    months = np.arange(1, 13)
    month_labels = ["J", "F", "M", "A", "M", "J", "J", "A", "S", "O", "N", "D"]

    for dn, color, offset in [("day", "#F59E0B", -0.15), ("night", "#3B82F6", 0.15)]:
        sub = df[df["day_night"] == dn]
        grouped = sub.groupby("month")["biomass_dry"]
        means = grouped.mean()
        stds = grouped.std()
        counts = grouped.count()

        x = months + offset
        m = means.reindex(months).values
        s = stds.reindex(months).values

        ax.errorbar(x, m, yerr=s, fmt="o-", color=color, capsize=3, capthick=1,
                    markersize=5, label=f"{dn} (mean ± std)", alpha=0.8)
        ax.fill_between(x, m - s, m + s, color=color, alpha=0.1)

    ax.set_xticks(months)
    ax.set_xticklabels(month_labels)
    ax.set_ylabel("Biomass dry (mg/m³)")
    ax.set_title("HOT — Monthly climatology", fontweight="bold")
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.2)

    # --- Bottom: sampling heatmap (year × month) ---
    ax2 = axes[1]
    pivot = df.groupby(["year", "month"]).size().unstack(fill_value=0)
    # Ensure all months present
    for m in range(1, 13):
        if m not in pivot.columns:
            pivot[m] = 0
    pivot = pivot[sorted(pivot.columns)]

    im = ax2.pcolormesh(
        pivot.columns - 0.5, pivot.index - 0.5, pivot.values,
        cmap="YlOrBr", vmin=0,
    )
    ax2.set_xlabel("Month")
    ax2.set_ylabel("Year")
    ax2.set_xticks(months)
    ax2.set_xticklabels(month_labels)
    ax2.set_title("Sampling density (tows per month)", fontsize=10)
    fig.colorbar(im, ax=ax2, label="# tows", shrink=0.8)

    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "diag_climatology.png", dpi=150)
    plt.close(fig)
    print("  3. diag_climatology.png")


# ---------------------------------------------------------------------------
# Figure 4: Functional group decomposition (G0 / G1) from day/night × layer
# ---------------------------------------------------------------------------
def fig_group_decomposition(df: pd.DataFrame):
    """Estimate G0 (resident) and G1 (migrant) from day/night concentrations.

    Logic (DVM model):
      - Surface layer, day   → G0 only (migrants are deep)
      - Surface layer, night → G0 + G1 (migrants came up)
      - Migrant layer, day   → G1 (migrants are there)
      - Migrant layer, night → ~empty (migrants went up)

    Therefore:
      G0 = C_surface_day
      G1 = C_surface_night - C_surface_day  (from surface uplift)
      G1 ≈ C_migrant_day                    (consistency check)
    """
    valid = df.dropna(subset=["zeu"]).copy()

    # Classify tows by coverage
    valid["covers_migrant"] = valid["tow_depth_max"] >= valid["layer_depth_surface"]

    # --- Surface-only tows: their biomass_dry IS the surface concentration ---
    surf_only = valid[~valid["covers_migrant"]]

    # --- Tows reaching migrant layer: extract migrant concentration ---
    # biomass_dry × D = C_surface × L_s + C_migrant × (D - L_s)
    # We estimate C_surface from surface-only tows (median per month×dn),
    # then solve for C_migrant per tow.
    deep = valid[valid["covers_migrant"]].copy()

    # Compute monthly median C_surface from surface-only tows
    surf_stats = (
        surf_only.groupby(["month", "day_night"])["biomass_dry"]
        .median()
        .rename("C_surface_ref")
    )

    deep = deep.join(surf_stats, on=["month", "day_night"])

    # Where we have a surface reference, solve for C_migrant
    h_s = deep["layer_depth_surface"]
    h_m = deep["tow_depth_max"] - deep["layer_depth_surface"]
    deep["C_migrant_est"] = np.where(
        h_m > 0,
        (deep["biomass_dry"] * deep["tow_depth_max"] - deep["C_surface_ref"] * h_s) / h_m,
        np.nan,
    )

    # --- Compute global medians per day_night ---
    conc = {}
    for dn in ["day", "night"]:
        c_surf = surf_only.loc[surf_only["day_night"] == dn, "biomass_dry"].median()
        c_migrant = deep.loc[deep["day_night"] == dn, "C_migrant_est"].median()
        n_surf = (surf_only["day_night"] == dn).sum()
        n_deep = (deep["day_night"] == dn).sum()
        conc[dn] = {
            "C_surface": c_surf, "C_migrant": c_migrant,
            "n_surf": n_surf, "n_deep": n_deep,
        }

    G0 = conc["day"]["C_surface"]
    G1_from_surface = conc["night"]["C_surface"] - conc["day"]["C_surface"]
    G1_from_migrant = conc["day"]["C_migrant"]

    # --- Seasonal (monthly) breakdown ---
    monthly_surf = (
        surf_only.groupby(["month", "day_night"])["biomass_dry"]
        .median()
        .unstack(fill_value=np.nan)
    )
    monthly_migrant = (
        deep.groupby(["month", "day_night"])["C_migrant_est"]
        .median()
        .unstack(fill_value=np.nan)
    )

    # ---- Plot ----
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    months = np.arange(1, 13)
    month_labels = ["J", "F", "M", "A", "M", "J", "J", "A", "S", "O", "N", "D"]

    # (0,0) Bar chart: global G0, G1 estimates with two independent G1 paths
    ax = axes[0, 0]
    bars_x = np.arange(3)
    bars_vals = [G0, G1_from_surface, G1_from_migrant]
    bars_labels = ["G0\n(C_surf day)", "G1\n(C_surf night\n- C_surf day)", "G1 check\n(C_mig day)"]
    bars_colors = ["#22C55E", "#8B5CF6", "#8B5CF6"]
    bars_hatches = ["", "", "//"]

    for i, (v, c, h) in enumerate(zip(bars_vals, bars_colors, bars_hatches)):
        ax.bar(i, v, color=c, alpha=0.7, hatch=h, edgecolor="black", linewidth=0.5)
        ax.text(i, v + 0.2, f"{v:.2f}", ha="center", fontsize=10, fontweight="bold")

    ax.set_xticks(bars_x)
    ax.set_xticklabels(bars_labels, fontsize=9)
    ax.set_ylabel("Concentration (mg/m³)")
    ax.set_title("Functional group estimates (median)")
    ax.grid(True, alpha=0.2, axis="y")

    # (0,1) Schematic: day vs night layer occupancy
    ax = axes[0, 1]
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 300)
    ax.invert_yaxis()

    # Day side (left)
    ax.fill_between([0.5, 4.5], 0, 127, color="#22C55E", alpha=0.3)
    ax.text(2.5, 60, f"G0\n{G0:.1f}", ha="center", va="center", fontsize=12, fontweight="bold", color="#22C55E")
    ax.fill_between([0.5, 4.5], 127, 250, color="#8B5CF6", alpha=0.3)
    ax.text(2.5, 185, f"G1\n{G1_from_migrant:.1f}", ha="center", va="center", fontsize=12, fontweight="bold", color="#8B5CF6")
    ax.text(2.5, 290, "DAY", ha="center", fontsize=11, fontweight="bold", color="#F59E0B")

    # Night side (right)
    ax.fill_between([5.5, 9.5], 0, 127, color="#22C55E", alpha=0.3)
    ax.fill_between([5.5, 9.5], 0, 127, color="#8B5CF6", alpha=0.15)
    ax.text(7.5, 60, f"G0+G1\n{conc['night']['C_surface']:.1f}", ha="center", va="center", fontsize=12, fontweight="bold", color="#166534")
    ax.fill_between([5.5, 9.5], 127, 250, color="gray", alpha=0.1)
    ax.text(7.5, 185, "~empty", ha="center", va="center", fontsize=11, color="gray")
    ax.text(7.5, 290, "NIGHT", ha="center", fontsize=11, fontweight="bold", color="#3B82F6")

    # Layer boundaries
    ax.axhline(127, color="black", lw=1.5, ls="-")
    ax.text(5, 122, "layer surface (~127m)", ha="center", va="bottom", fontsize=8)
    ax.axhline(0, color="black", lw=0.5)

    # Arrows showing DVM
    ax.annotate("", xy=(6.5, 50), xytext=(4.5, 185),
                arrowprops=dict(arrowstyle="->", color="#8B5CF6", lw=2))
    ax.text(5.2, 110, "DVM", fontsize=9, color="#8B5CF6", fontweight="bold", rotation=60)

    ax.set_ylabel("Depth (m)")
    ax.set_xticks([])
    ax.set_title("DVM schematic (mg/m³ per layer)")

    # (1,0) Monthly G0 and G1 seasonal cycle
    ax = axes[1, 0]

    # G0 = surface day median per month
    g0_monthly = monthly_surf["day"].reindex(months) if "day" in monthly_surf.columns else pd.Series(dtype=float)
    # G1 from surface = night - day
    g1_surf_monthly = (monthly_surf.get("night", pd.Series(dtype=float)).reindex(months)
                       - monthly_surf.get("day", pd.Series(dtype=float)).reindex(months))
    # G1 from migrant = migrant day
    g1_mig_monthly = monthly_migrant["day"].reindex(months) if "day" in monthly_migrant.columns else pd.Series(dtype=float)

    ax.plot(months, g0_monthly.values, "o-", color="#22C55E", label="G0 (C_surf day)", markersize=5)
    ax.plot(months, g1_surf_monthly.values, "s-", color="#8B5CF6", label="G1 (C_surf night - day)", markersize=5)
    ax.plot(months, g1_mig_monthly.values, "^--", color="#8B5CF6", alpha=0.5, label="G1 check (C_mig day)", markersize=5)

    ax.set_xticks(months)
    ax.set_xticklabels(month_labels)
    ax.set_ylabel("Concentration (mg/m³)")
    ax.set_title("Seasonal cycle of G0 and G1")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.2)

    # (1,1) Scatter: G1 from surface vs G1 from migrant (consistency)
    ax = axes[1, 1]
    # Per-month consistency
    g1_s = g1_surf_monthly.values
    g1_m = g1_mig_monthly.values
    mask = np.isfinite(g1_s) & np.isfinite(g1_m)
    ax.scatter(g1_s[mask], g1_m[mask], c=[f"C{m}" for m in months[mask]],
               s=80, zorder=5, edgecolors="black", linewidth=0.5)
    for m_idx in np.where(mask)[0]:
        ax.annotate(month_labels[m_idx], (g1_s[m_idx], g1_m[m_idx]),
                    textcoords="offset points", xytext=(5, 5), fontsize=8)

    lims = [0, max(np.nanmax(g1_s), np.nanmax(g1_m)) * 1.2]
    ax.plot(lims, lims, "k--", lw=0.8, alpha=0.5, label="1:1 line")
    ax.set_xlabel("G1 from surface (night - day) (mg/m³)")
    ax.set_ylabel("G1 from migrant layer (day) (mg/m³)")
    ax.set_title("G1 consistency check (monthly)")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.2)
    ax.set_aspect("equal", adjustable="datalim")

    fig.suptitle("HOT — Functional group decomposition (G0 resident / G1 migrant)",
                 fontweight="bold", y=1.01)
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "diag_group_decomposition.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    # Print summary
    print("  4. diag_group_decomposition.png")
    print()
    print("     Global estimates (median):")
    print(f"     G0 (resident)  = {G0:.2f} mg/m³  (C_surface day, n={conc['day']['n_surf']})")
    print(f"     G1 (migrant)   = {G1_from_surface:.2f} mg/m³  (C_surface night - day)")
    print(f"     G1 check       = {G1_from_migrant:.2f} mg/m³  (C_migrant day, n={conc['day']['n_deep']})")
    print(f"     C_surface night = {conc['night']['C_surface']:.2f} mg/m³  (G0 + G1)")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("HOT Observation Diagnostics")
    print("=" * 60)
    print()

    df = load()
    print(f"Loaded {len(df)} tows ({df['zeu'].notna().sum()} with pelagic depths)")
    print()

    fig_tow_vs_layers(df)
    fig_day_night_by_coverage(df)
    fig_climatology(df)
    fig_group_decomposition(df)

    print()
    print("Done.")


if __name__ == "__main__":
    main()
