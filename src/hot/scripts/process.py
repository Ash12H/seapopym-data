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

    # Rename columns to standard names
    # wwt: Wet Weight [g/m2] -> biomass [mg/m3] (conversion needed)
    # dwt: Dry Weight [g/m2] -> biomass_dry [mg/m3]
    # abnd: Abundance [#/m2?] -> abundance [#/m3?]
    # depth: Tow depth [m]

    rename_map = {
        "wwt": "biomass_wet_g_m2",
        "dwt": "biomass_dry_g_m2",
        "abnd": "abundance_raw",
        "vol": "volume_filtered",
        "mk_date": "time",  # Sometimes date is in a different column?
    }
    # Check if 'time' column already exists and is correct

    df = df.rename(columns=rename_map)

    if "time" in df.columns:
        df["time"] = pd.to_datetime(df["time"]).dt.tz_localize(None)

    # Clean object columns
    for col in df.select_dtypes(include=["object", "category"]).columns:
        df[col] = df[col].astype(str)

    # Aggregate by Tow (sum fractions)
    # The data contains size fractions (frac 0-5) for each tow.
    # We need to sum the biomass/abundance to get the total for the tow.
    # Metadata (lat, lon, depth, time) should be constant per tow.

    # Identify grouping columns
    group_cols = ["cruise", "tow"]

    # Identify columns to sum
    sum_cols = ["wwt", "dwt", "carb", "nit", "abnd"]
    sum_cols = [c for c in sum_cols if c in df.columns]

    # Identify columns to keep (take first)
    # We use all other columns not in group or sum
    first_cols = [c for c in df.columns if c not in group_cols + sum_cols]

    agg_dict = {c: "sum" for c in sum_cols}
    agg_dict.update({c: "first" for c in first_cols})

    print(f"Aggregating {len(df)} rows by cruise/tow...")
    df = df.groupby(group_cols, as_index=False).agg(agg_dict)
    print(f"Result: {len(df)} tows.")

    # Sort by time
    if "time" in df.columns:
        df = df.sort_values("time")

    # Rename columns to standard names
    rename_map = {
        "wwt": "biomass_wet_g_m2",
        "dwt": "biomass_dry_g_m2",
        "abnd": "abundance_raw",
        "vol": "volume_filtered",
        "mk_date": "time",
    }
    df = df.rename(columns=rename_map)

    # Ensure lat/lon are floats
    if "lat" in df.columns:
        df["lat"] = df["lat"].astype(float)
    if "lon" in df.columns:
        df["lon"] = df["lon"].astype(float)

    # Convert Units
    # Total Biomass Area Density (g/m2) -> Concentration (mg/m3)
    # Assumption: wwt, dwt are in g/m^2 (integrated). depth is in m.
    # Target: mg/m^3 (concentration)
    # Formula: (val_g_m2 * 1000) / depth_m

    if "biomass_wet_g_m2" in df.columns and "depth" in df.columns:
        df["biomass"] = (df["biomass_wet_g_m2"] * 1000) / df["depth"]
        print("Converted biomass_wet_g_m2 to biomass (mg/m3)")

    if "biomass_dry_g_m2" in df.columns and "depth" in df.columns:
        df["biomass_dry"] = (df["biomass_dry_g_m2"] * 1000) / df["depth"]
        print("Converted biomass_dry_g_m2 to biomass_dry (mg/m3)")

    # Clean object columns
    for col in df.select_dtypes(include=["object", "category"]).columns:
        df[col] = df[col].astype(str)

    # 3. Generate Figures
    print("Generating figures...")
    Plotter.plot_missing_values(df, FIGURES_DIR / "missing_values.png")

    val_col = "biomass" if "biomass" in df.columns else None

    if val_col and "time" in df.columns:
        Plotter.plot_time_series(
            df,
            "time",
            val_col,
            f"HOT Zooplankton {val_col}",
            FIGURES_DIR / f"time_series_{val_col}.png",
            ylabel="mg/m3",
        )

    if "lat" in df.columns and "lon" in df.columns:
        Plotter.plot_scatter_map(df, "lat", "lon", FIGURES_DIR / "map.png")

    # 4. Export to NetCDF
    print("Exporting to NetCDF...")
    ds = df.to_xarray()
    ds.attrs["history"] = f"Created on {datetime.now()} using seapopym-data pipeline."
    ds.attrs["source"] = "HOT Zooplankton Data"

    # Add attributes to variables
    if "biomass" in ds:
        ds["biomass"].attrs["units"] = "mg/m^3"
        ds["biomass"].attrs["long_name"] = (
            "Zooplankton Wet Weight Biomass Concentration"
        )

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

    print("Done.") if val_col else print("Done/Warning: No biomass column found.")


if __name__ == "__main__":
    main()
