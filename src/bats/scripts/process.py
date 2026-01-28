"""
BATS Station Processing Script
Processes zooplankton data from Bermuda Atlantic Time-series Study (BATS)
Following the validated workflow from ANALYSIS_BATS.md
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
import xarray as xr
from datetime import datetime

# Add src to python path to allow importing core
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.append(str(PROJECT_ROOT / "src"))

from core.plotting import Plotter


def main():
    # ========== PATHS ==========
    STATION_DIR = PROJECT_ROOT / "src" / "bats"
    OLD_DIR = PROJECT_ROOT / "OLD_src" / "bats"
    RAW_DIR = OLD_DIR / "1_raw"
    RELEASE_DIR = STATION_DIR / "release"
    REPORTS_DIR = STATION_DIR / "reports"
    FIGURES_DIR = REPORTS_DIR / "figures"

    # Create directories
    RELEASE_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    # Files
    INPUT_FILE = RAW_DIR / "bats_zooplankton.csv"
    OUTPUT_NC = RELEASE_DIR / "bats_zooplankton_obs.nc"
    REPORT_FILE = REPORTS_DIR / "report.md"

    print("=" * 60)
    print("Processing BATS Station (Bermuda Atlantic Time-series)")
    print("=" * 60)
    print(f"Input:  {INPUT_FILE}")
    print(f"Output: {OUTPUT_NC}")
    print()

    if not INPUT_FILE.exists():
        print(f"❌ Error: Input file {INPUT_FILE} not found.")
        return

    # ========== 1. LOAD DATA ==========
    print("📂 Loading data...")
    df = pd.read_csv(INPUT_FILE, index_col=0)
    print(f"   Loaded {len(df)} rows")
    print()

    # ========== 2. FILTER DATA ==========
    print("🔍 Filtering data...")
    initial_rows = len(df)

    # Filter 1: Exclude depth < 50m (aberrant tows)
    excluded_shallow = df[df["depth"] < 50]
    print(f"   Excluding {len(excluded_shallow)} rows with depth < 50m")
    df = df[df["depth"] >= 50]

    # Filter 2: Exclude sieve_size = 5000µm (micronekton)
    excluded_5000 = df[df["sieve_size"] == 5000.0]
    print(f"   Excluding {len(excluded_5000)} rows with sieve_size=5000µm")
    df = df[df["sieve_size"] != 5000.0]

    # Filter 3: Exclude rows without sieve_size
    excluded_no_sieve = df[df["sieve_size"].isna()]
    print(f"   Excluding {len(excluded_no_sieve)} rows without sieve_size")
    df = df[df["sieve_size"].notna()]

    print(f"   Result: {len(df)} rows")
    print()

    # ========== 3. TEMPORAL PROCESSING ==========
    print("⏰ Processing temporal data...")
    df["time"] = pd.to_datetime(df["time"])
    df["date"] = df["time"].dt.floor("D")
    df["hour"] = df["time"].dt.hour
    df["day_night"] = df["hour"].apply(lambda h: "day" if 6 <= h < 18 else "night")
    print()

    # ========== 4. DEPTH CATEGORIZATION ==========
    print("📊 Categorizing by depth...")
    df["depth_category"] = np.where(
        df["depth"] <= 150, "epipelagic_only", "epipelagic_mesopelagic"
    )
    print()

    # ========== 5. STORE TOW METADATA ==========
    df["tow_depth_max"] = df["depth"]

    # ========== 6. IDENTIFY TOWS ==========
    df["tow_id"] = df.groupby(["date", "depth"]).ngroup()
    n_tows = df["tow_id"].nunique()
    print(f"   Identified {n_tows} unique tows")
    print()

    # ========== 7. AGGREGATION LEVEL 1: Sum fractions per tow ==========
    print("🔢 Aggregating fractions per tow...")
    agg1 = (
        df.groupby(["date", "day_night", "depth_category", "tow_id"])
        .agg(
            {
                "dry_weight_vol_water_ratio": "sum",
                "wet_weight_vol_water_ratio": "sum",
                "tow_depth_max": "first",
                "lat": "first",
                "lon": "first",
            }
        )
        .reset_index()
    )
    print(f"   Aggregated {len(df)} rows → {len(agg1)} tows")
    print()

    # ========== 8. AGGREGATION LEVEL 2: Median per day/category ==========
    print("📈 Aggregating tows per day/category...")
    final = (
        agg1.groupby(["date", "day_night", "depth_category"])
        .agg(
            {
                "dry_weight_vol_water_ratio": "median",
                "wet_weight_vol_water_ratio": "median",
                "tow_depth_max": "median",
                "lat": "first",
                "lon": "first",
            }
        )
        .reset_index()
    )
    print(f"   Result: {len(final)} daily observations")
    print()

    # ========== 9. CONVERT TO XARRAY ==========
    print("🗂️  Converting to xarray...")
    ds = xr.Dataset.from_dataframe(
        final.set_index(["date", "depth_category", "day_night"])
    )
    ds = ds.rename(
        {
            "date": "time",
            "dry_weight_vol_water_ratio": "biomass_dry",
            "wet_weight_vol_water_ratio": "biomass_wet",
        }
    )
    print()

    # ========== 10. ADD METADATA ==========
    print("📝 Adding metadata...")
    ds.attrs["title"] = "BATS Zooplankton Observations"
    ds.attrs["station"] = "BATS"
    ds.attrs["location"] = "31.6°N, -64.2°W"
    ds.attrs["institution"] = "BBSR"
    ds.attrs["net_type"] = "1 m² rectangular, 202 µm mesh"
    ds.attrs["size_range"] = "0.2-5 mm (fractions 200-2000µm)"
    ds.attrs["processing_date"] = datetime.now().isoformat()
    ds.attrs["excluded_data"] = "depth <50m, sieve_size=5000µm, missing sieve_size"
    ds.attrs["conventions"] = "CF-1.8"

    ds["biomass_dry"].attrs = {
        "units": "mg m-3",
        "long_name": "Dry weight biomass concentration",
    }
    ds["biomass_wet"].attrs = {
        "units": "mg m-3",
        "long_name": "Wet weight biomass concentration",
    }
    ds["tow_depth_max"].attrs = {"units": "m", "long_name": "Maximum tow depth"}
    print()

    # ========== 11. SAVE NETCDF ==========
    print("💾 Saving NetCDF...")
    ds.to_netcdf(OUTPUT_NC, mode="w")
    print(f"   ✓ Saved to {OUTPUT_NC}")
    print()

    # ========== 12. GENERATE FIGURES ==========
    print("📊 Generating figures...")
    try:
        import matplotlib.pyplot as plt

        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        for i, depth_cat in enumerate(["epipelagic_only", "epipelagic_mesopelagic"]):
            for j, dn in enumerate(["day", "night"]):
                ax = axes[i, j]
                subset = final[
                    (final["depth_category"] == depth_cat)
                    & (final["day_night"] == dn)
                ]
                if not subset.empty:
                    ax.plot(subset["date"], subset["dry_weight_vol_water_ratio"], "o-", alpha=0.6)
                    ax.set_title(f"{depth_cat} - {dn}")
                    ax.set_ylabel("Biomass (mg/m³)")
                    ax.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(FIGURES_DIR / "time_series_biomass.png", dpi=150)
        plt.close()
        print("   ✓ time_series_biomass.png")
    except Exception as e:
        print(f"   ⚠ Error: {e}")

    try:
        fig, ax = plt.subplots(figsize=(8, 6))
        ax.scatter(final["lon"].iloc[0], final["lat"].iloc[0], s=200, c="red", marker="*")
        ax.set_xlabel("Longitude")
        ax.set_ylabel("Latitude")
        ax.set_title("BATS Location")
        ax.grid(True, alpha=0.3)
        plt.savefig(FIGURES_DIR / "map.png", dpi=150)
        plt.close()
        print("   ✓ map.png")
    except Exception as e:
        print(f"   ⚠ Error: {e}")
    print()

    # ========== 13. GENERATE REPORT ==========
    print("📄 Generating report...")
    with open(REPORT_FILE, "w") as f:
        f.write("# BATS Station Report\n\n")
        f.write(f"**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**Location**: 31.6°N, -64.2°W\n\n")
        f.write("## Summary\n\n")
        f.write(f"- Initial rows: {initial_rows:,}\n")
        f.write(f"- Final rows: {len(final):,}\n")
        f.write(f"- Period: {df['time'].min().date()} to {df['time'].max().date()}\n\n")
        f.write("### Exclusions\n\n")
        f.write(f"- Depth <50m: {len(excluded_shallow)} rows\n")
        f.write(f"- Sieve 5000µm: {len(excluded_5000)} rows\n")
        f.write(f"- Missing sieve: {len(excluded_no_sieve)} rows\n\n")
        f.write("## Figures\n\n")
        f.write("![Map](figures/map.png)\n\n")
        f.write("![Time Series](figures/time_series_biomass.png)\n\n")
    print(f"   ✓ {REPORT_FILE}")
    print()

    print("=" * 60)
    print("✅ Processing complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
