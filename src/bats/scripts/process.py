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
    RAW_DIR = STATION_DIR / "data" / "raw"
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
    # Day/Night classification using time_in (HHMM local time)
    # The 'time' column only contains dates (T00:00:00), not actual tow times
    df["time_in"] = pd.to_numeric(df["time_in"], errors="coerce")
    df["hour"] = df["time_in"] // 100
    df["day_night"] = df["hour"].apply(lambda h: "day" if 6 <= h < 18 else "night")
    print(f"   Day samples: {(df['day_night'] == 'day').sum()}")
    print(f"   Night samples: {(df['day_night'] == 'night').sum()}")
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
                "dry_weight_vol_water_ratio": lambda x: x.sum(min_count=1),
                "wet_weight_vol_water_ratio": lambda x: x.sum(min_count=1),
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

        f.write("## Methodology\n\n")
        f.write("**Sampling Method**: Double oblique tows (surface → ~200m → surface, ~30 min)\n\n")
        f.write("**Net**: 1 m² rectangular with 202 µm mesh\n\n")
        f.write("**Size Fractions**: Wet sieving through nested sieves (5.0, 2.0, 1.0, 0.5, 0.2 mm)\n\n")
        f.write("**Fractions analyzed**: 200µm, 500µm, 1mm, 2mm (excluding 5mm)\n\n")
        f.write("**Aggregation**:\n")
        f.write("1. Sum of size fractions per tow\n")
        f.write("2. Median of tows per day/depth_category/day_night\n\n")

        f.write("## Points d'attention et biais potentiels\n\n")

        f.write("### 1. Station fixe unique\n\n")
        f.write("- **Type** : Station BATS (~31.6°N, -64.2°W)\n")
        f.write("- **Avantage** : Séries temporelles sans confondant spatial, protocole standardisé\n")
        f.write("- **Limitation** : Représentativité régionale limitée au gyre subtropical Nord-Atlantique\n")
        f.write("- **Impact** : Excellente pour tendances temporelles, comparaisons inter-bassins ")
        f.write("nécessitent prudence\n\n")

        f.write("### 2. Fractionnement par taille\n\n")
        f.write("- **Méthode** : 5 tamis emboîtés (5.0, 2.0, 1.0, 0.5, 0.2 mm)\n")
        f.write("- **Fractions** : 200µm (0.2-0.5mm), 500µm (0.5-1mm), 1mm (1-2mm), 2mm (2-5mm), 5mm (>5mm)\n")
        f.write("- **Somme** : Fractions 200-2000µm uniquement\n")
        f.write("- **Avantage** : Information sur structure de taille\n")
        f.write("- **Différence HOT** : Pas de fraction <200µm (HOT a fraction 0)\n\n")

        f.write("### 3. Exclusion de la fraction 5000µm (>5mm)\n\n")
        f.write(f"- **Exclus** : {len(excluded_5000)} observations (fraction >5mm)\n")
        f.write("- **Justification** : Capture tout ce qui est >5mm sans limite supérieure, ")
        f.write("inclut potentiellement du micronecton >20mm mal échantillonné par filet 1m²/202µm\n")
        f.write("- **Organismes concernés** : Grands euphausiacés, méduses, larves de poissons\n")
        f.write("- **Impact** : Sous-estimation de la biomasse totale, cohérence avec définition ")
        f.write("zooplancton <5mm et avec HOT/PAPA/CalCOFI\n\n")

        f.write("### 4. Exclusion des traits aberrants (<50m)\n\n")
        f.write(f"- **Exclus** : {len(excluded_shallow)} traits avec profondeur <50m\n")
        f.write("- **Justification** : Écart majeur avec protocole standard (~200m)\n")
        f.write("- **Impact** : Amélioration cohérence, perte d'info sur conditions difficiles\n\n")

        f.write("### 5. Exclusion des lignes sans sieve_size\n\n")
        f.write(f"- **Exclus** : {len(excluded_no_sieve)} lignes sans information de tamis\n")
        f.write("- **Justification** : Impossible de catégoriser par taille sans cette information\n")
        f.write(f"- **Impact** : Perte minime ({len(excluded_no_sieve)/initial_rows*100:.1f}% des données)\n\n")

        f.write("### 6. Variabilité des profondeurs de trait\n\n")
        depth_stats = df['tow_depth_max'].describe()
        f.write(f"- **Profondeur médiane** : {depth_stats['50%']:.0f}m\n")
        f.write(f"- **Variabilité** : {depth_stats['min']:.0f}-{depth_stats['max']:.0f}m ")
        f.write(f"(écart-type {depth_stats['std']:.0f}m)\n")
        f.write("- **Protocole standard** : ~200m (double oblique)\n")
        f.write("- **Impact** : Variabilité de profondeur affecte volume échantillonné et ")
        f.write("couverture verticale\n")
        f.write("- **Mitigation** : Données pré-normalisées en mg/m³ (concentration volumique), ")
        f.write("catégorisation ≤150m vs >150m\n\n")

        f.write("### 7. Concentrations pré-calculées\n\n")
        f.write("- **Avantage** : Variables `*_vol_water_ratio` déjà en mg/m³ dans les données brutes\n")
        f.write("- **Différence HOT** : Pas de conversion m² → m³ nécessaire (HOT fournit mg/m²)\n")
        f.write("- **Validation** : Ratios vérifiés = poids / volume d'eau filtré\n")
        f.write("- **Impact** : Moins d'étapes de traitement, moins d'erreurs potentielles\n\n")

        f.write("### 8. Absence de données carbone/azote\n\n")
        f.write("- **Limitation** : Seulement poids sec et poids humide disponibles\n")
        f.write("- **Différence HOT** : HOT fournit C et N, permet calculs stoechiométriques\n")
        f.write("- **Impact** : Comparaisons avec HOT limitées à la biomasse sèche\n")
        f.write("- **Note** : C et N mesurés 1994-1998 uniquement (4 cruises/an), non exploité ici\n\n")

        f.write("### 9. Classification jour/nuit\n\n")
        f.write("- **Méthode** : Heure locale (time_in, format HHMM) : 06h-18h = jour, 18h-06h = nuit\n")
        f.write("- **Source** : Colonne `time_in` des données brutes (heure locale de début de trait)\n")
        f.write("- **Limitation** : Pas de correction saisonnière du lever/coucher du soleil\n")
        day_pct = (df['day_night'] == 'day').sum() / len(df) * 100
        night_pct = (df['day_night'] == 'night').sum() / len(df) * 100
        f.write(f"- **Distribution observée** : {day_pct:.1f}% jour vs {night_pct:.1f}% nuit\n\n")

        f.write("### 10. Protocole d'échantillonnage\n\n")
        f.write("- **Fréquence** : 2 réplicats jour (09h-15h) et 2 réplicats nuit (20h-02h) par cruise\n")
        f.write("- **Réplicats** : Permet estimation variabilité intra-journalière\n")
        f.write("- **Agrégation** : Médiane des réplicats par jour/catégorie\n\n")

        f.write("### 11. Couverture temporelle\n\n")
        f.write(f"- **Période** : {df['time'].min().year}-{df['time'].max().year} ")
        f.write(f"({df['time'].max().year - df['time'].min().year + 1} ans)\n")
        f.write("- **Fréquence** : Variable selon périodes\n")
        f.write("- **Gaps** : À documenter (problèmes logistiques, météo)\n\n")
    print(f"   ✓ {REPORT_FILE}")
    print()

    print("=" * 60)
    print("✅ Processing complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
