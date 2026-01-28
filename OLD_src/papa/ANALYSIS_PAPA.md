# Analyse de traitement : Station PAPA (North Pacific)

**Date d'analyse** : 2026-01-28
**Version analysée** : OLD_src/papa
**Période des données** : 1995-09-24 à 2020-08-31

---

## 1. Source et description des données

### Source
- **Organisme** : DFO (Department of Fisheries and Oceans Canada)
- **Base de données** : Zooplankton Database (North Pacific)
- **Documentation** : [Data Dictionary](https://api-proxy.edh-cde.dfo-mpo.gc.ca/catalogue/records/9447ecf8-a7f7-4904-8ab0-3c597c534c4b/attachments/Data_dictionary_EN_FR_zooplankton_database.htm)

### Fichier brut
- **Fichier** : `1_raw/papa_zooplankton.csv`
- **Format** : CSV avec séparateur `;` et décimale `,`
- **Nombre d'enregistrements** : 1,077 traits
- **Période** : 1995-09-24 à 2020-08-31 (25 ans)

---

## 2. Structure des données

### Variables métadonnées

| Variable | Type | Description |
|----------|------|-------------|
| `Date` | string | Date du trait (format: "D M Y") |
| `STN_TIME` | string | Heure du trait (HHMM) |
| `lat` | float | Latitude (décimal) |
| `lon` | float | Longitude (décimal) |
| `Station` | string | Nom de la station |
| `DEPTH_STRT` | int | Profondeur du trait (m) |
| `DEPTH_END` | int | Toujours 0 (surface) |
| `Volume Filtered(m3)` | float | Volume d'eau filtré (m³) |
| `Mesh_Size(um)` | int | Taille de maille (µm) |
| `Twilight` | category | "Daylight" ou "Night" |
| `Net_Type` | string | Type de filet (Bongo, Ring, SCOR, etc.) |

### Variables taxonomiques

**94 colonnes** de biomasse taxonomique en **mg/m³** (dry weight)

Groupes taxonomiques principaux :
- **Annélides** : ANNE:POLY (polychètes)
- **Crustacés** : ARCR (copépodes, amphipodes, décapodes, euphausiacés, isopodes, ostracodes)
- **Chaetognathes** : CHAE
- **Cnidaires** : CNID (méduses, siphonophores, scyphozoaires)
- **Cténophores** : CTEN
- **Échinodermes** : ECHI
- **Mollusques** : MOGA, MOCE (ptéropodes, céphalopodes, hétéropodes)
- **Tuniciers** : UROC (larvacés, thaliacés)
- **Poissons** : VERT:PISC
- **Autres** : ECTO (bryozoaires), CHRO (protozoaires)

---

## 3. Différences avec HOT/BATS

| Aspect | HOT/BATS | PAPA |
|--------|----------|------|
| **Type de station** | Station fixe unique | 314 stations sur une grande zone |
| **Type de données** | Biomasse totale par fraction de taille | Biomasse par taxon |
| **Fractions** | 5-6 fractions de taille (0.2-5mm) | 94 taxa avec tailles variables |
| **Variables** | dwt total (+ C, N pour HOT) | dwt par taxon |
| **Couverture spatiale** | 1 point fixe | Zone 46-58°N, -158 à -128°W |
| **Exclusions** | Fraction >5mm (micronecton) | Polychètes adultes (benthiques) |

---

## 4. Distribution des données

### Profondeurs

| Statistique | Valeur |
|-------------|--------|
| Min | 30 m |
| Q1 | 150 m |
| Médiane | 150 m |
| Q3 | 250 m |
| Max | 295 m |
| Moyenne | 188.7 ± 56.0 m |

**Distribution** :
- 0-50m : 16 traits (1.5%) - aberrants
- 50-100m : 18 traits (1.7%)
- 100-150m : 159 traits (14.8%)
- **150-200m** : 409 traits (38.0%) ← protocole standard 1
- 200-250m : 194 traits (18.0%)
- **250-300m** : 281 traits (26.1%) ← protocole standard 2

**Observation** : Deux protocoles standards distincts (150m et 250m).

### Jour/Nuit

- **Daylight** : 799 traits (74.2%)
- **Night** : 278 traits (25.8%)

**Note** : Majorité de traits de jour (contrairement à HOT/BATS qui ont des réplicats jour/nuit équilibrés).

### Maille de filet

- **236 µm** : 854 traits (79.3%) ← standard, cohérent avec HOT/BATS
- 253 µm : 96 traits (8.9%)
- 333-335 µm : 122 traits (11.3%)
- Autres : 5 traits (0.5%)

### Stations

- **314 stations uniques** sur une vaste zone
- **96 stations récurrentes** (>1 observation)

**Top 10 stations** :
1. P26 : 110 observations (Alaska Basin East)
2. P12 : 71 observations (Northern Vancouver Island Offshore)
3. P08 : 69 observations
4. P20 : 64 observations
5. P16 : 59 observations
6. LBP7 : 43 observations
7. CS01 : 40 observations
8. ODAS : 30 observations
9. CS00 : 19 observations
10. T10 : 13 observations

---

## 5. Workflow OLD (critique)

### Étape 1 : Agrégation taxonomique

```python
taxa_groups = {
    "benthos": ["ANNE:POLY: >> POLY larvae s1"],
    "crustacean": ["ARCR"],
    "chaetognatha": ["CHAE"],
    "small_gelatinous": ["CNID", "CTEN"],
    "larvacean": ["LARV"],
    "thaliacea": ["THAL"],
    "others": ["ECHI", "ECTO", "MOCE", "MOGA", "MOLL", "PROT", "PISC", "XXXX"],
}
```

**Exclusions** :
- `ANNE:POLY: >> POLY s1, s2, s3` : Polychètes adultes (benthiques, pas pélagiques)

**Somme** : `total = sum(tous les groupes)`

### Étape 2 : Binning spatial et profondeur

```python
# Binning profondeur (PROBLÉMATIQUE)
final_data["depth"] = pd.cut(depth, bins=[0, 50, 100, 150, 200, 250, 300, 350, 400])

# Binning spatial 1°×1° (PROBLÉMATIQUE)
final_data["lon"] = pd.cut(lon, bins=np.arange(-158, -126, 1))
final_data["lat"] = pd.cut(lat, bins=np.arange(46, 59, 1))
```

⚠️ **Problèmes identiques à HOT/BATS** :
- Binning profondeur inapproprié pour traits obliques
- Résolution spatiale 1° trop grossière

### Étape 3 : Export

```python
preprocessed_data[var].attrs = {"units": "mg/m3"}  # ✅ Correct maintenant !
```

---

## 6. Workflow recommandé (aligné sur HOT/BATS)

### Étape 1 : Lecture et filtrage initial

```python
df = pd.read_csv('papa_zooplankton.csv', sep=';', decimal=',', on_bad_lines='skip')

# Exclusion 1 : Traits aberrants (depth <50m)
df = df[df['DEPTH_STRT'] >= 50]  # Exclut 16 traits (1.5%)

# Exclusion 2 : Polychètes adultes (benthiques)
polychaete_adults = ['ANNE:POLY: >> POLY s1', 'ANNE:POLY: >> POLY s2', 'ANNE:POLY: >> POLY s3']
# Ces colonnes ne seront pas sommées
```

### Étape 2 : Conversion temporelle

```python
df['time'] = pd.to_datetime(df['Date'], format='%d %m %Y')
df['date'] = df['time'].dt.floor('D')
df['hour'] = extract_hour_from_STN_TIME(df['STN_TIME'])
df['day_night'] = df['Twilight'].apply(lambda x: 'day' if x == 'Daylight' else 'night')
```

### Étape 3 : Catégorisation profondeur

```python
# Même seuil 150m que HOT/BATS
df['depth_category'] = np.where(
    df['DEPTH_STRT'] <= 150,
    'epipelagic_only',
    'epipelagic_mesopelagic'
)
```

**Résultat attendu** :
- epipelagic_only (≤150m) : ~193 traits (18%)
- epipelagic_mesopelagic (>150m) : ~868 traits (82%)

### Étape 4 : Somme des taxa

```python
# Colonnes taxonomiques (exclure les 3 polychètes adultes)
taxa_cols = [col for col in df.columns[20:]
             if col not in polychaete_adults]

# Somme de tous les taxa
df['biomass_dry'] = df[taxa_cols].sum(axis=1)
```

### Étape 5 : Agrégation spatiale (grille 0.5°)

```python
# Binning spatial 0.5° (comme OLD)
df['lat_bin'] = (df['lat'] * 2).round() / 2  # centres: 46.5, 47.0, 47.5, ...
df['lon_bin'] = (df['lon'] * 2).round() / 2  # centres: -158.0, -157.5, ...
```

### Étape 6 : Identifier les tows

```python
# Tows uniques : même date, même position, même profondeur
df['tow_id'] = df.groupby(['date', 'lat_bin', 'lon_bin', 'DEPTH_STRT']).ngroup()
```

### Étape 7 : Agrégation niveau 1 (par tow)

```python
# Si plusieurs mesures par tow (rare), prendre la moyenne
agg1 = df.groupby(['date', 'lat_bin', 'lon_bin', 'day_night', 'depth_category', 'tow_id']).agg({
    'biomass_dry': 'mean',
    'DEPTH_STRT': 'first',
}).reset_index()
```

### Étape 8 : Agrégation niveau 2 (par cellule spatio-temporelle)

```python
# Médiane des tows par jour/cellule/catégorie
final = agg1.groupby(['date', 'lat_bin', 'lon_bin', 'day_night', 'depth_category']).agg({
    'biomass_dry': 'median',
    'DEPTH_STRT': 'median',
}).reset_index()
```

### Étape 9 : Conversion en xarray

```python
ds = xr.Dataset.from_dataframe(
    final.set_index(['date', 'lat_bin', 'lon_bin', 'depth_category', 'day_night'])
)

ds = ds.rename({
    'date': 'time',
    'lat_bin': 'lat',
    'lon_bin': 'lon',
    'DEPTH_STRT': 'tow_depth_max'
})
```

### Étape 10 : Métadonnées

```python
ds.attrs = {
    'title': 'PAPA Zooplankton Observations',
    'source': 'DFO Canada Zooplankton Database',
    'institution': 'DFO',
    'net_type': 'Bongo (majority), mesh 236 µm',
    'spatial_resolution': '0.5 degrees',
    'processing_date': datetime.now().isoformat(),
    'excluded_data': 'depth <50m, adult polychaetes (benthic)',
    'conventions': 'CF-1.8'
}

ds['biomass_dry'].attrs = {
    'units': 'mg m-3',
    'long_name': 'Dry weight biomass concentration (sum of 91 taxa)',
    'comment': 'Excludes adult polychaetes (ANNE:POLY s1, s2, s3)'
}

ds['tow_depth_max'].attrs = {
    'units': 'm',
    'long_name': 'Maximum tow depth'
}
```

---

## 7. Exclusions à appliquer

### Exclusion 1 : Traits aberrants (depth <50m)

- **Critère** : `DEPTH_STRT < 50`
- **Impact** : 16 traits sur 1,077 (1.5%)
- **Justification** : Écart avec les protocoles standards (150m, 250m), similaire à HOT/BATS

### Exclusion 2 : Polychètes adultes (benthiques)

- **Critère** : 3 colonnes taxonomiques
  - `ANNE:POLY: >> POLY s1`
  - `ANNE:POLY: >> POLY s2`
  - `ANNE:POLY: >> POLY s3`
- **Justification** :
  - Organismes benthiques (vivent sur le fond)
  - Pas du vrai zooplancton pélagique
  - Capture accidentelle lors des traits
  - **Conservé** : `ANNE:POLY: >> POLY larvae s1` (larves planctoniques)

### Données conservées

- **91 taxa planctoniques** (sur 94)
- **1,061 traits** de profondeur standard (≥50m)
- **Période** : 1995-2020 (25 ans)
- **Couverture** : 314 stations, Pacifique Nord-Est

---

## 8. Points d'attention

### Différences avec HOT/BATS

✅ **Avantages** :
- Couverture spatiale large (314 stations)
- Résolution taxonomique élevée (91 taxa)
- Longue série temporelle (25 ans)

⚠️ **Défis** :
- Pas de station fixe (nécessite agrégation spatiale 0.5°)
- Pas de carbone/azote (seulement dry weight)
- Déséquilibre jour/nuit (74% jour, 26% nuit)
- Deux protocoles de profondeur (150m et 250m)

### Compatibilité avec HOT/BATS

| Aspect | Statut |
|--------|--------|
| **Unités** | ✅ Compatible (mg/m³) |
| **Catégorisation profondeur** | ✅ Même seuil 150m |
| **Jour/Nuit** | ✅ Même logique |
| **Agrégation temporelle** | ✅ Journalière |
| **Structure NetCDF** | ✅ Même format |
| **Carbone** | ❌ Non disponible (comme BATS) |

---

## 9. Comparaison OLD vs NEW workflow

| Étape | OLD | NEW | Amélioration |
|-------|-----|-----|--------------|
| **Filtrage profondeur** | Aucun | Exclut <50m | ✅ Cohérence avec HOT/BATS |
| **Binning profondeur** | Bins 50m | Catégories ≤150m / >150m | ✅ Adapté aux traits obliques |
| **Résolution spatiale** | 1° | 0.5° | ✅ Meilleure résolution |
| **Agrégation temporelle** | Par cellule | Par tow puis médiane | ✅ Plus robuste |
| **Exclusions taxonomiques** | Polychètes adultes | Même chose | ✅ Identique |
| **Métadonnées** | Minimales | CF-1.8 complètes | ✅ Standards |

---

## 10. Prochaines étapes

1. ✅ Analyser distribution profondeurs → Validé
2. ✅ Identifier exclusions taxonomiques → Polychètes adultes
3. ⏳ Implémenter script de processing
4. ⏳ Générer NetCDF et rapport
5. ⏳ Commit des changements

---

## Références

- DFO Canada Zooplankton Database: https://api-proxy.edh-cde.dfo-mpo.gc.ca/catalogue/records/9447ecf8-a7f7-4904-8ab0-3c597c534c4b
- Métadonnées supplémentaires : `src/papa/data/extra/meta-data.md`
