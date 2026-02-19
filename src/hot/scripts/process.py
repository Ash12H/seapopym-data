"""
HOT Station Processing Script
Processes zooplankton data from Hawaii Ocean Time-series (HOT)
Following the validated workflow from ANALYSIS_HOT.md
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
    STATION_DIR = PROJECT_ROOT / "src" / "hot"
    RAW_DIR = STATION_DIR / "data" / "raw"
    RELEASE_DIR = STATION_DIR / "release"
    REPORTS_DIR = STATION_DIR / "reports"
    FIGURES_DIR = REPORTS_DIR / "figures"

    # Create directories
    RELEASE_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    # Files
    INPUT_FILE = RAW_DIR / "hot_zooplankton.csv"
    OUTPUT_NC = RELEASE_DIR / "hot_zooplankton_obs.nc"
    REPORT_FILE = REPORTS_DIR / "report.md"

    print("=" * 60)
    print("Processing HOT Station (Hawaii Ocean Time-series)")
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
    print(f"   Columns: {df.columns.tolist()}")
    print()

    # ========== 2. FILTER DATA ==========
    print("🔍 Filtering data...")
    initial_rows = len(df)
    initial_tows = df["tow"].nunique()

    # Filter 1: Exclude depth < 50m (aberrant tows)
    excluded_shallow = df[df["depth"] < 50]
    print(f"   Excluding {len(excluded_shallow)} rows with depth < 50m")
    print(f"   Affected tows: {excluded_shallow['tow'].unique()}")
    for tow in excluded_shallow["tow"].unique():
        tow_data = excluded_shallow[excluded_shallow["tow"] == tow].iloc[0]
        print(
            f"      Tow {tow}: {tow_data['time']} | depth={tow_data['depth']}m | vol={tow_data['vol']}m³"
        )
    df = df[df["depth"] >= 50]

    # Filter 2: Exclude fraction 5 (micronekton, poorly sampled)
    excluded_frac5 = df[df["frac"] == 5]
    print(f"   Excluding {len(excluded_frac5)} rows with frac=5 (micronekton)")
    df = df[df["frac"] <= 4]

    print(
        f"   Result: {len(df)} rows from {df['tow'].nunique()} tows ({initial_tows - df['tow'].nunique()} tows excluded)"
    )
    print()

    # ========== 3. TEMPORAL PROCESSING ==========
    print("⏰ Processing temporal data...")
    df["time"] = pd.to_datetime(df["time"])
    df["date"] = df["time"].dt.floor("D")
    df["hour"] = df["time"].dt.hour

    # Day/Night classification (6h-18h = day, 18h-6h = night)
    df["day_night"] = df["hour"].apply(lambda h: "day" if 6 <= h < 18 else "night")

    print(f"   Time range: {df['time'].min()} to {df['time'].max()}")
    print(f"   Day samples: {(df['day_night'] == 'day').sum()}")
    print(f"   Night samples: {(df['day_night'] == 'night').sum()}")
    print()

    # ========== 4. UNIT CONVERSION (m² → m³) ==========
    print("🔄 Converting units (m² → m³)...")

    # Variables to convert (from area density to concentration)
    # dwt: g/m² → g/m³
    # carb, nit: mg/m² → mg/m³
    df["dwt_m3"] = df["dwt"] / df["depth"]  # g/m³
    df["carb_m3"] = df["carb"] / df["depth"]  # mg/m³
    df["nit_m3"] = df["nit"] / df["depth"]  # mg/m³

    print("   Converted dwt (g/m² → g/m³)")
    print("   Converted carb (mg/m² → mg/m³)")
    print("   Converted nit (mg/m² → mg/m³)")
    print()

    # ========== 5. DEPTH CATEGORIZATION ==========
    print("📊 Categorizing by depth...")

    df["depth_category"] = np.where(
        df["depth"] <= 150, "epipelagic_only", "epipelagic_mesopelagic"
    )

    epi_only = (df["depth_category"] == "epipelagic_only").sum()
    epi_meso = (df["depth_category"] == "epipelagic_mesopelagic").sum()

    print(f"   epipelagic_only (≤150m): {epi_only} rows ({100*epi_only/len(df):.1f}%)")
    print(
        f"   epipelagic_mesopelagic (>150m): {epi_meso} rows ({100*epi_meso/len(df):.1f}%)"
    )
    print()

    # ========== 6. STORE TOW METADATA ==========
    print("💾 Storing tow metadata...")
    df["tow_depth_max"] = df.groupby("tow")["depth"].transform("first")
    print()

    # ========== 7. AGGREGATION LEVEL 1: Sum fractions per tow ==========
    print("🔢 Aggregating fractions per tow...")

    agg1 = (
        df.groupby(["date", "day_night", "depth_category", "tow"])
        .agg(
            {
                "dwt_m3": "sum",  # Sum fractions 0-4
                "carb_m3": "sum",
                "nit_m3": "sum",
                "tow_depth_max": "first",
                "lat": "first",
                "lon": "first",
            }
        )
        .reset_index()
    )

    print(f"   Aggregated {len(df)} rows → {len(agg1)} tows")
    print()

    # ========== 8. AGGREGATION LEVEL 2: Median of tows per day/category ==========
    print("📈 Aggregating tows per day/category (median)...")

    final = (
        agg1.groupby(["date", "day_night", "depth_category"])
        .agg(
            {
                "dwt_m3": "median",
                "carb_m3": "median",
                "nit_m3": "median",
                "tow_depth_max": "median",
                "lat": "first",
                "lon": "first",
            }
        )
        .reset_index()
    )

    print(f"   Aggregated {len(agg1)} tows → {len(final)} daily observations")
    print()

    # ========== 9. CONVERT TO XARRAY ==========
    print("🗂️  Converting to xarray Dataset...")

    ds = xr.Dataset.from_dataframe(
        final.set_index(["date", "depth_category", "day_night"])
    )

    # Rename and convert units
    ds = ds.rename(
        {
            "date": "time",
            "dwt_m3": "biomass_dry",
            "carb_m3": "biomass_carbon",
            "nit_m3": "biomass_nitrogen",
        }
    )

    # Convert biomass_dry: g/m³ → mg/m³
    ds["biomass_dry"] = ds["biomass_dry"] * 1000

    print()

    # ========== 10. ADD METADATA ==========
    print("📝 Adding metadata...")

    # Global attributes
    ds.attrs["title"] = "HOT Zooplankton Observations"
    ds.attrs["station"] = "HOT"
    ds.attrs["station_name"] = "Hawaii Ocean Time-series, Station ALOHA"
    ds.attrs["location"] = "22.75°N, -158°W"
    ds.attrs["institution"] = "University of Hawaii at Manoa"
    ds.attrs["source"] = "Hawaii Ocean Time-series Data Organization & Graphical System (HOT-DOGS)"
    ds.attrs["sampling_method"] = "Oblique tows from surface to max depth and back"
    ds.attrs["net_type"] = "1 m² net with 202 µm mesh (Nitex)"
    ds.attrs["size_range"] = "0.2-5 mm (mesozooplankton, fractions 0-4)"
    ds.attrs["history"] = f"Created on {datetime.now().isoformat()} using seapopym-data pipeline"
    ds.attrs["processing_date"] = datetime.now().isoformat()
    ds.attrs["data_period"] = f"{df['time'].min().date()} to {df['time'].max().date()}"
    ds.attrs["excluded_data"] = "Tows with depth <50m (2 tows), Fraction 5 (>5mm micronekton)"
    ds.attrs["references"] = "https://hahana.soest.hawaii.edu/hot/hot-dogs/"
    ds.attrs["conventions"] = "CF-1.8"

    # Variable attributes
    ds["biomass_dry"].attrs = {
        "long_name": "Zooplankton dry weight biomass concentration",
        "units": "mg m-3",
        "standard_name": "zooplankton_dry_weight_concentration",
        "description": "Sum of size fractions 0-4 (0.2-5mm), mean concentration over sampled water column",
    }

    ds["biomass_carbon"].attrs = {
        "long_name": "Zooplankton carbon biomass concentration",
        "units": "mg m-3",
        "standard_name": "zooplankton_carbon_concentration",
        "description": "Sum of size fractions 0-4 (0.2-5mm), mean concentration over sampled water column",
    }

    ds["biomass_nitrogen"].attrs = {
        "long_name": "Zooplankton nitrogen biomass concentration",
        "units": "mg m-3",
        "standard_name": "zooplankton_nitrogen_concentration",
        "description": "Sum of size fractions 0-4 (0.2-5mm), mean concentration over sampled water column",
    }

    ds["tow_depth_max"].attrs = {
        "long_name": "Maximum tow depth",
        "units": "m",
        "standard_name": "depth",
        "description": "Maximum depth reached during oblique tow (median of tows in this category/day)",
    }

    # Coordinate attributes
    ds["time"].attrs = {
        "long_name": "Time",
        "standard_name": "time",
        "axis": "T",
    }

    ds["depth_category"].attrs = {
        "long_name": "Depth category",
        "description": "Categorization based on maximum tow depth",
        "epipelagic_only": "Tows 0-150m, samples ONLY epipelagic zone (0-150m)",
        "epipelagic_mesopelagic": "Tows >150m, samples BOTH epipelagic (0-150m) AND mesopelagic (150-depth_max) zones",
    }

    ds["day_night"].attrs = {
        "long_name": "Day or night",
        "description": "Day (06:00-18:00 local time) or night (18:00-06:00 local time)",
        "flag_values": "day, night",
    }

    ds["lat"].attrs = {
        "long_name": "Latitude",
        "units": "degrees_north",
        "standard_name": "latitude",
        "axis": "Y",
    }

    ds["lon"].attrs = {
        "long_name": "Longitude",
        "units": "degrees_east",
        "standard_name": "longitude",
        "axis": "X",
    }

    print()

    # ========== 11. SAVE NETCDF ==========
    print("💾 Saving NetCDF...")
    ds.to_netcdf(OUTPUT_NC, mode="w")
    print(f"   ✓ Saved to {OUTPUT_NC}")
    print()

    # ========== 12. GENERATE FIGURES ==========
    print("📊 Generating figures...")

    # Convert back to dataframe for plotting
    plot_df = final.copy()
    plot_df["biomass_dry_mg_m3"] = plot_df["dwt_m3"] * 1000

    # Time series by depth category and day/night
    try:
        import matplotlib.pyplot as plt

        fig, axes = plt.subplots(2, 2, figsize=(14, 10))

        for i, depth_cat in enumerate(["epipelagic_only", "epipelagic_mesopelagic"]):
            for j, dn in enumerate(["day", "night"]):
                ax = axes[i, j]
                subset = plot_df[
                    (plot_df["depth_category"] == depth_cat)
                    & (plot_df["day_night"] == dn)
                ]
                if not subset.empty:
                    ax.plot(subset["date"], subset["biomass_dry_mg_m3"], "o-", alpha=0.6)
                    ax.set_title(f"{depth_cat} - {dn}")
                    ax.set_ylabel("Biomass (mg/m³)")
                    ax.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig(FIGURES_DIR / "time_series_biomass.png", dpi=150)
        plt.close()
        print("   ✓ time_series_biomass.png")
    except Exception as e:
        print(f"   ⚠ Could not generate time series plot: {e}")

    # Map
    try:
        fig, ax = plt.subplots(figsize=(8, 6))
        ax.scatter(final["lon"].iloc[0], final["lat"].iloc[0], s=200, c="red", marker="*", edgecolors="black", linewidths=2, zorder=5)
        ax.set_xlabel("Longitude")
        ax.set_ylabel("Latitude")
        ax.set_title("Station ALOHA Location")
        ax.grid(True, alpha=0.3)
        ax.set_xlim(final["lon"].iloc[0] - 5, final["lon"].iloc[0] + 5)
        ax.set_ylim(final["lat"].iloc[0] - 5, final["lat"].iloc[0] + 5)
        plt.savefig(FIGURES_DIR / "map.png", dpi=150)
        plt.close()
        print("   ✓ map.png")
    except Exception as e:
        print(f"   ⚠ Could not generate map: {e}")

    print()

    # ========== 13. GENERATE REPORT ==========
    print("📄 Generating report...")

    with open(REPORT_FILE, "w") as f:
        f.write("# HOT Station Processing Report\n\n")
        f.write(f"**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**Station**: Hawaii Ocean Time-series (HOT), Station ALOHA\n")
        f.write(f"**Location**: 22.75°N, -158°W\n\n")

        f.write("---\n\n")

        f.write("## Data Processing Summary\n\n")
        f.write(f"- **Input file**: `{INPUT_FILE.name}`\n")
        f.write(f"- **Output file**: `{OUTPUT_NC.name}`\n")
        f.write(f"- **Initial rows**: {initial_rows:,}\n")
        f.write(f"- **Initial tows**: {initial_tows:,}\n")
        f.write(f"- **Final rows**: {len(final):,}\n")
        f.write(f"- **Time period**: {df['time'].min().date()} to {df['time'].max().date()}\n\n")

        f.write("### Exclusions Applied\n\n")
        f.write(f"1. **Shallow tows** (depth <50m): {len(excluded_shallow['tow'].unique())} tows excluded\n")
        for tow in excluded_shallow["tow"].unique():
            tow_data = excluded_shallow[excluded_shallow["tow"] == tow].iloc[0]
            f.write(f"   - Tow {tow}: {tow_data['time']} | depth={tow_data['depth']}m\n")
        f.write(f"\n2. **Fraction 5** (>5mm micronekton): {len(excluded_frac5):,} rows excluded\n\n")

        f.write("### Depth Categories\n\n")
        epi_tows = final[final["depth_category"] == "epipelagic_only"]
        meso_tows = final[final["depth_category"] == "epipelagic_mesopelagic"]

        f.write(f"- **epipelagic_only** (≤150m): {len(epi_tows)} observations\n")
        f.write(f"  - Samples ONLY epipelagic zone (0-150m)\n")
        f.write(f"  - Mean tow depth: {epi_tows['tow_depth_max'].mean():.1f}m\n\n")

        f.write(f"- **epipelagic_mesopelagic** (>150m): {len(meso_tows)} observations\n")
        f.write(f"  - Samples BOTH epipelagic (0-150m) AND mesopelagic (>150m) zones\n")
        f.write(f"  - Mean tow depth: {meso_tows['tow_depth_max'].mean():.1f}m\n\n")

        f.write("### Biomass Statistics\n\n")
        f.write(f"| Metric | Mean | Median | Min | Max |\n")
        f.write(f"|--------|------|--------|-----|-----|\n")
        f.write(
            f"| Dry Weight (mg/m³) | {plot_df['biomass_dry_mg_m3'].mean():.2f} | "
            f"{plot_df['biomass_dry_mg_m3'].median():.2f} | "
            f"{plot_df['biomass_dry_mg_m3'].min():.2f} | "
            f"{plot_df['biomass_dry_mg_m3'].max():.2f} |\n"
        )
        f.write(
            f"| Carbon (mg/m³) | {plot_df['carb_m3'].mean():.2f} | "
            f"{plot_df['carb_m3'].median():.2f} | "
            f"{plot_df['carb_m3'].min():.2f} | "
            f"{plot_df['carb_m3'].max():.2f} |\n"
        )
        f.write(
            f"| Nitrogen (mg/m³) | {plot_df['nit_m3'].mean():.2f} | "
            f"{plot_df['nit_m3'].median():.2f} | "
            f"{plot_df['nit_m3'].min():.2f} | "
            f"{plot_df['nit_m3'].max():.2f} |\n"
        )
        f.write("\n")

        f.write("---\n\n")
        f.write("## Figures\n\n")

        f.write("### Station Location\n\n")
        if (FIGURES_DIR / "map.png").exists():
            f.write("![Station Map](figures/map.png)\n\n")
        else:
            f.write("*Map not available*\n\n")

        f.write("### Time Series of Biomass\n\n")
        if (FIGURES_DIR / "time_series_biomass.png").exists():
            f.write("![Time Series](figures/time_series_biomass.png)\n\n")
        else:
            f.write("*Time series plot not available*\n\n")

        f.write("---\n\n")
        f.write("## Methodology\n\n")
        f.write("**Sampling Method**: Oblique tows from surface to maximum depth and back\n\n")
        f.write("**Net**: 1 m² with 202 µm mesh (Nitex)\n\n")
        f.write("**Size Fractions**: 0 (200µm), 1 (500µm), 2 (1mm), 3 (2mm), 4 (5mm)\n\n")
        f.write("**Unit Conversion**: Area density (g/m² or mg/m²) divided by tow depth → concentration (mg/m³)\n\n")
        f.write("**Aggregation**:\n")
        f.write("1. Sum of size fractions 0-4 per tow\n")
        f.write("2. Median of tows per day/depth_category/day_night\n\n")

        f.write("---\n\n")
        f.write("## Points d'attention et biais potentiels\n\n")

        f.write("### 1. Station fixe unique\n\n")
        f.write("- **Type** : Station ALOHA (~22.75°N, -158°W)\n")
        f.write("- **Avantage** : Séries temporelles sans confondant spatial, répétabilité élevée\n")
        f.write("- **Limitation** : Représentativité régionale limitée, pas de gradient spatial\n")
        f.write("- **Impact** : Excellente pour tendances temporelles, non généralisable ")
        f.write("à l'ensemble du gyre subtropical Nord-Pacifique\n\n")

        f.write("### 2. Fractionnement par taille\n\n")
        f.write("- **Méthode** : 5 fractions (0: 0.2-0.5mm, 1: 0.5-1mm, 2: 1-2mm, 3: 2-5mm, 4: >5mm)\n")
        f.write("- **Somme** : Fractions 0-4 (0.2-5mm et >5mm)\n")
        f.write("- **Avantage** : Information sur structure de taille du zooplancton\n")
        f.write("- **Limitation** : Somme totale mélange différentes efficacités de capture par fraction\n\n")

        f.write("### 3. Exclusion de la fraction 5 (>5mm)\n\n")
        frac5_count = len(df[df['frac'] == 5]) if 'frac' in df.columns else 0
        f.write(f"- **Fraction exclue** : Fraction 5 (>5mm) - {frac5_count} observations\n")
        f.write("- **Justification** : Capture du micronecton (organismes >20mm) mal échantillonné ")
        f.write("par filet 1m²/202µm, efficacité de capture très faible pour grands organismes mobiles\n")
        f.write("- **Organismes concernés** : Grands euphausiacés, méduses, larves de poissons, céphalopodes\n")
        f.write("- **Impact** : Sous-estimation de la biomasse totale, mais meilleure cohérence ")
        f.write("avec définition standard du zooplancton (<5mm)\n\n")

        f.write("### 4. Exclusion des traits aberrants (<50m)\n\n")
        f.write(f"- **Exclus** : {len(excluded_shallow)} traits avec profondeur <50m\n")
        f.write("- **Justification** : Écart majeur avec protocole standard (~175m), ")
        f.write("potentiels problèmes techniques ou conditions météo défavorables\n")
        f.write("- **Impact** : Perte d'information sur périodes à conditions difficiles\n\n")

        f.write("### 5. Variabilité des profondeurs de trait\n\n")
        depth_stats = final['tow_depth_max'].describe()
        f.write(f"- **Profondeur médiane** : {depth_stats['50%']:.0f}m\n")
        f.write(f"- **Variabilité** : {depth_stats['min']:.0f}-{depth_stats['max']:.0f}m ")
        f.write(f"(écart-type {depth_stats['std']:.0f}m)\n")
        f.write("- **Protocoles** : Deux standards observés (~150m et ~200m)\n")
        f.write("- **Impact** : Traits peu profonds échantillonnent uniquement l'épipélagique, ")
        f.write("traits profonds incluent une partie du mésopélagique\n")
        f.write("- **Mitigation** : Catégorisation ≤150m vs >150m\n\n")

        f.write("### 6. Conversion densité surfacique → concentration volumique\n\n")
        f.write("- **Formule** : concentration (mg/m³) = densité (mg/m²) / profondeur (m)\n")
        f.write("- **Hypothèse** : Distribution uniforme du zooplancton sur la colonne d'eau échantillonnée\n")
        f.write("- **Réalité** : Distribution verticale hétérogène (thermocline, DCM, migrations)\n")
        f.write("- **Impact** : Conversion valide pour comparaisons entre traits de même profondeur, ")
        f.write("biais potentiel lors de comparaisons entre profondeurs différentes\n\n")

        f.write("### 7. Disponibilité carbone et azote\n\n")
        f.write("- **Avantage unique** : Mesures directes de carbone (C) et azote (N) disponibles\n")
        f.write("- **Variables** : biomass_dry, biomass_carbon, biomass_nitrogen\n")
        f.write("- **Utilité** : Permet d'estimer les ratios C:N, conversion vers d'autres unités\n")
        f.write("- **Limitation** : Non disponible pour BATS/PAPA/CalCOFI, comparaisons limitées ")
        f.write("à la biomasse sèche\n\n")

        f.write("### 8. Classification jour/nuit\n\n")
        f.write("- **Méthode** : Heure locale simple (06h-18h = jour, 18h-06h = nuit)\n")
        f.write("- **Simplicité** : Facile à reproduire, pas de dépendance externe\n")
        f.write("- **Limitation** : Ne tient pas compte de la variation saisonnière du lever/coucher du soleil\n")
        day_pct = (df['day_night'] == 'day').sum() / len(df) * 100
        night_pct = (df['day_night'] == 'night').sum() / len(df) * 100
        f.write(f"- **Distribution observée** : {day_pct:.1f}% jour vs {night_pct:.1f}% nuit\n\n")

        f.write("### 9. Couverture temporelle\n\n")
        f.write(f"- **Période** : {df['time'].min().year}-{df['time'].max().year} ")
        f.write(f"({df['time'].max().year - df['time'].min().year + 1} ans)\n")
        f.write("- **Fréquence** : Mensuelle environ (varie selon périodes)\n")
        f.write("- **Gaps** : À vérifier (événements El Niño, problèmes logistiques)\n\n")

        f.write("---\n\n")
        f.write("*Generated with seapopym-data pipeline*\n")

    print(f"   ✓ Report saved to {REPORT_FILE}")
    print()

    print("=" * 60)
    print("✅ Processing complete!")
    print("=" * 60)
    print(f"Output NetCDF: {OUTPUT_NC}")
    print(f"Report: {REPORT_FILE}")


if __name__ == "__main__":
    main()
