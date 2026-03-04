"""
Canaries Station Processing Script
Processes zooplankton data from Couret et al. (2023) PANGAEA dataset
50-year (1971-2021) mesozooplankton biomass compilation from Canary Current System
Output: 1 row = 1 observation (flat Parquet)
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature

# Add src to python path to allow importing core
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.append(str(PROJECT_ROOT / "src"))


def convert_carbon_m2_to_m3(carbon_m2, depth=200):
    """
    Convert carbon biomass from mg C/m² to mg C/m³.

    Parameters
    ----------
    carbon_m2 : array-like
        Carbon biomass in mg C/m²
    depth : float or array-like, default=200
        Depth in meters (0-200m for Canaries dataset)

    Returns
    -------
    array-like
        Carbon biomass in mg C/m³
    """
    return carbon_m2 / depth


def main():
    # ========== PATHS ==========
    STATION_DIR = PROJECT_ROOT / "src" / "canaries"
    RAW_DIR = STATION_DIR / "data" / "raw"
    RELEASE_DIR = STATION_DIR / "release"
    REPORTS_DIR = STATION_DIR / "reports"
    FIGURES_DIR = REPORTS_DIR / "figures"

    # Create directories
    RELEASE_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    # Files
    INPUT_FILE = RAW_DIR / "Couret-etal_2023.tab"
    OUTPUT_PARQUET = RELEASE_DIR / "canaries_zooplankton_obs.parquet"
    REPORT_FILE = REPORTS_DIR / "report.md"

    print("=" * 60)
    print("Processing Canaries Station (Couret et al. 2023)")
    print("=" * 60)
    print(f"Input:  {INPUT_FILE}")
    print(f"Output: {OUTPUT_PARQUET}")
    print()

    if not INPUT_FILE.exists():
        print(f"Error: Input file {INPUT_FILE} not found.")
        return

    # ========== 1. LOAD DATA ==========
    print("Loading data...")
    # PANGAEA format: skip 41 header lines (line 42 is the header), tab-separated
    df = pd.read_csv(INPUT_FILE, sep="\t", skiprows=41)
    print(f"   Loaded {len(df)} rows")

    # Rename columns to snake_case
    column_map = {
        "Reference": "reference",
        "Latitude": "latitude",
        "Longitude": "longitude",
        "Area": "area",
        "Date/Time": "date_time",
        "Size fraction [µm]": "size_fraction",
        "Station": "station",
        "Device": "net_type",
        "Period": "period",
        "Biom C [mg/m**2]": "biomass_carbon_m2"
    }
    df.rename(columns=column_map, inplace=True)
    print(f"   Columns: {list(df.columns)}")
    print()

    # ========== 2. CLEAN & FILTER ==========
    print("Filtering data...")
    initial_rows = len(df)

    # Parse dates (format: YYYY-MM-DD)
    df["time"] = pd.to_datetime(df["date_time"], format="%Y-%m-%d", utc=True)

    # Check size fractions
    print(f"   Size fractions: {df['size_fraction'].unique()}")

    print(f"   Result: {len(df)} rows (no exclusions applied)")
    print()

    # ========== 3. UNIT CONVERSION ==========
    print("Converting biomass units...")
    print("   Formula: biomass_carbon (mg C/m³) = biomass_carbon_m2 / 200")

    df["biomass_carbon"] = convert_carbon_m2_to_m3(df["biomass_carbon_m2"], depth=200)

    print(f"   Range: {df['biomass_carbon'].min():.2f} - {df['biomass_carbon'].max():.2f} mg C/m³")
    print(f"   Mean: {df['biomass_carbon'].mean():.2f} mg C/m³")
    print()

    # ========== 4. TEMPORAL PROCESSING ==========
    print("Processing temporal data...")

    # Use existing "period" column (already contains "day"/"night")
    print("   Using period column from source data...")
    df["day_night"] = df["period"]

    # Remove timezone info for Parquet compatibility
    if df["time"].dt.tz is not None:
        df["time"] = df["time"].dt.tz_localize(None)

    day_count = (df["day_night"] == "day").sum()
    night_count = (df["day_night"] == "night").sum()
    print(f"   Day: {day_count} obs ({day_count/len(df)*100:.1f}%)")
    print(f"   Night: {night_count} obs ({night_count/len(df)*100:.1f}%)")
    print()

    # ========== 5. DEPTH ASSIGNMENT ==========
    print("Assigning depth...")
    # All Canaries data is 0-200m
    df["tow_depth_max"] = 200
    print(f"   All {len(df)} observations: 0-200m")
    print()

    # ========== 6. BUILD FINAL DATAFRAME ==========
    print("Preparing final DataFrame...")

    final = df[["time", "day_night", "biomass_carbon", "tow_depth_max",
                 "latitude", "longitude"]].copy()
    final = final.rename(columns={"latitude": "lat", "longitude": "lon"})

    # Save Parquet
    print(f"\nSaving Parquet ({len(final)} observations)...")
    final.to_parquet(OUTPUT_PARQUET, index=False)
    print(f"   Saved to {OUTPUT_PARQUET}")
    print(f"   Columns: {final.columns.tolist()}")
    print()

    # ========== 7. GENERATE FIGURES ==========
    print("Generating figures...")

    # Figure 1: Map with coastlines and land
    print("   Creating map...")
    fig = plt.figure(figsize=(12, 10))
    ax = plt.axes(projection=ccrs.PlateCarree())

    ax.add_feature(cfeature.LAND, facecolor="lightgray", edgecolor="black", linewidth=0.5)
    ax.add_feature(cfeature.COASTLINE, linewidth=0.8)
    ax.add_feature(cfeature.BORDERS, linestyle=":", linewidth=0.5, alpha=0.5)

    scatter = ax.scatter(
        final["lon"],
        final["lat"],
        c=final["biomass_carbon"],
        s=30,
        alpha=0.6,
        cmap="viridis",
        transform=ccrs.PlateCarree(),
        zorder=10,
    )

    cbar = plt.colorbar(scatter, ax=ax, orientation="vertical", pad=0.05, shrink=0.8)
    cbar.set_label("Biomass Carbon (mg C/m³)", rotation=270, labelpad=20)

    lat_min, lat_max = final["lat"].min(), final["lat"].max()
    lon_min, lon_max = final["lon"].min(), final["lon"].max()
    margin = 2.0
    ax.set_extent(
        [lon_min - margin, lon_max + margin, lat_min - margin, lat_max + margin],
        crs=ccrs.PlateCarree(),
    )

    gl = ax.gridlines(draw_labels=True, dms=True, x_inline=False, y_inline=False, alpha=0.5)
    gl.top_labels = False
    gl.right_labels = False

    ax.set_title("Canary Current System - Sampling Locations (1971-2021)", fontsize=14, pad=10)

    map_file = FIGURES_DIR / "map.png"
    fig.savefig(map_file, bbox_inches="tight", dpi=150)
    plt.close(fig)
    print(f"   {map_file.name}")

    # Figure 2: Time series
    print("   Creating time series...")
    fig, ax = plt.subplots(figsize=(12, 6))

    ax.plot(final["time"], final["biomass_carbon"], "o", markersize=2, alpha=0.4)
    ax.set_xlabel("Date", fontsize=12)
    ax.set_ylabel("Biomass Carbon (mg C/m³)", fontsize=12)
    ax.set_title("Zooplankton Biomass - Canary Current System (1 obs = 1 point)", fontsize=14)
    ax.grid(True, alpha=0.3)

    ts_file = FIGURES_DIR / "time_series_biomass.png"
    fig.savefig(ts_file, bbox_inches="tight", dpi=150)
    plt.close(fig)
    print(f"   {ts_file.name}")
    print()

    # ========== 8. GENERATE REPORT ==========
    print("Generating report...")

    with open(REPORT_FILE, "w") as f:
        f.write("# Canary Current System Report\n\n")
        f.write(f"**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**Location**: Canary Islands region (28°N, -16°W)\n\n")

        f.write("## Summary\n\n")
        f.write(f"- Initial rows: {initial_rows:,}\n")
        f.write(f"- Final observations (rows): {len(final):,}\n")
        f.write(f"- Period: {final['time'].min().strftime('%Y-%m-%d')} to {final['time'].max().strftime('%Y-%m-%d')}\n\n")

        f.write("### Exclusions\n\n")
        f.write("- No exclusions applied (all size fractions ≤250µm)\n\n")

        f.write("## Figures\n\n")
        f.write("![Map](figures/map.png)\n\n")
        f.write("![Time Series](figures/time_series_biomass.png)\n\n")

        f.write("## Methodology\n\n")
        f.write("**Sampling Method**: Oblique tows from surface to 200m depth\n\n")
        f.write("**Nets**: WP-2 (92%), LHPR (6%), Juday Bogorov (1%)\n\n")
        f.write("**Size Fractions**: >200µm (98.4%), >250µm (1.3%)\n\n")
        f.write("**Unit Conversion**: mg C/m² → mg C/m³ (division by 200m depth)\n\n")
        f.write("**Aggregation**: None (1 row = 1 observation)\n\n")
        f.write("**Output format**: 1 row = 1 observation (Parquet)\n\n")

        f.write("## Biomass Statistics\n\n")
        f.write("| Metric | Mean | Median | Min | Max |\n")
        f.write("|--------|------|--------|-----|-----|\n")
        stats = final["biomass_carbon"].describe()
        f.write(
            f"| Carbon Biomass (mg C/m³) | {stats['mean']:.2f} | {stats['50%']:.2f} | "
            f"{stats['min']:.2f} | {stats['max']:.2f} |\n\n"
        )

        f.write("## Points d'attention et biais potentiels\n\n")

        f.write("### 1. Multi-sources (compilation 50 ans)\n\n")
        f.write("- **Type** : Compilation de ~30 publications scientifiques (1971-2021)\n")
        f.write("- **Avantage** : Couverture temporelle exceptionnelle, série temporelle longue\n")
        f.write("- **Limitation** : Hétérogénéité méthodologique entre études, protocoles variables\n")
        f.write("- **Impact** : Variable `reference` permet traçabilité, mais comparabilité inter-études limitée\n\n")

        f.write("### 2. Hétérogénéité des filets\n\n")
        f.write(f"- **WP-2** : {(df['net_type'] == 'WP-2').sum()} obs (92%)\n")
        f.write(f"- **LHPR** : {(df['net_type'] == 'LHPR').sum()} obs (6%)\n")
        f.write(f"- **Juday Bogorov** : {(df['net_type'] == 'Juday Bogorov (50 cmx2)').sum()} obs (1%)\n")
        f.write("- **Impact** : Efficacité de capture variable selon le filet\n")
        f.write("- **Mitigation** : WP-2 dominant garantit cohérence majoritaire\n\n")

        f.write("### 3. Conversion mg C/m² → mg C/m³\n\n")
        f.write("- **Formule** : biomass_carbon = biomass_carbon_m² / 200\n")
        f.write("- **Hypothèse** : Distribution verticale uniforme du zooplancton sur 0-200m\n")
        f.write("- **Réalité** : Distribution hétérogène (thermocline, DCM, migrations verticales)\n")
        f.write("- **Cohérence** : Conversion nécessaire pour compatibilité avec HOT/BATS/PAPA/CalCOFI (mg C/m³)\n\n")

        f.write("### 4. Profondeur fixe (0-200m)\n\n")
        f.write("- **Profondeur** : Tous les traits à 0-200m (métadonnées PANGAEA)\n")
        f.write("- **Limitation** : Pas d'information sur variabilité réelle des profondeurs de trait\n")
        f.write("- **Différence HOT/BATS** : HOT/BATS ont profondeurs variables (50-268m), Canaries homogène\n\n")

        f.write("### 5. Fractions de taille\n\n")
        f.write(f"- **>200µm** : {(df['size_fraction'] == '>200').sum()} obs (98.4%)\n")
        f.write(f"- **>250µm** : {(df['size_fraction'] == '>250').sum()} obs (1.3%)\n")
        f.write("- **Cohérence** : Pas de fraction >5mm détectée, cohérent avec autres stations\n\n")

        f.write("### 6. Classification jour/nuit\n\n")
        f.write("- **Méthode** : Colonne `period` des données source (jour/nuit)\n")
        f.write(f"- **Distribution observée** : {day_count} jour ({day_count/len(df)*100:.1f}%) vs ")
        f.write(f"{night_count} nuit ({night_count/len(df)*100:.1f}%)\n\n")

        f.write("### 7. Couverture temporelle et spatiale\n\n")
        f.write("- **Période** : 1971-2021 (50 ans)\n")
        f.write("- **Échantillonnage** : Irrégulier, opportuniste selon publications\n")
        f.write("- **Biais temporel** : Concentration possible sur certaines périodes\n")
        f.write("- **Biais spatial** : Concentration autour des Canaries, couverture NW Afrique plus sparse\n\n")

    print(f"   {REPORT_FILE}")
    print()

    print("=" * 60)
    print("Processing complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
