"""
CalCOFI Station Processing Script
Processes zooplankton data from CalCOFI NOAA Zooplankton Volume dataset
Converts displacement volumes to carbon biomass using Lavaniegos & Ohman (2007)
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
import xarray as xr
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
        # Create location from coordinates
        location = LocationInfo(
            latitude=row["latitude"],
            longitude=row["longitude"]
        )

        # Get sun times for this location and date (returns timezone-aware UTC times)
        s = sun(location.observer, date=row["time"].date())

        tow_time_utc = row["time"]
        sunrise_utc = s["sunrise"]
        sunset_utc = s["sunset"]

        # Handle case where sunset wraps to next day in UTC
        # (happens for locations west of UTC, e.g., California)
        if sunset_utc < sunrise_utc:
            # Sunset is on next day in UTC
            # Day is: tow_time >= sunrise OR tow_time <= sunset
            is_day = (tow_time_utc >= sunrise_utc) or (tow_time_utc <= sunset_utc)
        else:
            # Normal case: sunrise and sunset on same day
            is_day = sunrise_utc <= tow_time_utc <= sunset_utc

        return "day" if is_day else "night"
    except Exception:
        # Fallback: simple hour-based classification
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
    OUTPUT_NC = RELEASE_DIR / "calcofi_zooplankton_obs.nc"
    REPORT_FILE = REPORTS_DIR / "report.md"

    print("=" * 60)
    print("Processing CalCOFI Station (NOAA Zooplankton Volume)")
    print("=" * 60)
    print(f"Input:  {INPUT_FILE}")
    print(f"Output: {OUTPUT_NC}")
    print()

    if not INPUT_FILE.exists():
        print(f"❌ Error: Input file {INPUT_FILE} not found.")
        return

    # ========== 1. LOAD DATA ==========
    print("📂 Loading data...")
    df = pd.read_parquet(INPUT_FILE)
    print(f"   Loaded {len(df)} rows")
    print()

    # ========== 2. FILTER DATA ==========
    print("🔍 Filtering data...")
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
    print("⏰ Processing temporal data...")
    df["time"] = pd.to_datetime(df["time"], unit="s")

    # Classify day/night using astral (needs timezone-aware times)
    print("   Classifying day/night with astral...")
    df["day_night"] = df.apply(classify_day_night, axis=1)

    # Now remove timezone info for NetCDF compatibility
    if df["time"].dt.tz is not None:
        df["time"] = df["time"].dt.tz_localize(None)
    df["date"] = df["time"].dt.floor("D")

    day_count = (df["day_night"] == "day").sum()
    night_count = (df["day_night"] == "night").sum()
    print(f"   Day: {day_count} tows ({day_count/len(df)*100:.1f}%)")
    print(f"   Night: {night_count} tows ({night_count/len(df)*100:.1f}%)")
    print()

    # ========== 4. SPATIAL BINNING (1°) ==========
    print("🗺️  Binning spatial grid (1° resolution)...")
    df["lat_bin"] = df["latitude"].round(0)
    df["lon_bin"] = df["longitude"].round(0)
    print(f"   Latitude range: {df['lat_bin'].min():.0f}° to {df['lat_bin'].max():.0f}°")
    print(f"   Longitude range: {df['lon_bin'].min():.0f}° to {df['lon_bin'].max():.0f}°")
    print()

    # ========== 5. DEPTH ASSIGNMENT ==========
    print("📊 Assigning tow depth by protocol...")
    df["year"] = df["time"].dt.year
    df["tow_depth_max"] = np.where(df["year"] <= 1968, 140, 210)

    # All CalCOFI tows are epipelagic_only (<200m)
    df["depth_category"] = "epipelagic_only"

    depth_140 = (df["tow_depth_max"] == 140).sum()
    depth_210 = (df["tow_depth_max"] == 210).sum()
    print(f"   140m protocol (≤1968): {depth_140} tows")
    print(f"   210m protocol (>1968): {depth_210} tows")
    print()

    # ========== 6. LAVANIEGOS CONVERSION ==========
    print("🧮 Converting displacement volume to carbon biomass...")
    print("   Formula: log10(C) = 0.6664 × log10(DV) + 1.9997")

    df["biomass_carbon"] = lavaniegos_dv_to_carbon(
        df["small_plankton"],
        df["tow_depth_max"]
    )

    print(f"   Converted {len(df)} observations")
    print(f"   Biomass range: {df['biomass_carbon'].min():.2f} - {df['biomass_carbon'].max():.2f} mg C/m³")
    print()

    # ========== 7. IDENTIFY TOWS ==========
    print("🎣 Identifying tows...")
    df["tow_id"] = df.groupby(
        ["date", "lat_bin", "lon_bin", "tow_depth_max"]
    ).ngroup()
    n_tows = df["tow_id"].nunique()
    print(f"   Identified {n_tows} unique tows")
    print()

    # ========== 8. AGGREGATION LEVEL 1: Average per tow ==========
    print("🔢 Aggregating per tow...")
    agg1 = (
        df.groupby(
            ["date", "lat_bin", "lon_bin", "day_night", "depth_category", "tow_id"]
        )
        .agg({"biomass_carbon": "mean", "tow_depth_max": "first"})
        .reset_index()
    )
    print(f"   Aggregated {len(df)} rows → {len(agg1)} tows")
    print()

    # ========== 9. AGGREGATION LEVEL 2: Median per day/category/cell ==========
    print("📈 Aggregating tows per day/category/cell...")
    final = (
        agg1.groupby(["date", "lat_bin", "lon_bin", "day_night", "depth_category"])
        .agg({"biomass_carbon": "median", "tow_depth_max": "median"})
        .reset_index()
    )
    print(f"   Result: {len(final)} spatio-temporal observations")
    print()

    # ========== 10. CONVERT TO XARRAY ==========
    print("🗂️  Converting to xarray...")
    ds = xr.Dataset.from_dataframe(
        final.set_index(
            ["date", "lat_bin", "lon_bin", "depth_category", "day_night"]
        )
    )
    ds = ds.rename({"date": "time", "lat_bin": "lat", "lon_bin": "lon"})
    print()

    # ========== 11. ADD METADATA ==========
    print("📝 Adding metadata...")
    ds.attrs["title"] = "CalCOFI Zooplankton Observations"
    ds.attrs["source"] = "CalCOFI NOAA Zooplankton Volume"
    ds.attrs["institution"] = "NOAA SWFSC"
    ds.attrs["region"] = "California Current System"
    ds.attrs["conversion_method"] = "Lavaniegos & Ohman (2007)"
    ds.attrs["conversion_formula"] = "log10(C) = 0.6664 × log10(DV) + 1.9997"
    ds.attrs["depth_protocol"] = "140m (≤1968), 210m (>1968)"
    ds.attrs["spatial_resolution"] = "1 degree"
    ds.attrs["processing_date"] = datetime.now().isoformat()
    ds.attrs[
        "excluded_data"
    ] = "small_plankton NaN or ≤0"
    ds.attrs["conventions"] = "CF-1.8"

    ds["biomass_carbon"].attrs = {
        "units": "mg m-3",
        "long_name": "Carbon biomass concentration",
        "comment": "Converted from displacement volume using Lavaniegos & Ohman (2007)",
        "standard_name": "mole_concentration_of_organic_carbon_in_sea_water",
    }
    ds["tow_depth_max"].attrs = {
        "units": "m",
        "long_name": "Maximum tow depth",
        "comment": "140m for year ≤1968, 210m for year >1968"
    }

    ds["lat"].attrs = {
        "units": "degrees_north",
        "long_name": "Latitude (binned 1°)",
        "axis": "Y",
    }
    ds["lon"].attrs = {
        "units": "degrees_east",
        "long_name": "Longitude (binned 1°)",
        "axis": "X",
    }
    print()

    # ========== 12. SAVE NETCDF ==========
    print("💾 Saving NetCDF...")
    ds.to_netcdf(OUTPUT_NC, mode="w")
    print(f"   ✓ Saved to {OUTPUT_NC}")
    print()

    # ========== 13. GENERATE FIGURES ==========
    print("📊 Generating figures...")
    try:
        import matplotlib.pyplot as plt

        # Time series by depth category and day/night
        fig, axes = plt.subplots(1, 2, figsize=(14, 5))
        for j, dn in enumerate(["day", "night"]):
            ax = axes[j]
            subset = final[
                (final["depth_category"] == "epipelagic_only")
                & (final["day_night"] == dn)
            ]
            if not subset.empty:
                # Group by date and take mean over spatial cells
                ts = subset.groupby("date")["biomass_carbon"].mean()
                ax.plot(ts.index, ts.values, "o-", alpha=0.6, markersize=2)
                ax.set_title(f"epipelagic_only - {dn}")
                ax.set_ylabel("Carbon Biomass (mg C/m³)")
                ax.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(FIGURES_DIR / "time_series_biomass.png", dpi=150)
        plt.close()
        print("   ✓ time_series_biomass.png")
    except Exception as e:
        print(f"   ⚠ Error generating time series: {e}")

    try:
        # Spatial map of mean biomass with cartopy
        import cartopy.crs as ccrs
        import cartopy.feature as cfeature

        spatial_mean = final.groupby(["lat_bin", "lon_bin"])["biomass_carbon"].mean()

        fig = plt.figure(figsize=(12, 10))
        ax = plt.axes(projection=ccrs.PlateCarree())

        # Add geographic features
        ax.add_feature(cfeature.LAND, facecolor='lightgray', edgecolor='black', linewidth=0.5)
        ax.add_feature(cfeature.COASTLINE, linewidth=0.8)
        ax.add_feature(cfeature.BORDERS, linestyle=':', linewidth=0.5, alpha=0.5)

        # Plot data
        scatter = ax.scatter(
            spatial_mean.index.get_level_values(1),
            spatial_mean.index.get_level_values(0),
            c=spatial_mean.values,
            s=80,
            cmap="YlOrRd",
            alpha=0.8,
            edgecolors='black',
            linewidth=0.5,
            transform=ccrs.PlateCarree(),
            zorder=5
        )

        # Set extent (fixed for CalCOFI region)
        lat_min, lat_max = spatial_mean.index.get_level_values(0).min(), spatial_mean.index.get_level_values(0).max()
        margin = 3
        ax.set_extent([-180, -60,
                       lat_min - margin, lat_max + margin],
                      crs=ccrs.PlateCarree())

        # Gridlines
        gl = ax.gridlines(draw_labels=True, linewidth=0.5, alpha=0.5, linestyle='--')
        gl.top_labels = False
        gl.right_labels = False

        plt.colorbar(scatter, ax=ax, label="Mean Carbon Biomass (mg C/m³)", shrink=0.7)
        ax.set_title("CalCOFI Spatial Distribution (mean carbon biomass)",
                     fontsize=14, fontweight='bold')

        plt.tight_layout()
        plt.savefig(FIGURES_DIR / "map.png", dpi=150, bbox_inches='tight')
        plt.close()
        print("   ✓ map.png")
    except Exception as e:
        print(f"   ⚠ Error generating map: {e}")
    print()

    # ========== 14. GENERATE REPORT ==========
    print("📄 Generating report...")
    with open(REPORT_FILE, "w") as f:
        f.write("# CalCOFI Station Report\n\n")
        f.write(f"**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(
            f"**Region**: California Current System ({df['latitude'].min():.1f}-{df['latitude'].max():.1f}°N, "
            f"{df['longitude'].min():.1f}-{df['longitude'].max():.1f}°E)\n\n"
        )

        f.write("## Summary\n\n")
        f.write(f"- Initial rows: {initial_rows:,}\n")
        f.write(f"- Final observations: {len(final):,}\n")
        f.write(f"- Unique tows: {n_tows:,}\n")
        f.write(f"- Period: {df['time'].min().date()} to {df['time'].max().date()}\n")
        f.write(f"- Spatial cells (1°): {final[['lat_bin', 'lon_bin']].drop_duplicates().shape[0]}\n\n")

        f.write("### Exclusions\n\n")
        f.write(f"- small_plankton NaN: {len(excluded_nan)} rows\n")
        f.write(f"- small_plankton ≤ 0: {len(excluded_zero)} rows\n\n")

        f.write("### Depth Protocol\n\n")
        f.write(f"- 140m protocol (≤1968): {depth_140} tows\n")
        f.write(f"- 210m protocol (>1968): {depth_210} tows\n")
        f.write("- All tows: epipelagic_only (<200m)\n\n")

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
        f.write("**Spatial Resolution**: 1° grid\n\n")
        f.write("**Aggregation**:\n")
        f.write("1. Average biomass per tow\n")
        f.write("2. Median of tows per day/depth_category/spatial_cell\n\n")

        f.write("## Points d'attention et biais potentiels\n\n")

        f.write("### 1. Changement de protocole de profondeur (1969)\n\n")
        f.write("- **Avant 1969** : Profondeur standard 140m\n")
        f.write("- **Après 1968** : Profondeur standard 210m\n")
        f.write("- **Impact** : Différence de volume échantillonné et de couverture verticale. ")
        f.write("Les traits post-1968 intègrent une partie de la zone mésopélagique (150-210m), ")
        f.write("potentiellement incluant des organismes non capturés avant 1969.\n")
        f.write("- **Mitigation** : Conversion en concentration volumique (mg/m³) normalise partiellement ")
        f.write("l'effet, mais la composition taxonomique peut différer.\n\n")

        f.write("### 2. Conversion non-linéaire Lavaniegos & Ohman (2007)\n\n")
        f.write("- **Formule empirique** : Basée sur des échantillons CalCOFI (1951-2005)\n")
        f.write("- **Relation log-log** : Amplification des incertitudes pour les faibles et fortes valeurs\n")
        f.write("- **Limites de validité** : Formule calibrée sur le système California Current, ")
        f.write("extrapolation à d'autres régions non validée\n")
        f.write("- **Incertitude** : Pas d'intervalle de confiance publié pour la formule\n\n")

        f.write("### 3. Restriction aux petits organismes (small_plankton)\n\n")
        f.write("- **Seuil** : Organismes avec volume individuel <5ml\n")
        f.write("- **Exclus** : Grands organismes gélatineux (méduses, salpes), euphausiacés adultes, ")
        f.write("larves de poissons de grande taille\n")
        f.write("- **Justification** : Cohérence avec HOT/BATS (fraction <5mm), capture hétérogène ")
        f.write("des grands organismes par les filets standards\n")
        f.write("- **Impact** : Sous-estimation de la biomasse totale, mais meilleure cohérence ")
        f.write("inter-stations\n\n")

        f.write("### 4. Agrégation spatiale (1° × 1°)\n\n")
        f.write("- **Résolution** : Grille 1° (~111km à l'équateur)\n")
        f.write("- **Justification** : Couverture spatiale large (0-54°N, -180 à -78°W), ")
        f.write("hétérogénéité des stations\n")
        f.write("- **Impact** : Lissage des variations locales, perte de résolution côtière\n")
        f.write("- **Cellules** : 965 cellules uniques sur la période 1951-2023\n\n")

        f.write("### 5. Classification jour/nuit\n\n")
        f.write("- **Méthode** : Calcul astronomique (lever/coucher soleil) via bibliothèque `astral`\n")
        f.write("- **Avantage** : Précision basée sur position géographique et date réelles\n")
        f.write("- **Attention** : Gestion des timezones (UTC vs local) et wrap-around jour suivant\n")
        f.write(f"- **Distribution observée** : {day_count} jour ({day_count/len(df)*100:.1f}%) vs ")
        f.write(f"{night_count} nuit ({night_count/len(df)*100:.1f}%)\n\n")

        f.write("### 6. Absence d'exclusions par profondeur/maille\n\n")
        f.write("- **Aucune exclusion** : Contrairement à HOT/BATS (traits <50m exclus), ")
        f.write("tous les traits CalCOFI sont conservés\n")
        f.write("- **Raison** : Protocole standardisé CalCOFI (140m/210m), pas de traits aberrants détectés\n")
        f.write("- **Maille** : Variable selon période (majoritairement 202-333µm)\n\n")

        f.write("### 7. Couverture temporelle et spatiale\n\n")
        f.write("- **Période** : 1951-2023 (72 ans)\n")
        f.write("- **Échantillonnage** : Irrégulier dans le temps et l'espace (campagnes opportunistes)\n")
        f.write("- **Biais géographique** : Concentration des observations près des côtes californiennes\n")
        f.write("- **Biais saisonnier** : À vérifier (campagnes potentiellement concentrées sur certaines saisons)\n\n")

    print(f"   ✓ {REPORT_FILE}")
    print()

    print("=" * 60)
    print("✅ Processing complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
