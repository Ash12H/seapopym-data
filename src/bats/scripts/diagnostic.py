"""
BATS Observation Diagnostic Script
Produces diagnostic figures for the BATS zooplankton Parquet release.

1. Tow depth vs pelagic layer depths
2. Day/night biomass boxplot
3. Monthly climatology (mean ± std)
3b. Sampling density heatmap
4. DVM summary (bar chart + schematic)

Observation operator (for model loss):
  - Day   →  observe G0         (residents in surface)
  - Night →  observe G0 + G1    (residents + migrants in surface)
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
FIGURES_DIR = PROJECT_ROOT / "src" / "bats" / "reports" / "figures"
PARQUET = PROJECT_ROOT / "src" / "bats" / "release" / "bats_zooplankton_obs.parquet"

STATION = "BATS"


def load():
    df = pd.read_parquet(PARQUET)
    df["time"] = pd.to_datetime(df["time"])
    df["month"] = df["time"].dt.month
    df["year"] = df["time"].dt.year
    return df


def fig_tow_vs_layers(df: pd.DataFrame):
    valid = df.dropna(subset=["zeu"]).sort_values("time")

    fig, ax = plt.subplots(figsize=(14, 5))

    colors = {"day": "#F59E0B", "night": "#3B82F6"}
    for dn in ["day", "night"]:
        sub = valid[valid["day_night"] == dn]
        ax.scatter(sub["time"], sub["tow_depth_max"],
                   c=colors[dn], s=8, alpha=0.5, label=f"tow ({dn})", zorder=3)

    ax.plot(valid["time"], valid["layer_depth_surface"], "k-", lw=1.2, label="layer surface (1.5×Zeu)")
    ax.plot(valid["time"], valid["layer_depth_migrant"], "k--", lw=0.8, alpha=0.5, label="layer migrant (4.5×Zeu)")

    ax.fill_between(valid["time"], 0, valid["layer_depth_surface"], alpha=0.08, color="green", label="surface layer")
    ax.fill_between(valid["time"], valid["layer_depth_surface"], valid["layer_depth_migrant"],
                    alpha=0.05, color="blue", label="migrant layer")

    ax.invert_yaxis()
    ax.set_ylabel("Depth (m)")
    ax.set_xlabel("Date")
    ax.set_title(f"{STATION} — Tow depth vs pelagic layer boundaries", fontweight="bold")
    ax.legend(loc="lower right", fontsize=8, ncol=3)
    ax.grid(True, alpha=0.2)

    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "diag_tow_vs_layers.png", dpi=150)
    plt.close(fig)
    print("  1. diag_tow_vs_layers.png")


def fig_day_night_boxplot(df: pd.DataFrame):
    data_day = df.loc[df["day_night"] == "day", "biomass_dry"]
    data_night = df.loc[df["day_night"] == "night", "biomass_dry"]

    fig, ax = plt.subplots(figsize=(7, 5))

    bp = ax.boxplot(
        [data_day.dropna(), data_night.dropna()],
        tick_labels=["day (→ G0)", "night (→ G0+G1)"],
        patch_artist=True, widths=0.5, showfliers=True,
        flierprops=dict(marker=".", markersize=3, alpha=0.3),
    )
    bp["boxes"][0].set_facecolor("#F59E0B")
    bp["boxes"][0].set_alpha(0.6)
    bp["boxes"][1].set_facecolor("#3B82F6")
    bp["boxes"][1].set_alpha(0.6)

    med_day, med_night = data_day.median(), data_night.median()
    ratio = med_night / med_day if med_day > 0 else float("nan")

    ax.set_title(
        f"day: n={len(data_day)}, median={med_day:.2f}  |  "
        f"night: n={len(data_night)}, median={med_night:.2f}  |  "
        f"ratio N/D={ratio:.2f}",
        fontsize=9,
    )
    ax.set_ylabel("Biomass dry (mg/m³)")
    ax.grid(True, alpha=0.2, axis="y")

    fig.suptitle(f"{STATION} — Day vs night biomass", fontweight="bold", y=1.02)
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "diag_day_night.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("  2. diag_day_night.png")


def fig_climatology(df: pd.DataFrame):
    months = np.arange(1, 13)
    month_labels = ["J", "F", "M", "A", "M", "J", "J", "A", "S", "O", "N", "D"]

    fig, ax = plt.subplots(figsize=(12, 5))

    for dn, color, offset, label in [
        ("day", "#F59E0B", -0.15, "day → G0"),
        ("night", "#3B82F6", 0.15, "night → G0+G1"),
    ]:
        sub = df[df["day_night"] == dn]
        grouped = sub.groupby("month")["biomass_dry"]
        means = grouped.mean()
        stds = grouped.std()

        x = months + offset
        m = means.reindex(months).values
        s = stds.reindex(months).values

        ax.errorbar(x, m, yerr=s, fmt="o-", color=color, capsize=3, capthick=1,
                    markersize=5, label=f"{label} (mean ± std)", alpha=0.8)
        ax.fill_between(x, m - s, m + s, color=color, alpha=0.1)

    ax.set_xticks(months)
    ax.set_xticklabels(month_labels)
    ax.set_xlabel("Month")
    ax.set_ylabel("Biomass dry (mg/m³)")
    ax.set_title(f"{STATION} — Monthly climatology", fontweight="bold")
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.2)

    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "diag_climatology.png", dpi=150)
    plt.close(fig)
    print("  3. diag_climatology.png")


def fig_sampling_density(df: pd.DataFrame):
    months = np.arange(1, 13)
    month_labels = ["J", "F", "M", "A", "M", "J", "J", "A", "S", "O", "N", "D"]

    pivot = df.groupby(["year", "month"]).size().unstack(fill_value=0)
    for m in range(1, 13):
        if m not in pivot.columns:
            pivot[m] = 0
    pivot = pivot[sorted(pivot.columns)]

    fig, ax = plt.subplots(figsize=(12, 5))
    im = ax.pcolormesh(
        pivot.columns - 0.5, pivot.index - 0.5, pivot.values,
        cmap="YlOrBr", vmin=0,
    )
    ax.set_xlabel("Month")
    ax.set_ylabel("Year")
    ax.set_xticks(months)
    ax.set_xticklabels(month_labels)
    ax.set_title(f"{STATION} — Sampling density (tows per month)", fontweight="bold")
    fig.colorbar(im, ax=ax, label="# tows", shrink=0.8)

    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "diag_sampling_density.png", dpi=150)
    plt.close(fig)
    print("  3b. diag_sampling_density.png")


def fig_dvm_summary(df: pd.DataFrame):
    med_day = df.loc[df["day_night"] == "day", "biomass_dry"].median()
    med_night = df.loc[df["day_night"] == "night", "biomass_dry"].median()
    n_day = (df["day_night"] == "day").sum()
    n_night = (df["day_night"] == "night").sum()

    median_lds = df.dropna(subset=["zeu"])["layer_depth_surface"].median()

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    # Bar chart
    ax = axes[0]
    ax.bar([0, 1], [med_day, med_night],
           color=["#F59E0B", "#3B82F6"], alpha=0.7,
           edgecolor="black", linewidth=0.5)
    ax.text(0, med_day + 0.1, f"{med_day:.2f}", ha="center", fontsize=11, fontweight="bold")
    ax.text(1, med_night + 0.1, f"{med_night:.2f}", ha="center", fontsize=11, fontweight="bold")
    ax.set_xticks([0, 1])
    ax.set_xticklabels([f"Day → G0\n(n={n_day})", f"Night → G0+G1\n(n={n_night})"], fontsize=10)
    ax.set_ylabel("Biomass dry (mg/m³)")
    ax.set_title("Median biomass by observation type")
    ax.grid(True, alpha=0.2, axis="y")

    # DVM schematic
    ax = axes[1]
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 300)
    ax.invert_yaxis()

    ax.fill_between([0.5, 4.5], 0, median_lds, color="#22C55E", alpha=0.3)
    ax.text(2.5, median_lds * 0.45, f"G0\n{med_day:.1f}",
            ha="center", va="center", fontsize=12, fontweight="bold", color="#22C55E")
    ax.fill_between([0.5, 4.5], median_lds, 250, color="#8B5CF6", alpha=0.3)
    ax.text(2.5, median_lds + (250 - median_lds) * 0.45, "G1",
            ha="center", va="center", fontsize=12, fontweight="bold", color="#8B5CF6")
    ax.text(2.5, 290, "DAY", ha="center", fontsize=11, fontweight="bold", color="#F59E0B")

    ax.fill_between([5.5, 9.5], 0, median_lds, color="#22C55E", alpha=0.3)
    ax.fill_between([5.5, 9.5], 0, median_lds, color="#8B5CF6", alpha=0.15)
    ax.text(7.5, median_lds * 0.45, f"G0+G1\n{med_night:.1f}",
            ha="center", va="center", fontsize=12, fontweight="bold", color="#166534")
    ax.fill_between([5.5, 9.5], median_lds, 250, color="gray", alpha=0.1)
    ax.text(7.5, median_lds + (250 - median_lds) * 0.45, "~empty",
            ha="center", va="center", fontsize=11, color="gray")
    ax.text(7.5, 290, "NIGHT", ha="center", fontsize=11, fontweight="bold", color="#3B82F6")

    ax.axhline(median_lds, color="black", lw=1.5, ls="-")
    ax.text(5, median_lds - 5, f"layer surface (~{median_lds:.0f}m)",
            ha="center", va="bottom", fontsize=8)
    ax.axhline(0, color="black", lw=0.5)

    ax.annotate("", xy=(6.5, median_lds * 0.35),
                xytext=(4.5, median_lds + (250 - median_lds) * 0.45),
                arrowprops=dict(arrowstyle="->", color="#8B5CF6", lw=2))
    ax.text(5.2, median_lds * 0.85, "DVM", fontsize=9,
            color="#8B5CF6", fontweight="bold", rotation=60)

    ax.set_ylabel("Depth (m)")
    ax.set_xticks([])
    ax.set_title("DVM schematic")

    fig.suptitle(f"{STATION} — DVM summary", fontweight="bold", y=1.02)
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "diag_dvm_summary.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    print("  4. diag_dvm_summary.png")
    print()
    print(f"     Day  → G0     : {n_day} tows, median={med_day:.2f} mg/m³")
    print(f"     Night→ G0+G1  : {n_night} tows, median={med_night:.2f} mg/m³")
    print(f"     Ratio N/D     : {med_night/med_day:.2f}")


def main():
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print(f"{STATION} Observation Diagnostics")
    print("=" * 60)
    print()

    df = load()
    n_day = (df["day_night"] == "day").sum()
    n_night = (df["day_night"] == "night").sum()
    print(f"Loaded {len(df)} tows ({n_day} day, {n_night} night)")
    print()

    fig_tow_vs_layers(df)
    fig_day_night_boxplot(df)
    fig_climatology(df)
    fig_sampling_density(df)
    fig_dvm_summary(df)

    print()
    print("Done.")


if __name__ == "__main__":
    main()
