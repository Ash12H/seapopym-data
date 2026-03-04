"""Plot functions for zooplankton biomass analysis.

Each function generates a single PNG figure.
Conventions: dpi=150, bbox_inches="tight", sns whitegrid theme, plt.close() after save.
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

sns.set_theme(style="whitegrid")


def _savefig(fig: plt.Figure, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved {path}")


def plot_outlier_timeseries(
    df: pd.DataFrame, outlier_mask: pd.Series, label: str, output_path: Path
) -> None:
    """Time series with outliers highlighted in red."""
    fig, ax = plt.subplots(figsize=(12, 5))

    normal = df[~outlier_mask]
    outliers = df[outlier_mask]

    ax.scatter(normal["time"], normal["biomass"], s=12, alpha=0.5, label="Normal", color="steelblue")
    ax.scatter(outliers["time"], outliers["biomass"], s=25, alpha=0.8, label=f"Outliers (n={len(outliers)})", color="red", zorder=5)

    ax.set_title(f"{label} — Biomass time series with IQR outliers")
    ax.set_xlabel("Time")
    ax.set_ylabel("Biomass dry (mg/m³)")
    ax.legend()
    _savefig(fig, output_path)


def plot_temporal_heatmap(
    matrix: pd.DataFrame, label: str, output_path: Path
) -> None:
    """Heatmap of observation count per year x month."""
    fig, ax = plt.subplots(figsize=(10, max(6, len(matrix) * 0.3)))

    month_labels = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    sns.heatmap(
        matrix,
        annot=True,
        fmt="d",
        cmap="YlOrRd",
        xticklabels=month_labels,
        ax=ax,
        cbar_kws={"label": "Observation count"},
    )
    ax.set_title(f"{label} — Temporal coverage (year × month)")
    ax.set_ylabel("Year")
    ax.set_xlabel("Month")
    _savefig(fig, output_path)


def plot_day_night_comparison(
    df: pd.DataFrame, label: str, output_path: Path
) -> None:
    """Violin/box plots comparing day vs night biomass."""
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    # Violin plot
    sns.violinplot(data=df, x="day_night", y="biomass", hue="day_night", ax=axes[0], inner="box",
                   palette={"day": "#f0c040", "night": "#3060a0"}, order=["day", "night"], legend=False)
    axes[0].set_title(f"{label} — Day vs Night (violin)")
    axes[0].set_xlabel("")
    axes[0].set_ylabel("Biomass dry (mg/m³)")

    # Box plot
    sns.boxplot(data=df, x="day_night", y="biomass", hue="day_night", ax=axes[1],
                palette={"day": "#f0c040", "night": "#3060a0"}, order=["day", "night"], legend=False)
    axes[1].set_title(f"{label} — Day vs Night (box)")
    axes[1].set_xlabel("")
    axes[1].set_ylabel("Biomass dry (mg/m³)")

    fig.tight_layout()
    _savefig(fig, output_path)


def plot_depth_category_comparison(
    df: pd.DataFrame, label: str, output_path: Path
) -> None:
    """Violin/box plots comparing depth categories."""
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    order = ["epipelagic_only", "epipelagic_mesopelagic"]
    palette = {"epipelagic_only": "#66b3ff", "epipelagic_mesopelagic": "#ff6666"}
    short_labels = {"epipelagic_only": "Epi only", "epipelagic_mesopelagic": "Epi+Meso"}

    plot_df = df.copy()
    plot_df["depth_label"] = plot_df["depth_category"].map(short_labels)
    label_order = [short_labels[o] for o in order]
    label_palette = {short_labels[k]: v for k, v in palette.items()}

    sns.violinplot(data=plot_df, x="depth_label", y="biomass", hue="depth_label", ax=axes[0], inner="box",
                   palette=label_palette, order=label_order, legend=False)
    axes[0].set_title(f"{label} — Depth categories (violin)")
    axes[0].set_xlabel("")
    axes[0].set_ylabel("Biomass dry (mg/m³)")

    sns.boxplot(data=plot_df, x="depth_label", y="biomass", hue="depth_label", ax=axes[1],
                palette=label_palette, order=label_order, legend=False)
    axes[1].set_title(f"{label} — Depth categories (box)")
    axes[1].set_xlabel("")
    axes[1].set_ylabel("Biomass dry (mg/m³)")

    fig.tight_layout()
    _savefig(fig, output_path)


def plot_seasonal_climatology(
    climatology: pd.DataFrame, label: str, output_path: Path
) -> None:
    """Monthly climatology with median line and IQR shading."""
    fig, ax = plt.subplots(figsize=(10, 5))

    months = climatology.index.values
    month_labels = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    ax.plot(months, climatology["median"], "o-", color="steelblue", linewidth=2, label="Median")
    ax.fill_between(
        months,
        climatology["q25"],
        climatology["q75"],
        alpha=0.3,
        color="steelblue",
        label="IQR (Q25–Q75)",
    )

    ax.set_xticks(range(1, 13))
    ax.set_xticklabels(month_labels)
    ax.set_title(f"{label} — Seasonal climatology")
    ax.set_xlabel("Month")
    ax.set_ylabel("Biomass dry (mg/m³)")
    ax.legend()
    _savefig(fig, output_path)


def plot_anomalies(
    df: pd.DataFrame, label: str, output_path: Path
) -> None:
    """Bar chart of biomass anomalies (positive=blue, negative=red)."""
    df = df.dropna(subset=["anomaly"]).sort_values("time")

    fig, ax = plt.subplots(figsize=(12, 5))

    colors = ["steelblue" if a >= 0 else "indianred" for a in df["anomaly"]]
    ax.bar(df["time"], df["anomaly"], color=colors, width=20, alpha=0.7)

    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_title(f"{label} — Biomass anomalies (obs − monthly climatology)")
    ax.set_xlabel("Time")
    ax.set_ylabel("Anomaly (mg/m³)")
    _savefig(fig, output_path)


def plot_trend(
    annual_medians: pd.Series, slope: float, intercept: float,
    tau: float, p_value: float, label: str, output_path: Path
) -> None:
    """Annual median time series with Theil-Sen trend line."""
    fig, ax = plt.subplots(figsize=(10, 5))

    years = annual_medians.index.values
    values = annual_medians.values

    ax.scatter(years, values, s=40, color="steelblue", zorder=5, label="Annual median")

    # Trend line
    x_fit = np.array([years.min(), years.max()])
    y_fit = slope * x_fit + intercept
    sig_label = f"p={p_value:.4f}" if p_value >= 0.0001 else f"p<0.0001"
    ax.plot(x_fit, y_fit, "--", color="indianred", linewidth=2,
            label=f"Theil-Sen: {slope:+.4f} mg/m³/yr (τ={tau:.3f}, {sig_label})")

    ax.set_title(f"{label} — Long-term trend (annual medians)")
    ax.set_xlabel("Year")
    ax.set_ylabel("Biomass dry (mg/m³)")
    ax.legend(fontsize=9)
    _savefig(fig, output_path)
