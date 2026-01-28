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

    if not INPUT_FILE.exists():
        print(f"Error: Input file {INPUT_FILE} not found.")
        return

    # 1. Load Data
    # Note: 'time' is just date. 'time_in' is HHMM.
    df = DataLoader.load_csv(INPUT_FILE)

    # 2. Process
    print("Cleaning data...")

    # Clean string columns
    for col in df.select_dtypes(include=["object", "category"]).columns:
        df[col] = df[col].astype(str)

    # Convert lat/lon to float
    if "lat" in df.columns:
        df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
    if "lon" in df.columns:
        df["lon"] = pd.to_numeric(df["lon"], errors="coerce")

    # Aggregate by Tow
    # Fractions (200, 500, 1000, 2000, 5000 um) -> Sum weights
    # Grouping keys: Tow identifiers
    group_cols = [
        "Cruise_ID",
        "time",  # Date
        "time_in",  # Start Time HHMM
        "time_out",
        "lat",
        "lon",
        "depth",
        "volume_water",
        "duration_minutes",
    ]
    # Ensure all group_cols are present
    group_cols = [c for c in group_cols if c in df.columns]

    sum_cols = ["wet_weight", "dry_weight"]
    sum_cols = [c for c in sum_cols if c in df.columns]

    print(f"Aggregating {len(df)} rows by tow...")
    df_agg = df.groupby(group_cols, as_index=False)[sum_cols].sum()
    print(f"Result: {len(df_agg)} tows.")

    df = df_agg

    # Calculate Concentration (mg/m3)
    # wet_weight (mg) / volume_water (m3)
    if "wet_weight" in df.columns and "volume_water" in df.columns:
        df["biomass"] = df["wet_weight"] / df["volume_water"]
        print("Calculated biomass (mg/m3) from wet_weight / volume_water")

    if "dry_weight" in df.columns and "volume_water" in df.columns:
        df["biomass_dry"] = df["dry_weight"] / df["volume_water"]
        print("Calculated biomass_dry (mg/m3) from dry_weight / volume_water")

    # Construct Datetime
    # time column is 'YYYY-MM-DDTHH:MM:SS' (usually 00:00:00)
    # time_in is 'HHMM' (int or str)

    def parse_datetime(row):
        try:
            date_str = str(row["time"]).split("T")[0]  # Get YYYY-MM-DD
            time_in = str(row["time_in"]).strip()

            # Pad with zeros if needed (e.g. 930 -> 0930)
            if time_in == "nan" or time_in == "":
                return pd.to_datetime(date_str)

            time_in = time_in.split(".")[0]  # remove float decimal if present
            time_in = time_in.zfill(4)

            if len(time_in) != 4:
                return pd.to_datetime(date_str)

            hh = time_in[:2]
            mm = time_in[2:]

            # Handle 2400? -> 0000 next day (logic can be complex, assume simplistic 24->00)
            if hh == "24":
                hh = "00"

            full_str = f"{date_str} {hh}:{mm}:00"
            return pd.to_datetime(full_str)
        except Exception:
            return pd.to_datetime(row["time"])

    df["datetime"] = df.apply(parse_datetime, axis=1)
    df["time"] = df["datetime"]  # Replace Time
    df = df.drop(columns=["datetime"])

    # Sort by time
    df = df.sort_values("time")

    # 3. Generate Figures
    print("Generating figures...")
    Plotter.plot_missing_values(df, FIGURES_DIR / "missing_values.png")

    val_col = "biomass" if "biomass" in df.columns else None

    if val_col:
        Plotter.plot_time_series(
            df,
            "time",
            val_col,
            "BATS Zooplankton Biomass",
            FIGURES_DIR / f"time_series_{val_col}.png",
            ylabel="mg/m3",
        )

    if "lat" in df.columns and "lon" in df.columns:
        Plotter.plot_scatter_map(df, "lat", "lon", FIGURES_DIR / "map.png")

    # 4. Export to NetCDF
    print("Exporting to NetCDF...")
    ds = df.to_xarray()
    ds.attrs["history"] = f"Created on {datetime.now()} using seapopym-data pipeline."
    ds.attrs["source"] = "BATS Zooplankton Data"

    if "biomass" in ds:
        ds["biomass"].attrs["units"] = "mg/m^3"
        ds["biomass"].attrs["long_name"] = (
            "Zooplankton Wet Weight Biomass Concentration"
        )

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

        if val_col:
            f.write("## 3. Time Series\n")
            f.write(f"![Time Series](figures/time_series_{val_col}.png)\n\n")

    print("Done.") if val_col else print("Done/Warning: No biomass column found.")


if __name__ == "__main__":
    main()
