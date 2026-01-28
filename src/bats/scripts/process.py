import sys
from pathlib import Path
import pandas as pd
from datetime import datetime

# Add src to python path to allow importing core
# Assuming script is run from project root or src/bats/scripts
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.append(str(PROJECT_ROOT / "src"))

from core.io import DataLoader, DataWriter
from core.plotting import Plotter


def main():
    # Paths
    STATION_DIR = PROJECT_ROOT / "src" / "bats"
    RAW_DIR = STATION_DIR / "data" / "raw"
    RELEASE_DIR = STATION_DIR / "release"
    REPORTS_DIR = STATION_DIR / "reports"
    FIGURES_DIR = REPORTS_DIR / "figures"

    # Files
    INPUT_FILE = RAW_DIR / "bats_zooplankton.csv"
    OUTPUT_NC = RELEASE_DIR / "bats_zooplankton_obs.nc"
    REPORT_FILE = REPORTS_DIR / "report.md"

    print("Processing BATS station...")
    print(f"Input: {INPUT_FILE}")

    # 1. Load Data
    df = DataLoader.load_csv(
        INPUT_FILE, index_col=0
    )  # raw_data = pd.read_csv("...", index_col=0)

    # 2. Process
    print("Cleaning data...")
    # Logic extracted from notebook
    if "time" in df.columns:
        df["time"] = pd.to_datetime(df["time"])

    # Drop unused columns (as per notebook)
    cols_to_drop = ["Cruise_ID", "time_out", "duration_minutes", "UNOLS"]
    df = df.drop(columns=[c for c in cols_to_drop if c in df.columns], errors="ignore")

    # Convert units if necessary (example)
    # df = UnitManager.convert_column(df, "biomass", "mg/m^3", "g/m^3")

    # 3. Generate Figures
    print("Generating figures...")
    Plotter.plot_missing_values(df, FIGURES_DIR / "missing_values.png")

    if "time" in df.columns and "wet_weight" in df.columns:
        Plotter.plot_time_series(
            df,
            "time",
            "wet_weight",
            "BATS Zooplankton Wet Weight",
            FIGURES_DIR / "time_series_wet_weight.png",
            ylabel="mg/m3",
        )

    if "lat" in df.columns and "lon" in df.columns:
        Plotter.plot_scatter_map(df, "lat", "lon", FIGURES_DIR / "map.png")

    # 4. Export to NetCDF
    print("Exporting to NetCDF...")
    ds = df.to_xarray()
    ds.attrs["history"] = f"Created on {datetime.now()} using seapopym-data pipeline."
    ds.attrs["source"] = "BATS Zooplankton Data"

    DataWriter.save_nc(ds, OUTPUT_NC)

    # 5. Generate Report
    print("Generating report...")
    with open(REPORT_FILE, "w") as f:
        f.write("# BATS Station Report\n\n")
        f.write(f"**Date**: {datetime.now()}\n")
        f.write(f"**Input**: `{INPUT_FILE.name}`\n")
        f.write(f"**Output**: `{OUTPUT_NC.name}`\n\n")

        f.write("## 1. Data Quality\n")
        f.write("![Missing Values](figures/missing_values.png)\n\n")

        f.write("## 2. Geography\n")
        f.write("![Map](figures/map.png)\n\n")

        f.write("## 3. Time Series\n")
        f.write("![Time Series](figures/time_series_wet_weight.png)\n\n")

    print("Done.")


if __name__ == "__main__":
    main()
