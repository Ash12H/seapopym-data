import sys
from pathlib import Path
import pandas as pd
from datetime import datetime

# Add src to python path to allow importing core
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.append(str(PROJECT_ROOT / "src"))

from core.io import DataLoader, DataWriter
from core.plotting import Plotter


def main():
    # Paths
    STATION_DIR = PROJECT_ROOT / "src" / "hot"
    RAW_DIR = STATION_DIR / "data" / "raw"
    RELEASE_DIR = STATION_DIR / "release"
    REPORTS_DIR = STATION_DIR / "reports"
    FIGURES_DIR = REPORTS_DIR / "figures"

    # Files
    INPUT_FILE = RAW_DIR / "hot_zooplankton.csv"
    OUTPUT_NC = RELEASE_DIR / "hot_zooplankton_obs.nc"
    REPORT_FILE = REPORTS_DIR / "report.md"

    print("Processing HOT station...")
    print(f"Input: {INPUT_FILE}")

    if not INPUT_FILE.exists():
        print(f"Error: Input file {INPUT_FILE} not found.")
        return

    # 1. Load Data
    df = DataLoader.load_csv(INPUT_FILE)

    # 2. Process
    print("Cleaning data...")
    if "time" in df.columns:
        df["time"] = pd.to_datetime(df["time"]).dt.tz_localize(None)

    # Clean object columns
    for col in df.select_dtypes(include=["object", "category"]).columns:
        df[col] = df[col].astype(str)

    # 3. Generate Figures
    print("Generating figures...")
    Plotter.plot_missing_values(df, FIGURES_DIR / "missing_values.png")

    val_col = None
    possible_cols = ["biomass", "wet_weight", "dry_weight", "zooplankton_biomass"]
    for c in possible_cols:
        if c in df.columns:
            val_col = c
            break

    if val_col and "time" in df.columns:
        Plotter.plot_time_series(
            df,
            "time",
            val_col,
            f"HOT Zooplankton {val_col}",
            FIGURES_DIR / f"time_series_{val_col}.png",
        )

    if "lat" in df.columns and "lon" in df.columns:
        Plotter.plot_scatter_map(df, "lat", "lon", FIGURES_DIR / "map.png")

    # 4. Export to NetCDF
    print("Exporting to NetCDF...")
    ds = df.to_xarray()
    ds.attrs["history"] = f"Created on {datetime.now()} using seapopym-data pipeline."
    ds.attrs["source"] = "HOT Zooplankton Data"

    DataWriter.save_nc(ds, OUTPUT_NC)

    # 5. Generate Report
    print("Generating report...")
    with open(REPORT_FILE, "w") as f:
        f.write("# HOT Station Report\n\n")
        f.write(f"**Date**: {datetime.now()}\n")
        f.write(f"**Input**: `{INPUT_FILE.name}`\n")
        f.write(f"**Output**: `{OUTPUT_NC.name}`\n\n")

        f.write("## 1. Data Quality\n")
        f.write("![Missing Values](figures/missing_values.png)\n\n")

        f.write("## 2. Geography\n")
        if (FIGURES_DIR / "map.png").exists():
            f.write("![Map](figures/map.png)\n\n")
        else:
            f.write("*No geographic data found.*\n\n")

        if val_col:
            f.write("## 3. Time Series\n")
            f.write(f"![Time Series](figures/time_series_{val_col}.png)\n\n")

    print("Done.")


if __name__ == "__main__":
    main()
