"""
CalCOFI Station Processing Script
Processes zooplankton data from CalCOFI NOAA Zooplankton Volume dataset
Converts displacement volumes to carbon biomass using Lavaniegos & Ohman (2007)
Output: 1 row = 1 tow (flat Parquet)
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime
from astral import LocationInfo
from astral.sun import sun

# Add src to python path to allow importing core
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.append(str(PROJECT_ROOT / "src"))


def lavaniegos_dv_to_carbon(dv_ml_per_1000m3, depth):
    """
    Convert displacement volume to carbon biomass using Lavaniegos & Ohman (2007).

    Formula: log10(C) = 0.6664 × log10(DV) + 1.9997
    where C = Carbon (mg C/m²), DV = Displacement Volume (ml/m²)

    Parameters
    ----------
    dv_ml_per_1000m3 : array-like
        Displacement volume in ml/1000m³
    depth : array-like or scalar
        Tow depth in meters

    Returns
    -------
    array-like
        Carbon biomass in mg C/m³
    """
    # Step 1: Convert ml/1000m³ → ml/m²
    dv_ml_per_m2 = dv_ml_per_1000m3 * depth / 1000

    # Step 2: Apply Lavaniegos formula (log-log)
    log_c = 0.6664 * np.log10(dv_ml_per_m2) + 1.9997
    c_mg_per_m2 = 10 ** log_c

    # Step 3: Convert mg/m² → mg/m³
    biomass_carbon = c_mg_per_m2 / depth

    return biomass_carbon


def classify_day_night(row):
    """
    Classify tow as day or night based on solar position.
    Uses astral library to compute sunrise/sunset for given location and date.

    Parameters
    ----------
    row : pd.Series
        Row with 'time', 'latitude', 'longitude' columns (time must be timezone-aware UTC)

    Returns
    -------
    str
        "day" or "night"
    """
    try:
        location = LocationInfo(
            latitude=row["latitude"],
            longitude=row["longitude"]
        )

        s = sun(location.observer, date=row["time"].date())

        tow_time_utc = row["time"]
        sunrise_utc = s["sunrise"]
        sunset_utc = s["sunset"]

        if sunset_utc < sunrise_utc:
            is_day = (tow_time_utc >= sunrise_utc) or (tow_time_utc <= sunset_utc)
        else:
            is_day = sunrise_utc <= tow_time_utc <= sunset_utc

        return "day" if is_day else "night"
    except Exception:
        hour = row["time"].hour
        return "day" if 6 <= hour < 18 else "night"


def main():
    # ========== PATHS ==========
    STATION_DIR = PROJECT_ROOT / "src" / "calcofi"
    RAW_DIR = STATION_DIR / "data" / "raw"
    RELEASE_DIR = STATION_DIR / "release"
    REPORTS_DIR = STATION_DIR / "reports"
    FIGURES_DIR = REPORTS_DIR / "figures"

    # Create directories
    RELEASE_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    # Files
    INPUT_FILE = RAW_DIR / "zooplankton.parquet"
    OUTPUT_PARQUET = RELEASE_DIR / "calcofi_zooplankton_obs.parquet"
    REPORT_FILE = REPORTS_DIR / "report.md"

    print("=" * 60)
    print("Processing CalCOFI Station (NOAA Zooplankton Volume)")
    print("=" * 60)
    print(f"Input:  {INPUT_FILE}")
    print(f"Output: {OUTPUT_PARQUET}")
    print()

    if not INPUT_FILE.exists():
        print(f"Error: Input file {INPUT_FILE} not found.")
        return

    # ========== 1. LOAD DATA ==========
    print("Loading data...")
    df = pd.read_parquet(INPUT_FILE)
    print(f"   Loaded {len(df)} rows")
    print()

    # ========== 2. FILTER DATA ==========
    print("Filtering data...")
    initial_rows = len(df)

    # Filter 1: Exclude rows with missing small_plankton
    excluded_nan = df[df["small_plankton"].isna()]
    print(f"   Excluding {len(excluded_nan)} rows with small_plankton = NaN")
    df = df[df["small_plankton"].notna()]

    # Filter 2: Exclude rows with small_plankton <= 0
    excluded_zero = df[df["small_plankton"] <= 0]
    print(f"   Excluding {len(excluded_zero)} rows with small_plankton ≤ 0")
    df = df[df["small_plankton"] > 0]

    print(f"   Result: {len(df)} rows")
    print()

    # ========== 3. TEMPORAL PROCESSING ==========
    print("Processing temporal data...")
    df["time"] = pd.to_datetime(df["time"], unit="s")

    # Classify day/night using astral (needs timezone-aware times)
    print("   Classifying day/night with astral...")
    df["day_night"] = df.apply(classify_day_night, axis=1)

    # Remove timezone info if present
    if df["time"].dt.tz is not None:
        df["time"] = df["time"].dt.tz_localize(None)

    day_count = (df["day_night"] == "day").sum()
    night_count = (df["day_night"] == "night").sum()
    print(f"   Day: {day_count} tows ({day_count/len(df)*100:.1f}%)")
    print(f"   Night: {night_count} tows ({night_count/len(df)*100:.1f}%)")
    print()

    # ========== 4. DEPTH ASSIGNMENT ==========
    print("Assigning tow depth by protocol...")
    df["year"] = df["time"].dt.year
    df["tow_depth_max"] = np.where(df["year"] <= 1968, 140, 210)

    depth_140 = (df["tow_depth_max"] == 140).sum()
    depth_210 = (df["tow_depth_max"] == 210).sum()
    print(f"   140m protocol (≤1968): {depth_140} tows")
    print(f"   210m protocol (>1968): {depth_210} tows")
    print()

    # ========== 5. LAVANIEGOS CONVERSION ==========
    print("Converting displacement volume to carbon biomass...")
    print("   Formula: log10(C) = 0.6664 × log10(DV) + 1.9997")

    df["biomass_carbon"] = lavaniegos_dv_to_carbon(
        df["small_plankton"],
        df["tow_depth_max"]
    )

    print(f"   Converted {len(df)} observations")
    print(f"   Biomass range: {df['biomass_carbon'].min():.2f} - {df['biomass_carbon'].max():.2f} mg C/m³")
    print()

    # ========== 6. BUILD FINAL DATAFRAME ==========
    print("Preparing final DataFrame...")

    final = df[["time", "day_night", "biomass_carbon", "tow_depth_max",
                 "latitude", "longitude"]].copy()
    final = final.rename(columns={"latitude": "lat", "longitude": "lon"})

    # Save Parquet
    print(f"\nSaving Parquet ({len(final)} tows)...")
    final.to_parquet(OUTPUT_PARQUET, index=False)
    print(f"   Saved to {OUTPUT_PARQUET}")
    print(f"   Columns: {final.columns.tolist()}")
    print()

    # ========== 7. GENERATE FIGURES ==========
    print("Generating figures...")
    try:
        import matplotlib.pyplot as plt

        fig, axes = plt.subplots(1, 2, figsize=(14, 5))
        for j, dn in enumerate(["day", "night"]):
            ax = axes[j]
            subset = final[final["day_night"] == dn]
            if not subset.empty:
                ax.plot(subset["time"], subset["biomass_carbon"], "o", alpha=0.2, markersize=1)
                ax.set_title(f"{dn}")
                ax.set_ylabel("Carbon Biomass (mg C/m³)")
                ax.grid(True, alpha=0.3)
        plt.suptitle("CalCOFI Zooplankton Biomass (1 tow = 1 point)")
        plt.tight_layout()
        plt.savefig(FIGURES_DIR / "time_series_biomass.png", dpi=150)
        plt.close()
        print("   time_series_biomass.png")
    except Exception as e:
        print(f"   Error generating time series: {e}")

    try:
        import cartopy.crs as ccrs
        import cartopy.feature as cfeature

        fig = plt.figure(figsize=(12, 10))
        ax = plt.axes(projection=ccrs.PlateCarree())

        ax.add_feature(cfeature.LAND, facecolor='lightgray', edgecolor='black', linewidth=0.5)
        ax.add_feature(cfeature.COASTLINE, linewidth=0.8)
        ax.add_feature(cfeature.BORDERS, linestyle=':', linewidth=0.5, alpha=0.5)

        scatter = ax.scatter(
            final["lon"],
            final["lat"],
            c=final["biomass_carbon"],
            s=10,
            cmap="YlOrRd",
            alpha=0.4,
            transform=ccrs.PlateCarree(),
            zorder=5
        )

        lat_min, lat_max = final["lat"].min(), final["lat"].max()
        lon_min, lon_max = final["lon"].min(), final["lon"].max()
        margin = 3
        ax.set_extent([lon_min - margin, lon_max + margin,
                       lat_min - margin, lat_max + margin],
                      crs=ccrs.PlateCarree())

        gl = ax.gridlines(draw_labels=True, linewidth=0.5, alpha=0.5, linestyle='--')
        gl.top_labels = False
        gl.right_labels = False

        plt.colorbar(scatter, ax=ax, label="Carbon Biomass (mg C/m³)", shrink=0.7)
        ax.set_title("CalCOFI Spatial Distribution", fontsize=14, fontweight='bold')

        plt.tight_layout()
        plt.savefig(FIGURES_DIR / "map.png", dpi=150, bbox_inches='tight')
        plt.close()
        print("   map.png")
    except Exception as e:
        print(f"   Error generating map: {e}")
    print()

    # ========== 8. GENERATE REPORT ==========
    print("Generating report...")
    with open(REPORT_FILE, "w") as f:
        f.write("# CalCOFI Station Report\n\n")
        f.write(f"**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(
            f"**Region**: California Current System ({df['latitude'].min():.1f}-{df['latitude'].max():.1f}°N, "
            f"{df['longitude'].min():.1f}-{df['longitude'].max():.1f}°E)\n\n"
        )

        f.write("## Summary\n\n")
        f.write(f"- Initial rows: {initial_rows:,}\n")
        f.write(f"- Final tows (rows): {len(final):,}\n")
        f.write(f"- Period: {df['time'].min().date()} to {df['time'].max().date()}\n\n")

        f.write("### Exclusions\n\n")
        f.write(f"- small_plankton NaN: {len(excluded_nan)} rows\n")
        f.write(f"- small_plankton ≤ 0: {len(excluded_zero)} rows\n\n")

        f.write("### Depth Protocol\n\n")
        f.write(f"- 140m protocol (≤1968): {depth_140} tows\n")
        f.write(f"- 210m protocol (>1968): {depth_210} tows\n\n")

        f.write("### Biomass Statistics\n\n")
        f.write("| Metric | Mean | Median | Min | Max |\n")
        f.write("|--------|------|--------|-----|-----|\n")
        stats = final["biomass_carbon"].describe()
        f.write(
            f"| Carbon Biomass (mg C/m³) | {stats['mean']:.2f} | {stats['50%']:.2f} | "
            f"{stats['min']:.2f} | {stats['max']:.2f} |\n\n"
        )

        f.write("## Figures\n\n")
        f.write("![Map](figures/map.png)\n\n")
        f.write("![Time Series](figures/time_series_biomass.png)\n\n")

        f.write("## Methodology\n\n")
        f.write("**Conversion Method**: Lavaniegos & Ohman (2007)\n\n")
        f.write("**Formula**: `log10(C) = 0.6664 × log10(DV) + 1.9997`\n\n")
        f.write("where C = Carbon biomass (mg C/m²), DV = Displacement Volume (ml/m²)\n\n")
        f.write("**Source Variable**: small_plankton (organisms with individual DV <5ml)\n\n")
        f.write("**Aggregation**: None (1 row = 1 tow, Parquet)\n\n")

        f.write("## Points d'attention et biais potentiels\n\n")

        f.write("### 1. Changement de protocole de profondeur (1969)\n\n")
        f.write("- **Avant 1969** : Profondeur standard 140m\n")
        f.write("- **Après 1968** : Profondeur standard 210m\n")
        f.write("- **Impact** : Différence de volume échantillonné et de couverture verticale. ")
        f.write("Les traits post-1968 intègrent une partie de la zone mésopélagique (150-210m).\n")
        f.write("- **Mitigation** : Conversion en concentration volumique (mg/m³) normalise partiellement l'effet.\n\n")

        f.write("### 2. Conversion non-linéaire Lavaniegos & Ohman (2007)\n\n")
        f.write("- **Formule empirique** : Basée sur des échantillons CalCOFI (1951-2005)\n")
        f.write("- **Relation log-log** : Amplification des incertitudes pour les faibles et fortes valeurs\n")
        f.write("- **Limites de validité** : Formule calibrée sur le système California Current\n\n")

        f.write("### 3. Restriction aux petits organismes (small_plankton)\n\n")
        f.write("- **Seuil** : Organismes avec volume individuel <5ml\n")
        f.write("- **Exclus** : Grands organismes gélatineux, euphausiacés adultes\n")
        f.write("- **Justification** : Cohérence avec HOT/BATS (fraction <5mm)\n\n")

        f.write("### 4. Classification jour/nuit\n\n")
        f.write("- **Méthode** : Calcul astronomique (lever/coucher soleil) via bibliothèque `astral`\n")
        f.write("- **Avantage** : Précision basée sur position géographique et date réelles\n")
        f.write(f"- **Distribution observée** : {day_count} jour ({day_count/len(df)*100:.1f}%) vs ")
        f.write(f"{night_count} nuit ({night_count/len(df)*100:.1f}%)\n\n")

        f.write("### 5. Couverture temporelle et spatiale\n\n")
        f.write("- **Période** : 1951-2023 (72 ans)\n")
        f.write("- **Échantillonnage** : Irrégulier dans le temps et l'espace\n")
        f.write("- **Biais géographique** : Concentration des observations près des côtes californiennes\n\n")

    print(f"   {REPORT_FILE}")
    print()

    print("=" * 60)
    print("Processing complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
