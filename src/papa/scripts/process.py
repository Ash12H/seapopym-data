"""
PAPA Station Processing Script
Processes zooplankton data from DFO Canada Zooplankton Database
Following the validated workflow from ANALYSIS_PAPA.md
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
    STATION_DIR = PROJECT_ROOT / "src" / "papa"
    OLD_DIR = PROJECT_ROOT / "OLD_src" / "papa"
    RAW_DIR = OLD_DIR / "1_raw"
    RELEASE_DIR = STATION_DIR / "release"
    REPORTS_DIR = STATION_DIR / "reports"
    FIGURES_DIR = REPORTS_DIR / "figures"

    # Create directories
    RELEASE_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    # Files
    INPUT_FILE = RAW_DIR / "papa_zooplankton.csv"
    OUTPUT_NC = RELEASE_DIR / "papa_zooplankton_obs.nc"
    REPORT_FILE = REPORTS_DIR / "report.md"

    print("=" * 60)
    print("Processing PAPA Station (DFO Canada Zooplankton Database)")
    print("=" * 60)
    print(f"Input:  {INPUT_FILE}")
    print(f"Output: {OUTPUT_NC}")
    print()

    if not INPUT_FILE.exists():
        print(f"❌ Error: Input file {INPUT_FILE} not found.")
        return

    # ========== 1. LOAD DATA ==========
    print("📂 Loading data...")
    # PAPA uses ';' separator and ',' as decimal
    df = pd.read_csv(
        INPUT_FILE, sep=";", decimal=",", on_bad_lines="skip", low_memory=False
    )
    print(f"   Loaded {len(df)} rows")
    print()

    # ========== 2. IDENTIFY TAXONOMIC COLUMNS (BEFORE ADDING NEW COLS) ==========
    print("🔬 Identifying taxonomic columns...")
    # Taxonomic columns start at index 20
    taxa_cols = df.columns[20:].tolist()

    # Exclude adult polychaetes (benthic, not pelagic)
    excluded_taxa = [
        "ANNE:POLY: >> POLY s1",
        "ANNE:POLY: >> POLY s2",
        "ANNE:POLY: >> POLY s3",
    ]

    taxa_cols_to_sum = [col for col in taxa_cols if col not in excluded_taxa]

    print(f"   Total taxonomic columns: {len(taxa_cols)}")
    print(f"   Excluded (adult polychaetes): {len(excluded_taxa)}")
    print(f"   To sum: {len(taxa_cols_to_sum)} taxa")
    print()

    # ========== 3. CLEAN COLUMNS ==========
    print("🧹 Cleaning columns...")
    # Convert lat/lon (they are strings with '.' decimal)
    df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
    df["lon"] = pd.to_numeric(df["lon"], errors="coerce")
    df["DEPTH_STRT"] = pd.to_numeric(df["DEPTH_STRT"], errors="coerce")
    print()

    # ========== 4. FILTER DATA ==========
    print("🔍 Filtering data...")
    initial_rows = len(df)

    # Filter 1: Exclude depth < 50m (aberrant tows)
    excluded_shallow = df[df["DEPTH_STRT"] < 50]
    print(f"   Excluding {len(excluded_shallow)} rows with depth < 50m")
    df = df[df["DEPTH_STRT"] >= 50]

    print(f"   Result: {len(df)} rows")
    print()

    # ========== 5. TEMPORAL PROCESSING ==========
    print("⏰ Processing temporal data...")

    # Parse date: format "24 9 1995" (D M Y)
    df["time"] = pd.to_datetime(df["Date"], format="%d %m %Y", errors="coerce")
    df["date"] = df["time"].dt.floor("D")

    # Parse hour from STN_TIME: "2030" -> 20h
    def extract_hour(stn_time):
        try:
            time_str = str(stn_time).strip().zfill(4)
            if len(time_str) > 4:
                time_str = time_str.split(".")[0].zfill(4)
            hh = int(time_str[:2])
            if hh == 24:
                hh = 0
            return hh
        except:
            return None

    df["hour"] = df["STN_TIME"].apply(extract_hour)

    # Day/Night from Twilight column
    df["day_night"] = df["Twilight"].apply(
        lambda x: "day" if x == "Daylight" else "night"
    )
    print()

    # ========== 6. DEPTH CATEGORIZATION ==========
    print("📊 Categorizing by depth...")
    df["depth_category"] = np.where(
        df["DEPTH_STRT"] <= 150, "epipelagic_only", "epipelagic_mesopelagic"
    )
    print()

    # ========== 7. STORE TOW METADATA ==========
    df["tow_depth_max"] = df["DEPTH_STRT"]

    # ========== 8. SPATIAL BINNING (0.5°) ==========
    print("🗺️  Binning spatial grid (0.5° resolution)...")
    df["lat_bin"] = (df["lat"] * 2).round() / 2
    df["lon_bin"] = (df["lon"] * 2).round() / 2
    print(f"   Latitude range: {df['lat_bin'].min():.1f}° to {df['lat_bin'].max():.1f}°")
    print(f"   Longitude range: {df['lon_bin'].min():.1f}° to {df['lon_bin'].max():.1f}°")
    print()

    # ========== 9. SUM TAXA ==========
    print("➕ Summing taxonomic biomass...")
    # Sum all taxa (identified at the beginning)
    df["biomass_dry"] = df[taxa_cols_to_sum].sum(axis=1)
    print(f"   ✓ Summed {len(taxa_cols_to_sum)} taxa")
    print()

    # ========== 10. IDENTIFY TOWS ==========
    print("🎣 Identifying tows...")
    df["tow_id"] = df.groupby(
        ["date", "lat_bin", "lon_bin", "DEPTH_STRT"]
    ).ngroup()
    n_tows = df["tow_id"].nunique()
    print(f"   Identified {n_tows} unique tows")
    print()

    # ========== 11. AGGREGATION LEVEL 1: Average per tow ==========
    print("🔢 Aggregating per tow...")
    agg1 = (
        df.groupby(
            ["date", "lat_bin", "lon_bin", "day_night", "depth_category", "tow_id"]
        )
        .agg({"biomass_dry": "mean", "tow_depth_max": "first"})
        .reset_index()
    )
    print(f"   Aggregated {len(df)} rows → {len(agg1)} tows")
    print()

    # ========== 12. AGGREGATION LEVEL 2: Median per day/category/cell ==========
    print("📈 Aggregating tows per day/category/cell...")
    final = (
        agg1.groupby(["date", "lat_bin", "lon_bin", "day_night", "depth_category"])
        .agg({"biomass_dry": "median", "tow_depth_max": "median"})
        .reset_index()
    )
    print(f"   Result: {len(final)} spatio-temporal observations")
    print()

    # ========== 13. CONVERT TO XARRAY ==========
    print("🗂️  Converting to xarray...")
    ds = xr.Dataset.from_dataframe(
        final.set_index(
            ["date", "lat_bin", "lon_bin", "depth_category", "day_night"]
        )
    )
    ds = ds.rename({"date": "time", "lat_bin": "lat", "lon_bin": "lon"})
    print()

    # ========== 14. ADD METADATA ==========
    print("📝 Adding metadata...")
    ds.attrs["title"] = "PAPA Zooplankton Observations"
    ds.attrs["source"] = "DFO Canada Zooplankton Database"
    ds.attrs["institution"] = "DFO (Department of Fisheries and Oceans Canada)"
    ds.attrs["region"] = "North Pacific (46-58°N, -158 to -128°W)"
    ds.attrs["net_type"] = "Bongo (majority), mesh 236 µm"
    ds.attrs["spatial_resolution"] = "0.5 degrees"
    ds.attrs["processing_date"] = datetime.now().isoformat()
    ds.attrs[
        "excluded_data"
    ] = "depth <50m, adult polychaetes (ANNE:POLY s1, s2, s3 - benthic)"
    ds.attrs["conventions"] = "CF-1.8"

    ds["biomass_dry"].attrs = {
        "units": "mg m-3",
        "long_name": "Dry weight biomass concentration",
        "comment": "Sum of 91 planktonic taxa (excludes adult polychaetes)",
    }
    ds["tow_depth_max"].attrs = {"units": "m", "long_name": "Maximum tow depth"}

    ds["lat"].attrs = {
        "units": "degrees_north",
        "long_name": "Latitude (binned 0.5°)",
        "axis": "Y",
    }
    ds["lon"].attrs = {
        "units": "degrees_east",
        "long_name": "Longitude (binned 0.5°)",
        "axis": "X",
    }
    print()

    # ========== 15. SAVE NETCDF ==========
    print("💾 Saving NetCDF...")
    ds.to_netcdf(OUTPUT_NC, mode="w")
    print(f"   ✓ Saved to {OUTPUT_NC}")
    print()

    # ========== 16. GENERATE FIGURES ==========
    print("📊 Generating figures...")
    try:
        import matplotlib.pyplot as plt

        # Time series by depth category
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        for i, depth_cat in enumerate(["epipelagic_only", "epipelagic_mesopelagic"]):
            for j, dn in enumerate(["day", "night"]):
                ax = axes[i, j]
                subset = final[
                    (final["depth_category"] == depth_cat)
                    & (final["day_night"] == dn)
                ]
                if not subset.empty:
                    # Group by date and take mean over spatial cells
                    ts = subset.groupby("date")["biomass_dry"].mean()
                    ax.plot(ts.index, ts.values, "o-", alpha=0.6, markersize=3)
                    ax.set_title(f"{depth_cat} - {dn}")
                    ax.set_ylabel("Biomass (mg/m³)")
                    ax.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(FIGURES_DIR / "time_series_biomass.png", dpi=150)
        plt.close()
        print("   ✓ time_series_biomass.png")
    except Exception as e:
        print(f"   ⚠ Error generating time series: {e}")

    try:
        # Spatial map of mean biomass
        fig, ax = plt.subplots(figsize=(10, 8))
        spatial_mean = final.groupby(["lat_bin", "lon_bin"])["biomass_dry"].mean()
        scatter = ax.scatter(
            spatial_mean.index.get_level_values(1),
            spatial_mean.index.get_level_values(0),
            c=spatial_mean.values,
            s=50,
            cmap="YlOrRd",
            alpha=0.7,
        )
        plt.colorbar(scatter, ax=ax, label="Mean Biomass (mg/m³)")
        ax.set_xlabel("Longitude")
        ax.set_ylabel("Latitude")
        ax.set_title("PAPA Spatial Distribution (mean biomass)")
        ax.grid(True, alpha=0.3)
        plt.savefig(FIGURES_DIR / "map.png", dpi=150)
        plt.close()
        print("   ✓ map.png")
    except Exception as e:
        print(f"   ⚠ Error generating map: {e}")
    print()

    # ========== 17. GENERATE REPORT ==========
    print("📄 Generating report...")
    with open(REPORT_FILE, "w") as f:
        f.write("# PAPA Station Report\n\n")
        f.write(f"**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(
            f"**Region**: North Pacific ({df['lat'].min():.1f}-{df['lat'].max():.1f}°N, "
            f"{df['lon'].min():.1f}-{df['lon'].max():.1f}°W)\n\n"
        )

        f.write("## Summary\n\n")
        f.write(f"- Initial rows: {initial_rows:,}\n")
        f.write(f"- Final observations: {len(final):,}\n")
        f.write(f"- Unique tows: {n_tows:,}\n")
        f.write(f"- Period: {df['time'].min().date()} to {df['time'].max().date()}\n")
        f.write(f"- Spatial cells (0.5°): {final[['lat_bin', 'lon_bin']].drop_duplicates().shape[0]}\n\n")

        f.write("### Exclusions\n\n")
        f.write(f"- Depth <50m: {len(excluded_shallow)} rows\n")
        f.write(f"- Adult polychaetes: {len(excluded_taxa)} taxa columns (benthic species)\n\n")

        f.write("### Depth Categories\n\n")
        epi_only = final[final["depth_category"] == "epipelagic_only"]
        epi_meso = final[final["depth_category"] == "epipelagic_mesopelagic"]
        f.write(f"- Epipelagic only (≤150m): {len(epi_only)} observations\n")
        f.write(
            f"  - Mean tow depth: {epi_only['tow_depth_max'].mean():.1f}m\n"
        )
        f.write(
            f"- Epipelagic + Mesopelagic (>150m): {len(epi_meso)} observations\n"
        )
        f.write(
            f"  - Mean tow depth: {epi_meso['tow_depth_max'].mean():.1f}m\n\n"
        )

        f.write("### Biomass Statistics\n\n")
        f.write("| Metric | Mean | Median | Min | Max |\n")
        f.write("|--------|------|--------|-----|-----|\n")
        stats = final["biomass_dry"].describe()
        f.write(
            f"| Dry Weight (mg/m³) | {stats['mean']:.2f} | {stats['50%']:.2f} | "
            f"{stats['min']:.2f} | {stats['max']:.2f} |\n\n"
        )

        f.write("## Figures\n\n")
        f.write("![Map](figures/map.png)\n\n")
        f.write("![Time Series](figures/time_series_biomass.png)\n\n")

        f.write("## Methodology\n\n")
        f.write("**Sampling Method**: Oblique tows from surface to maximum depth\n\n")
        f.write("**Net**: Bongo (majority) with 236 µm mesh\n\n")
        f.write("**Taxonomic Groups**: 91 planktonic taxa (94 total - 3 benthic polychaetes)\n\n")
        f.write("**Spatial Resolution**: 0.5° grid\n\n")
        f.write("**Aggregation**:\n")
        f.write("1. Sum of 91 taxa per tow\n")
        f.write("2. Median of tows per day/depth_category/spatial_cell\n\n")

    print(f"   ✓ {REPORT_FILE}")
    print()

    print("=" * 60)
    print("✅ Processing complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
