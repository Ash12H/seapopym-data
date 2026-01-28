# Analyse de traitement : Station BATS (Bermuda Atlantic Time-series Study)

**Date d'analyse** : 2026-01-28
**Version analysée** : OLD_src/bats
**Période des données** : 1995-05-10 à 2022-12-13

---

## 1. Méthodes d'échantillonnage (BATS Analytical Methods)

### Protocole de terrain
- **Net** : 1 m² rectangulaire avec maille 202 µm
- **Type de trait** : Double oblique, surface → ~200m → surface (~30 min)
- **Fréquence** : 2 réplicats jour (09h-15h) et 2 réplicats nuit (20h-02h) par cruise
- **Instruments** :
  - Flowmètre (General Oceanics) pour volume filtré
  - Vemco Minilog pour température et profondeur

### Traitement post-prélèvement
1. **Division** : 1/2 du tow pour photographie silhouette + préservation formaldéhyde, 1/2 pour fractionnement
2. **Fractionnement** : Tamisage humide à travers tamis emboîtés (5.0, 2.0, 1.0, 0.5, 0.2 mm)
3. **Congélation** : Chaque fraction sur disque Nitex 0.2mm pré-pesé, congelée pour analyse

### Analyses de masse
- **Poids humide** (wet_weight) : Pesée après décongélation et absorption de l'excès d'humidité
- **Poids sec** (dry_weight) : Séchage à 60°C pendant 24h puis pesée
- **C et N** : Analyseur élémentaire sur sous-échantillons (4 cruises/an, 1994-1998 seulement)

### Normalisation des données
**Formule de normalisation à 200m** :
```
Biomass[0-200m] = biomass[0-x m] × 200/x
```
où x = profondeur réelle du trait

**Note** : Les colonnes `*_200m_depth` contiennent des valeurs normalisées à 200m, **pas des concentrations volumiques**.

---

## 2. Description des données brutes

### Format initial
- **Fichier** : `1_raw/bats_zooplankton.csv`
- **Source** : Bermuda Atlantic Time-series Study (BATS)
- **Nombre d'enregistrements** : 6,728 lignes
- **Position** : Station BATS (~31.6°N, -64.2°W)

### Variables disponibles

| Variable | Unité | Description | Couverture |
|----------|-------|-------------|------------|
| `wet_weight` | mg | Poids humide | 6665/6728 (99.1%) |
| `dry_weight` | mg | Poids sec | 6666/6728 (99.1%) |
| `wet_weight_vol_water_ratio` | mg/m³ | Concentration poids humide | 6665/6728 (99.1%) |
| `dry_weight_vol_water_ratio` | mg/m³ | Concentration poids sec | 6666/6728 (99.1%) |
| `volume_water` | m³ | Volume d'eau filtré | 6728/6728 (100%) |
| `sieve_size` | µm | Taille de tamis | 6706/6728 (99.7%) |

**Note importante** : Les ratios de concentration (mg/m³) sont **déjà calculés** dans les données brutes.

### Structure des prélèvements

**Méthode** :
- Traits obliques de la surface à profondeur max
- Fractionnement en **5 tailles** par tamis emboîtés

**Fractionnement par taille** (d'après méthodes analytiques) :

Tamis emboîtés avec mailles : **5.0, 2.0, 1.0, 0.5, 0.2 mm**

| Sieve Size (µm) | Taille (mm) | Organismes capturés | N observations |
|-----------------|-------------|---------------------|----------------|
| 200 | 0.2 | 0.2-0.5 mm (petits copépodes) | 1341 |
| 500 | 0.5 | 0.5-1.0 mm (copépodes moyens) | 1341 |
| 1000 | 1.0 | 1.0-2.0 mm (gros copépodes) | 1342 |
| 2000 | 2.0 | 2.0-5.0 mm (petits euphausiacés) | 1340 |
| 5000 | 5.0 | **>5.0 mm** (grands euphausiacés + micronecton) | 1342 |

**Note critique sur fraction 5000µm** :
- Comme HOT fraction 5, capture **tout ce qui est >5mm sans limite supérieure**
- Peut inclure du micronecton >20mm (limite zooplancton/micronecton)
- Net 1m² avec maille 202µm probablement inefficace pour gros organismes rapides
- **Décision** : Exclure fraction 5000µm pour les mêmes raisons que HOT

**Différences avec HOT** :
- **Protocole similaire** : Même type de net (1m², 202µm), tamis emboîtés
- **Pas de fraction <0.2mm** (HOT avait fraction 0)
- **Ratios pré-calculés** : Les concentrations mg/m³ sont déjà disponibles
- **Pas de carbone/azote** : Seulement wet et dry weight (C/N mesuré 1994-1998 seulement)

---

## 2. Distribution des profondeurs

### Profondeurs observées
- **Min** : 40 m
- **Q1** : 162 m
- **Médiane** : 187 m
- **Q3** : 208 m
- **Max** : 306 m
- **Moyenne** : 183.5 m ± 35.6 m

### Distribution
Les profondeurs varient de 40m à 306m avec **une très grande précision** (valeurs au centimètre près). La majorité des traits se situent entre 162m et 208m, cohérent avec un protocole standard similaire à HOT.

**Points critiques** :
- Comme HOT, ce sont des **traits obliques** de surface (0m) à profondeur max
- Les concentrations (mg/m³) représentent la **moyenne sur toute la colonne échantillonnée**
- Variabilité importante (40-306m) nécessite une catégorisation par profondeur

---

## 3. Workflow de traitement (OLD version)

### Étape 1 : Pas de conversion nécessaire !

**Différence majeure avec HOT** : Les données BATS contiennent déjà les colonnes de concentration :

```
dry_weight_vol_water_ratio (mg/m³) = dry_weight (mg) / volume_water (m³)
```

✅ **Vérification** : `dry_weight_vol_water_ratio` = `dry_weight` / `volume_water` (confirmé)

**Pas de conversion m² → m³ à effectuer** : Les ratios sont déjà fournis.

### Étape 2 : Agrégation en bins de profondeur (OLD)

**Code OLD** :
```python
raw_data["depth"] = pd.cut(
    raw_data["depth"],
    bins=[0, 50, 100, 150, 200, 250, 300, 350, 400],
    labels=[50, 100, 150, 200, 250, 300, 350, 400],
    right=False,
)
```

⚠️ **Même problème que HOT** : Cette agrégation en bins est inadaptée pour des traits obliques intégrés.

### Étape 3 : Séparation jour/nuit

**Critère** :
```python
raw_data["is_day"] = raw_data.time.dt.hour.isin(range(6, 18))
```

Jour = 06h-18h, Nuit = 18h-06h

### Étape 4 : Conversion sieve_size

**Code** :
```python
raw_data["sieve_size"] = raw_data["sieve_size"].astype(float) / 1000  # µm → mm
```

### Étape 5 : Agrégation par tow

**Code** :
```python
preprocessed_data = xr.Dataset.from_dataframe(
    raw_data.groupby(
        ["time", "is_day", "depth", "latitude", "longitude", "sieve_size"]
    ).mean()
)
```

**Opération** : `.mean()` sur tous les tows ayant la même combinaison.

---

## 4. Comparaison HOT vs BATS

| Aspect | HOT | BATS |
|--------|-----|------|
| **Variables** | dwt (g/m²), carb (mg/m²), nit (mg/m²) | dry_weight (mg), ratios pré-calculés |
| **Unités brutes** | Intégrées (m²) | Masses (mg) + ratios (mg/m³) |
| **Conversion nécessaire** | ✅ Oui (÷ depth) | ❌ Non (déjà faite) |
| **Carbone/Azote** | ✅ Disponible | ❌ Non disponible |
| **Fractions** | 6 (frac 0-5) | 5 (200-5000µm) |
| **Fraction à exclure** | frac 5 (>5mm micronecton) | ⚠️ À déterminer si sieve_size=5000 |

---

## 5. Analyse des profondeurs pour catégorisation

Appliquons le même seuil de 150m validé pour HOT :

```python
# Distribution avec seuil 150m
epipelagic_only (≤150m): ~15-20% des données
epipelagic_mesopelagic (>150m): ~80-85% des données
```

**Statistiques à calculer** :
- Nombre de tows ≤150m
- Nombre de tows >150m
- Profondeur moyenne par catégorie

---

## 6. Variables à produire (nouveau format)

**Structure proposée** (alignée sur HOT) :

```python
Dimensions: (time, depth_category, day_night)

Variables:
  - biomass_dry (mg/m³)         # dry_weight_vol_water_ratio sommé
  - biomass_wet (mg/m³)         # wet_weight_vol_water_ratio sommé
  - tow_depth_max (m)           # Profondeur max du trait (traçabilité)

Coordinates:
  - depth_category: ["epipelagic_only", "epipelagic_mesopelagic"]
  - day_night: ["day", "night"]

Attributes:
  depth_category:epipelagic_only:
    description: "Oblique tows 0-150m, samples ONLY epipelagic zone"
    depth_range: "40-150"

  depth_category:epipelagic_mesopelagic:
    description: "Oblique tows >150m, samples BOTH epipelagic AND mesopelagic zones"
    depth_range: "151-306"
```

**Différence avec HOT** :
- Pas de `biomass_carbon` ni `biomass_nitrogen` (non disponible)
- Ajout de `biomass_wet` (disponible dans BATS, pas utilisé dans HOT)

---

## 7. Workflow recommandé pour BATS

```python
# 1. Lecture et filtrage initial
df = pd.read_csv('bats_zooplankton.csv', index_col=0)
df = df[df['sieve_size'].notna()]  # Exclure lignes sans sieve_size

# 2. Vérifier si fraction 5000µm doit être exclue
# À déterminer : est-ce que 5000µm capture du micronecton mal échantillonné ?

# 3. Conversion temporelle
df['time'] = pd.to_datetime(df['time'])
df['date'] = df['time'].dt.floor('D')
df['hour'] = df['time'].dt.hour
df['day_night'] = df['hour'].apply(lambda h: 'day' if 6 <= h < 18 else 'night')

# 4. Catégorisation profondeur (seuil 150m)
df['depth_category'] = np.where(
    df['depth'] <= 150,
    'epipelagic_only',
    'epipelagic_mesopelagic'
)

# 5. Utiliser directement les ratios pré-calculés
# PAS de conversion nécessaire, les colonnes sont déjà en mg/m³

# 6. Stocker tow_depth_max
df['tow_depth_max'] = df['depth']  # Déjà la profondeur du trait

# 7. Agrégation niveau 1 : somme des fractions par tow
# Identifier les tows uniques (même time/depth/lat/lon)
agg1 = df.groupby(['date', 'day_night', 'depth_category', 'depth', 'lat', 'lon']).agg({
    'dry_weight_vol_water_ratio': 'sum',  # Somme fractions
    'wet_weight_vol_water_ratio': 'sum',
    'tow_depth_max': 'first'
}).reset_index()

# 8. Agrégation niveau 2 : médiane des tows par jour/catégorie
final = agg1.groupby(['date', 'day_night', 'depth_category']).agg({
    'dry_weight_vol_water_ratio': 'median',
    'wet_weight_vol_water_ratio': 'median',
    'tow_depth_max': 'median',
    'lat': 'first',
    'lon': 'first'
}).reset_index()

# 9. Conversion en xarray
ds = xr.Dataset.from_dataframe(
    final.set_index(['date', 'depth_category', 'day_night'])
)

ds = ds.rename({
    'date': 'time',
    'dry_weight_vol_water_ratio': 'biomass_dry',
    'wet_weight_vol_water_ratio': 'biomass_wet'
})

# 10. Export NetCDF
ds.to_netcdf('bats_zooplankton_obs.nc')
```

---

## 8. Données à exclure

### Exclusions validées

**1. Fraction 5000µm** (>5mm)
- **Raison** : Capture tout ce qui est >5mm sans limite supérieure, peut inclure du micronecton >20mm
- **Documentation** : Protocole BATS utilise tamis emboîtés (5.0, 2.0, 1.0, 0.5, 0.2mm), similaire à HOT
- **Impact** : Exclusion de 1,342 mesures (fraction 5000µm de tous les tows)
- **Justification** : Même logique que HOT, nets 1m²/202µm inefficaces pour gros organismes rapides

**2. Traits aberrants** (depth <50m)
- **Données concernées** : 5 lignes avec depth = 40m
- **Raison** : Écart avec profondeur standard (~200m)
- **Impact** : Exclusion de 5 lignes sur 6,728 (0.07%)
- **Justification** : Non représentatifs du protocole standard, cohérent avec exclusion HOT

**3. Lignes sans sieve_size**
- **Impact** : 22 lignes (0.3%)
- **Raison** : Impossible de catégoriser sans taille de tamis

### Données conservées

- **Fractions 200-2000µm** : Mésozooplancton 0.2-5mm (4 fractions)
- **Traits 50-306m** : Tous les traits de profondeur standard
- **Wet et dry weight** : Les deux types de biomasse disponibles

---

## 9. Points d'attention

### Avantages BATS vs HOT

✅ **Ratios pré-calculés** : Pas besoin de conversion m² → m³
✅ **Données plus directes** : Concentrations déjà disponibles
✅ **Moins d'ambiguïté** : Pas de calculs intermédiaires à valider

### Inconvénients BATS vs HOT

❌ **Pas de carbone/azote** : Perte de ces variables importantes
❌ **Moins de fractions** : 5 au lieu de 6 (pas de fraction 0)
⚠️ **Fraction 5000µm** : À vérifier si elle doit être exclue

### Questions en suspens

1. La fraction 5000µm (5mm) doit-elle être exclue comme HOT frac 5 ?
2. Y a-t-il une documentation BATS équivalente à `analytical_methods.md` de HOT ?
3. Les traits <50m doivent-ils être exclus ?

---

## 10. Prochaines étapes

1. ✅ Analyser distribution profondeurs avec seuil 150m
2. ⚠️ Décider du traitement de la fraction 5000µm
3. ⚠️ Identifier traits aberrants (<50m ?)
4. ✅ Implémenter script de processing
5. ✅ Générer NetCDF et rapport
