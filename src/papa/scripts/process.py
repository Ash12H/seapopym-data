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
    STATION_DIR = PROJECT_ROOT / "src" / "papa"
    RAW_DIR = STATION_DIR / "data" / "raw"
    RELEASE_DIR = STATION_DIR / "release"
    REPORTS_DIR = STATION_DIR / "reports"
    FIGURES_DIR = REPORTS_DIR / "figures"

    # Files
    INPUT_FILE = RAW_DIR / "papa_zooplankton.csv"
    OUTPUT_NC = RELEASE_DIR / "papa_zooplankton_obs.nc"
    REPORT_FILE = REPORTS_DIR / "report.md"

    print("Processing PAPA station...")
    print(f"Input: {INPUT_FILE}")

    if not INPUT_FILE.exists():
        print(f"Error: Input file {INPUT_FILE} not found.")
        return

    # 1. Load Data
    # PAPA data uses ';' as separator and ',' as decimal
    # Also has potential bad lines due to comments
    df = DataLoader.load_csv(
        INPUT_FILE, sep=";", decimal=",", on_bad_lines="skip", low_memory=False
    )

    # 2. Process
    print("Cleaning data...")
    # 2. Process
    print("Cleaning data...")

    # Clean object columns
    for col in df.select_dtypes(include=["object", "category"]).columns:
        df[col] = df[col].astype(str)

    # Clean Lat/Lon
    # They use '.' decimal compared to loaded ',' preference, so they remain strings
    if "lat" in df.columns:
        df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
    if "lon" in df.columns:
        df["lon"] = pd.to_numeric(df["lon"], errors="coerce")

    # Handle Depth
    # 'DEPTH_STRT' seems to be the tow depth (e.g. 246m, 150m)
    # 'DEPTH_END' is consistently 0 (surface)
    if "DEPTH_STRT" in df.columns:
        df["depth"] = pd.to_numeric(df["DEPTH_STRT"], errors="coerce")

    # Create Time column
    # Date: "24 9 1995" (D M Y)
    # STN_TIME: "2030" (HHMM)

    def parse_datetime(row):
        try:
            date_str = str(row["Date"]).strip()
            time_str = str(row["STN_TIME"]).strip()

            # Pad time to 4 digits
            time_str = time_str.zfill(4)
            if len(time_str) > 4:  # Handle 2030.0 if valid float
                time_str = time_str.split(".")[0].zfill(4)

            hh = time_str[:2]
            mm = time_str[2:]

            # Handle 2400
            if hh == "24":
                hh = "00"

            # Parse Date
            # Format appears to be "%d %m %Y" from "24 9 1995"
            dt_str = f"{date_str} {hh}:{mm}:00"
            return datetime.strptime(dt_str, "%d %m %Y %H:%M:%S")
        except Exception:
            return pd.NaT

    if "Date" in df.columns and "STN_TIME" in df.columns:
        print("Parsing datetime...")
        df["time"] = df.apply(parse_datetime, axis=1)
        df = df.dropna(subset=["time"])

    # 3. Identify Recurring Stations
    print("Analyzing station recurrence...")
    station_counts = df["Station"].value_counts()
    recurring_stations = station_counts[station_counts > 1]

    df["Status"] = df["Station"].apply(
        lambda x: "Recurring (>1 obs)"
        if x in recurring_stations.index
        else "Single (1 obs)"
    )

    # 4. Generate Figures
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
            f"PAPA Zooplankton {val_col}",
            FIGURES_DIR / f"time_series_{val_col}.png",
        )

    if "lat" in df.columns and "lon" in df.columns:
        Plotter.plot_scatter_map(
            df, "lat", "lon", FIGURES_DIR / "map.png", hue="Status"
        )

    # 5. Export to NetCDF
    print("Exporting to NetCDF...")
    ds = df.to_xarray()
    ds.attrs["history"] = f"Created on {datetime.now()} using seapopym-data pipeline."
    ds.attrs["source"] = "PAPA Zooplankton Data"

    DataWriter.save_nc(ds, OUTPUT_NC)

    # 6. Generate Report
    print("Generating report...")
    with open(REPORT_FILE, "w") as f:
        f.write("# PAPA Station Report\n\n")
        f.write(f"**Date**: {datetime.now()}\n")
        f.write(f"**Input**: `{INPUT_FILE.name}`\n")
        f.write(f"**Output**: `{OUTPUT_NC.name}`\n\n")

        f.write("## 1. Data Quality\n")
        f.write("![Missing Values](figures/missing_values.png)\n\n")

        f.write("## 2. Geography\n")
        if (FIGURES_DIR / "map.png").exists():
            f.write("![Map](figures/map.png)\n\n")

            f.write("### Recurring Stations (>1 observations)\n")
            f.write(f"Total recurring stations: {len(recurring_stations)}\n\n")
            f.write("| Station | Occurrences |\n")
            f.write("| ------- | ----------- |\n")
            for station, count in recurring_stations.items():
                f.write(f"| {station} | {count} |\n")
            f.write("\n")
        else:
            f.write("*No geographic data found.*\n\n")

        if val_col:
            f.write("## 3. Time Series\n")
            f.write(f"![Time Series](figures/time_series_{val_col}.png)\n\n")

    print("Done.")


if __name__ == "__main__":
    main()
