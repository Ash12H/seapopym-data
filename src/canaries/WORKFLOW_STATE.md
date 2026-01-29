# Workflow State - Canaries

## Informations générales

- **Projet** : Traitement des données de zooplancton - Canaries (Couret et al. 2023)
- **Étape courante** : 6. Revue
- **Rôle actif** : Reviewer
- **Dernière mise à jour** : 2026-01-29

## Résumé du besoin

Créer un workflow de traitement pour les données de mésozooplancton du système du courant des Canaries (Couret et al. 2023), suivant le modèle des stations HOT/BATS/PAPA/CalCOFI.

**Entrée :**
- Fichier : `Couret-etal_2023.tab` (PANGAEA format)
- Période : 1971-2021 (50 ans)
- Biomasse carbone : mg C/m² (0-200m)
- ~1,975 observations

**Sortie :**
- Fichier NetCDF CF-1.8 : `canaries_zooplankton_obs.nc`
- Rapport Markdown avec figures et points d'attention

**Traitement :**
1. Conversion d'unités : mg C/m² → mg C/m³ (division par 200m)
2. Zones géographiques : Agrégation des 3 zones ensemble
3. Types de filets : Dataset unique incluant WP-2 (92%), LHPR (6%), Juday Bogorov (1%) avec variable `net_type`
4. Fractions de taille : Garder toutes (>200µm et >250µm, pas de >5mm)
5. Agrégation spatiale : Grille 1° lat/lon
6. Agrégation temporelle : Médiane journalière
7. Documentation : Points d'attention incluant hétérogénéité méthodologique

## Rapport d'analyse

### Structure du projet

Le projet suit une organisation par station avec structure standardisée :

```
src/
├── {station}/           # hot, bats, papa, calcofi, canaries
│   ├── data/
│   │   ├── raw/         # Données brutes (CSV, parquet, TSV)
│   │   ├── temp/        # Données intermédiaires
│   │   └── extra/       # Métadonnées supplémentaires
│   ├── release/         # NetCDF finaux (exclus du git via .gitignore)
│   ├── reports/
│   │   ├── figures/     # PNG générées
│   │   └── report.md    # Rapport markdown
│   ├── scripts/
│   │   └── process.py   # Script de traitement principal
│   └── WORKFLOW_STATE.md (optionnel, pour ASH)
├── core/                # Modules partagés
│   ├── io.py           # DataLoader, DataWriter
│   ├── plotting.py     # Plotter (cartopy, seaborn)
│   └── units.py        # UnitManager (pint)
```

**Note pour Canaries** : Actuellement utilise `1_raw/` au lieu de `data/raw/` → incohérence à corriger

### Technologies identifiées

- **Langage** : Python ≥3.12
- **Gestionnaire de paquets** : uv (pyproject.toml)
- **Manipulation de données** : pandas (3.0.0), xarray (2025.12.0)
- **Formats de données** : NetCDF4, Parquet, CSV/TSV
- **Visualisation** : matplotlib (3.10.8), seaborn (0.13.2), cartopy (0.25.0)
- **Calculs scientifiques** : numpy (via scipy 1.17.0), astral (3.2) pour jour/nuit
- **Unités** : pint-xarray (0.6.0), cf-xarray (0.10.10) pour CF-1.8
- **Linter** : ruff (line-length=88, ignore E402)
- **Tests** : pytest (9.0.2) - groupe dev

### Patterns et conventions

#### Nommage
- **Fichiers** : snake_case (`process.py`, `report.md`)
- **Répertoires** : snake_case (`data/raw/`, `reports/figures/`)
- **Variables Python** : snake_case (`biomass_carbon`, `day_night`)
- **Fonctions** : snake_case descriptives (`classify_day_night`, `lavaniegos_dv_to_carbon`)
- **Classes** : PascalCase (`DataLoader`, `Plotter`, `UnitManager`)

#### Structure des scripts process.py
1. **Imports** : stdlib → pathlib → pandas/numpy/xarray → astral → core modules
2. **PROJECT_ROOT** : Path resolution via `Path(__file__).parent.parent.parent.parent`
3. **Fonctions utilitaires** : Conversions spécifiques à la station (ex: `lavaniegos_dv_to_carbon`)
4. **Fonction main()** avec sections claires :
   - Paths (INPUT, OUTPUT, REPORTS)
   - Load data
   - Filter/clean data
   - Temporal processing (temps UTC, jour/nuit astral)
   - Spatial processing (binning si nécessaire)
   - Unit conversion
   - Aggregation (median par jour/depth_category/spatial_cell)
   - Export NetCDF (CF-1.8, compression zlib=5)
   - Generate figures (map avec cartopy, time series)
   - Generate report (markdown avec stats, figures, methodology, attention points)
5. **if __name__ == "__main__": main()**

#### Conventions NetCDF
- **Format** : CF-1.8 (Climate and Forecast)
- **Compression** : zlib=True, complevel=5
- **Dimensions** : `time`, `latitude`, `longitude` (si grille) ou `obs` (si points)
- **Variables principales** :
  - `biomass_carbon` (mg C/m³)
  - `day_night` (string: "day"/"night")
  - `depth_category` (string: "epipelagic_only"/"epipelagic_mesopelagic")
- **Attributs globaux** : title, institution, source, history, references
- **Attributs variables** : long_name, units, standard_name (CF), _FillValue

#### Classification jour/nuit
- **Méthode** : Astral library (calcul astronomique lever/coucher soleil)
- **Timezone** : UTC pour calcul, puis suppression timezone pour NetCDF
- **Gestion UTC wrap-around** : Nécessaire pour longitudes ouest (sunset < sunrise en UTC)

#### Agrégation temporelle
- **Résolution finale** : Journalière
- **Méthode** : Médiane des observations par jour/depth_category/spatial_cell

#### Agrégation spatiale
- **Stations fixes** (HOT, BATS, PAPA ≤0.5°) : Pas d'agrégation spatiale ou grille 0.5°
- **Régions étendues** (CalCOFI, Canaries) : Grille 1° lat/lon

#### Rapports markdown
- **Sections obligatoires** :
  1. En-tête (titre, date, location)
  2. Summary (initial/final rows, period, exclusions)
  3. Figures (map.png, time_series_biomass.png)
  4. Methodology (sampling method, net, fractions, aggregation)
  5. **Points d'attention et biais potentiels** (7-11 points numérotés)

### Points d'attention

#### Incohérences détectées
1. **Structure de répertoire Canaries** : Utilise `1_raw/` au lieu de `data/raw/` standard
2. **Format d'entrée** : PANGAEA TSV avec ~38 lignes d'en-têtes métadonnées (vs CSV/Parquet pour autres)

#### Spécificités Canaries à gérer
1. **Format PANGAEA** : Fichier `.tab` avec métadonnées en en-tête, nécessite parsing spécial
2. **Multi-sources** : 1,975 obs compilées depuis ~30 publications (1971-2021)
3. **Hétérogénéité méthodologique** :
   - 3 types de filets : WP-2 (92%), LHPR (6%), Juday Bogorov (1%)
   - 2 fractions de taille : >200µm (98.4%), >250µm (1.3%)
4. **Unités d'origine** : mg C/m² (0-200m) → conversion vers mg C/m³ nécessaire
5. **3 zones géographiques** : Area_1, Area_2, Area_3 (à agréger ensemble)
6. **Profondeur fixe** : 0-200m documentée, pas de variabilité comme HOT/BATS
7. **Pas de données excluant >5mm** : Toutes fractions ≤250µm sont cohérentes

#### Dette technique apparente
- Aucune détectée (projet récent, refactoring récent vers uv)

#### Zones complexes
1. **Parsing PANGAEA** : Nécessite détection ligne d'en-tête et gestion colonnes avec métadonnées
2. **Conversion mg C/m² → mg C/m³** : Division par 200m (profondeur fixe)
3. **Documentation multi-méthodes** : Traçabilité via variable `net_type`

## Décisions d'architecture

### Choix techniques

| Domaine | Choix | Justification |
| ------- | ----- | ------------- |
| Parsing données | pandas.read_csv() avec skiprows | Format PANGAEA TSV avec 38 lignes d'en-têtes, délimiteur TAB |
| Manipulation données | pandas → xarray | Pattern établi (HOT/BATS/PAPA/CalCOFI) |
| Conversion unités | Division par 200m | mg C/m² → mg C/m³, profondeur fixe 0-200m |
| Classification jour/nuit | astral library | Pattern établi, calcul astronomique précis |
| Agrégation spatiale | Grille 1° lat/lon | Couverture large (Canaries + upwelling NW Afrique) |
| Agrégation temporelle | Médiane journalière | Pattern établi, robuste aux outliers |
| Export | NetCDF CF-1.8, zlib=5 | Standard projet |
| Visualisation | cartopy + seaborn | Pattern établi, maps avec coastlines |
| Variable net_type | Catégorielle string | Traçabilité des 3 méthodes (WP-2, LHPR, Juday Bogorov) |

### Structure proposée

```
src/canaries/
├── data/               # ✓ Correction : 1_raw/ → data/ (cohérence projet)
│   ├── raw/            # Couret-etal_2023.tab (déplacé depuis 1_raw/)
│   ├── temp/           # Optionnel, données intermédiaires
│   └── extra/          # Optionnel, métadonnées
├── release/
│   └── canaries_zooplankton_obs.nc
├── reports/
│   ├── figures/
│   │   ├── map.png
│   │   └── time_series_biomass.png
│   └── report.md
├── scripts/
│   └── process.py      # Script principal
└── WORKFLOW_STATE.md
```

### Flux de traitement (process.py)

```
1. LOAD DATA
   ├─ Lire Couret-etal_2023.tab (skiprows=37, sep='\t')
   └─ Colonnes : Reference, Latitude, Longitude, Area, Date/Time,
                 Size fraction, Station, Device, Period, Biom C

2. CLEAN & FILTER
   ├─ Renommer colonnes : snake_case standard
   ├─ Parser dates (format YYYY-MM-DD)
   ├─ Garder toutes fractions (>200µm, >250µm)
   └─ Pas d'exclusion (pas de >5mm détecté)

3. UNIT CONVERSION
   ├─ biomass_carbon_m2 (mg C/m²) → biomass_carbon (mg C/m³)
   └─ Formule : biomass_carbon = biomass_carbon_m2 / 200

4. TEMPORAL PROCESSING
   ├─ time : pd.to_datetime() → UTC
   ├─ day_night : classify_day_night(astral)
   ├─ Retirer timezone (NetCDF compatibility)
   └─ date : floor to day

5. SPATIAL BINNING
   ├─ lat_bin = round(latitude, 0)  # 1° grid
   └─ lon_bin = round(longitude, 0)

6. DEPTH CATEGORY
   └─ depth_category = "epipelagic_only" (tous les traits 0-200m)

7. AGGREGATION
   ├─ Group by: date, lat_bin, lon_bin, depth_category, day_night
   └─ Median(biomass_carbon)

8. EXPORT NETCDF
   ├─ Dimensions: obs (n observations agrégées)
   ├─ Coords: time, latitude, longitude
   ├─ Data vars: biomass_carbon, day_night, depth_category, net_type,
   │             area_original (Area_1/2/3), size_fraction
   └─ CF-1.8 attributes + compression

9. GENERATE FIGURES
   ├─ map.png : Cartopy avec coastlines, land, borders
   └─ time_series_biomass.png : Biomasse vs temps

10. GENERATE REPORT
    └─ report.md : Summary, Figures, Methodology, Points d'attention
```

### Interfaces et contrats

**Fonction classify_day_night(row)**
- Input : pd.Series avec `time` (datetime UTC tz-aware), `latitude`, `longitude`
- Output : str ("day" ou "night")
- Pattern : Identique HOT/BATS/PAPA/CalCOFI

**Fonction de conversion**
```python
def convert_carbon_m2_to_m3(carbon_m2: float, depth: float = 200) -> float:
    """Convert carbon biomass from mg C/m² to mg C/m³."""
    return carbon_m2 / depth
```

**Variables NetCDF**
- `biomass_carbon` : float32, mg C/m³, _FillValue=np.nan
- `day_night` : string, {"day", "night"}
- `depth_category` : string, {"epipelagic_only"}
- `net_type` : string, {"WP-2", "LHPR", "Juday Bogorov (50 cmx2)"}
- `area_original` : string, {"Area_1", "Area_2", "Area_3"} (optionnel, traçabilité)
- `size_fraction` : string, {">200", ">250"} (optionnel, traçabilité)

### Risques identifiés

| Risque | Impact | Mitigation |
|--------|--------|------------|
| Parsing incorrect PANGAEA (ligne d'en-tête variable) | Haut | Vérifier skiprows=37 via inspection manuelle, valider colonnes attendues |
| Qualité hétérogène données multi-sources | Moyen | Variable `Reference` pour traçabilité, documentation points d'attention |
| Conversion mg C/m² → mg C/m³ sur profondeur fixe 200m | Moyen | Documenter hypothèse distribution uniforme, cohérent avec métadonnées PANGAEA |
| Timezone wrap-around (Canaries ~28°N, -16°W) | Bas | Astral gère automatiquement, code testé sur CalCOFI (similaire) |
| Peu de données LHPR/Juday Bogorov (7% total) | Bas | Variable net_type permet filtrage a posteriori si nécessaire |

### Points d'attention à documenter

1. **Multi-sources** : Compilation de ~30 publications (1971-2021), hétérogénéité méthodologique
2. **Hétérogénéité des filets** : WP-2 (92%), LHPR (6%), Juday Bogorov (1%)
3. **Conversion mg C/m² → mg C/m³** : Hypothèse distribution uniforme 0-200m
4. **Profondeur fixe** : Pas de variabilité documentée (contrairement HOT/BATS)
5. **Fractions de taille** : >200µm (98.4%), >250µm (1.3%), cohérent avec autres stations
6. **3 zones géographiques** : Area_1 (North), Area_2 (South/Islands), Area_3 (Upwelling) agrégées
7. **Agrégation spatiale 1°** : Lissage variations locales, justifié par couverture large
8. **Pas d'exclusions** : Contrairement HOT/BATS (<50m), toutes obs conservées
9. **Classification jour/nuit** : Astral, précision astronomique
10. **Couverture temporelle/spatiale** : 50 ans mais échantillonnage irrégulier

## Todo List

| État | ID | Nom | Description | Dépendances | Résolution |
| ---- | -- | --- | ----------- | ----------- | ---------- |
| ☑ | T1 | Restructurer répertoires | Créer data/raw/, data/temp/, data/extra/ et déplacer 1_raw/Couret-etal_2023.tab → data/raw/ | - | Répertoires créés et fichier déplacé |
| ☑ | T2 | Créer répertoires release et reports | Créer release/, reports/, reports/figures/ | - | Répertoires créés |
| ☑ | T3 | Créer scripts/process.py (structure) | Créer fichier avec imports, PROJECT_ROOT, structure main() vide | T1, T2 | Fichier créé avec structure de base |
| ☑ | T4 | Implémenter convert_carbon_m2_to_m3 | Ajouter fonction de conversion mg C/m² → mg C/m³ dans process.py | T3 | Fonction implémentée (division par 200m) |
| ☑ | T5 | Implémenter classify_day_night | Ajouter fonction classification jour/nuit avec astral (pattern CalCOFI) | T3 | Fonction implémentée (non utilisée, colonne period utilisée à la place) |
| ☑ | T6 | Implémenter section LOAD DATA | Parser PANGAEA TSV (skiprows=41, sep='\t'), renommer colonnes snake_case | T3 | Section implémentée, 1970 lignes chargées |
| ☑ | T7 | Implémenter section CLEAN & FILTER | Parser dates, vérifier fractions, pas d'exclusions | T6 | Section implémentée, pas d'exclusions |
| ☑ | T8 | Implémenter section UNIT CONVERSION | Appliquer convert_carbon_m2_to_m3 sur colonne biomass | T4, T7 | Section implémentée, range 0.01-31.19 mg C/m³ |
| ☑ | T9 | Implémenter section TEMPORAL PROCESSING | Convertir UTC, utiliser colonne period, retirer timezone, créer date | T5, T8 | Section implémentée, 81.3% jour, 18.7% nuit |
| ☑ | T10 | Implémenter section SPATIAL BINNING | Créer lat_bin, lon_bin (grille 1°) | T9 | Section implémentée, 44 cellules uniques |
| ☑ | T11 | Implémenter section DEPTH ASSIGNMENT | Assigner depth_category="epipelagic_only", tow_depth_max=200 | T10 | Section implémentée, tous 0-200m |
| ☑ | T12 | Implémenter section AGGREGATION | Group by date/lat_bin/lon_bin/depth_category/day_night, median biomass | T11 | Section implémentée, 1970→813 obs |
| ☑ | T13 | Implémenter section EXPORT NETCDF | Créer xr.Dataset CF-1.8, compression, save canaries_zooplankton_obs.nc | T12 | NetCDF exporté avec succès (conversion object dtype pour strings) |
| ☑ | T14 | Implémenter section GENERATE FIGURES | Créer map.png (cartopy) et time_series_biomass.png | T12 | Figures générées avec succès |
| ☑ | T15 | Implémenter section GENERATE REPORT | Créer report.md avec summary, figures, methodology, 10 points d'attention | T13, T14 | Rapport généré avec 10 points d'attention |
| ☑ | T16 | Supprimer 1_raw/ (cleanup) | Supprimer répertoire 1_raw/ après migration vers data/raw/ | T1, T15 | Répertoire supprimé |

## Historique des transitions

| De | Vers | Raison | Date |
| -- | ---- | ------ | ---- |
| - | 1. Initialisation | Création du workflow pour traitement données Canaries | 2026-01-29 |
| 1. Initialisation | 2. Analyse | Besoin validé par l'utilisateur | 2026-01-29 |
| 2. Analyse | 3. Architecture | Analyse complétée | 2026-01-29 |
| 3. Architecture | 4. Planification | Architecture validée par l'utilisateur | 2026-01-29 |
| 4. Planification | 5. Execution | Todo list complétée (16 tâches) | 2026-01-29 |
| 5. Execution | 6. Revue | Toutes les tâches traitées avec succès | 2026-01-29 |
