import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
from pathlib import Path
from typing import Optional

# Basic setup for publication-quality figures
sns.set_theme(style="whitegrid")
plt.rcParams["figure.figsize"] = [10, 6]
plt.rcParams["figure.dpi"] = 150


class Plotter:
    """Standardized plotter for Seapopym data reports."""

    @staticmethod
    def save_figure(fig: plt.Figure, path: Path) -> None:
        """Save a figure to a path with standard settings."""
        path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(path, bbox_inches="tight")
        plt.close(fig)
        print(f"Saved figure to {path}")

    @staticmethod
    def plot_time_series(
        data: pd.DataFrame,
        x_col: str,
        y_col: str,
        title: str,
        output_path: Path,
        ylabel: Optional[str] = None,
    ) -> None:
        """Plot a standard time series."""
        fig, ax = plt.subplots()
        sns.lineplot(data=data, x=x_col, y=y_col, ax=ax, markers=True)
        ax.set_title(title)
        if ylabel:
            ax.set_ylabel(ylabel)
        Plotter.save_figure(fig, output_path)

    @staticmethod
    def plot_missing_values(data: pd.DataFrame, output_path: Path) -> None:
        """Plot a bar chart of missing values per column."""
        missing = data.isnull().sum()
        missing = missing[missing > 0].sort_values(ascending=False)

        if missing.empty:
            print("No missing values to plot.")
            return

        fig, ax = plt.subplots()
        sns.barplot(
            x=missing.index, y=missing.values, ax=ax, hue=missing.index, legend=False
        )
        ax.set_title("Missing Values Count")
        ax.set_xticklabels(ax.get_xticklabels(), rotation=45, ha="right")
        ax.set_ylabel("Count")
        Plotter.save_figure(fig, output_path)

    @staticmethod
    def plot_scatter_map(
        data: pd.DataFrame,
        lat_col: str,
        lon_col: str,
        output_path: Path,
        hue: Optional[str] = None,
    ) -> None:
        """Plot a simple scatter map (lat vs lon)."""
        fig, ax = plt.subplots()
        sns.scatterplot(data=data, x=lon_col, y=lat_col, hue=hue, ax=ax, alpha=0.6)
        ax.set_title("Station Locations")
        ax.set_xlabel("Longitude")
        ax.set_ylabel("Latitude")
        ax.axis("equal")  # Approximate simplified aspect ratio
        Plotter.save_figure(fig, output_path)
