# Analyse de traitement : Station HOT (Hawaii Ocean Time-series)

**Date d'analyse** : 2026-01-28
**Version analysée** : OLD_src/hot
**Période des données** : 1994-02-17 à 2022-09-02
**Sources** : HOT-DOGS database + HOT Analytical Methods documentation

---

## Note importante : Analyse révisée

**Mise à jour après lecture des méthodes analytiques HOT** :

Suite à l'ajout du document `analytical_methods.md`, plusieurs points de l'analyse initiale ont été **corrigés et précisés** :

✅ **Confirmé** :
- Tailles de maille exactes des fractions 0-5 : 200µm, 500µm, 1mm, 2mm, 5mm, >5mm
- Justification de l'exclusion de fraction 5 (micronecton mal échantillonné)
- Formules de calcul de biomasse par m² avec facteurs de normalisation

🔄 **Clarifié** :
- Nature des unités en m² : normalisation par **surface horizontale balayée**, pas intégration verticale simple
- Le facteur `depth` dans les formules sert à calculer la surface balayée pendant le trait oblique
- La conversion m² → m³ est mathématiquement correcte et donne une **concentration moyenne** sur la colonne 0-depth

❌ **Problème identifié** :
- L'agrégation en bins de profondeur (0-50m, 50-100m, etc.) est **inadaptée** pour des traits obliques intégrés
- Ces bins n'ont pas de sens physique car chaque trait échantillonne toute la colonne d'eau
- Cette étape devrait être **supprimée** ou remplacée par un regroupement par plage de profondeur de trait

---

## 1. Méthodes d'échantillonnage (HOT Analytical Methods)

### Protocole de terrain
- **Net** : 1 m² avec maille 202 µm (Nitex)
- **Type de trait** : Oblique, surface → ~175m → surface (~20-30 min à 1 nœud)
- **Fréquence** : 6 tows par cruise (3 jour + 3 nuit)
- **Instruments** :
  - Flowmètre (General Oceanics 2030R) pour volume filtré
  - Capteur température-pression pour profondeur du trait

### Traitement post-prélèvement
1. **Division** : 1/2 du tow préservé au formaldéhyde, 1/4 fractionné pour biomasse
2. **Fractionnement** : Passage à travers tamis emboîtés (5mm, 2mm, 1mm, 500µm, 200µm)
3. **Congélation** : Chaque fraction sur filtre Nitex 47mm pré-pesé, congelée à -85°C

### Analyses de masse
- **Poids humide** (wwt) : Pesée après décongélation et absorption de l'excès d'humidité
- **Poids sec** (dwt) : Séchage à 60°C puis pesée
- **Carbone et Azote** (carb, nit) : Analyseur élémentaire CHN (Perkin Elmer 2400) sur sous-échantillon séché

### Calculs de biomasse
**Formule pour dwt, carb, nit par m²** :
```
mg m⁻² = masse_mesurée (mg) × depth (m) / [volume_filtered (m³) × fraction_of_tow]
```

**Normalisation** : Les valeurs en mg/m² représentent la biomasse normalisée par la **surface horizontale** balayée par le filet durant le trait oblique, pas une simple intégration verticale.

---

## 2. Description des données brutes

### Format initial
- **Fichier** : `1_raw/hot_zooplankton.csv`
- **Source** : Hawaii Ocean Time-series (HOT-DOGS) - tblHOT_Macrozooplankton_v2022
- **Nombre d'enregistrements** : 9,348 lignes (1,558 tows × 6 fractions)
- **Position** : Station fixe ALOHA (22.75°N, -158°W)

### Variables disponibles

| Variable | Unité initiale | Description | Couverture |
|----------|---------------|-------------|------------|
| `abnd` | #/m² | Abundance | 856/9348 (9%) |
| `wwt` | g/m² | Wet Weight (Poids humide) | 8682/9348 (93%) |
| `dwt` | g/m² | Dry Weight (Poids sec) | 9264/9348 (99%) |
| `carb` | mg/m² | Carbon (Carbone) | 7833/9348 (84%) |
| `nit` | mg/m² | Nitrogen (Azote) | 7833/9348 (84%) |
| `svol` | ml/m³ | Settled Volume | 348/9348 (4%) |
| `vol` | m³ | Volume filtré | 9348/9348 (100%) |

### Structure des prélèvements

**Méthode** :
- Net oblique de 1 m² avec maille de 202 µm
- Trait vertical : surface → ~175m → surface
- 6 tows par cruise : 3 de jour (10h-14h) et 3 de nuit (22h-02h)

**Fractionnement par taille** :
- Généralement **1/4 du tow** est fractionné à travers des tamis emboîtés
- Chaque tow produit **6 fractions** (frac 0-5) selon la taille retenue :

| Fraction | Taille de maille | Type d'organismes |
|----------|------------------|-------------------|
| 0 | 200 µm (0.2 mm) | Petits copépodes, nauplii |
| 1 | 500 µm (0.5 mm) | Copépodes moyens |
| 2 | 1000 µm (1 mm) | Gros copépodes |
| 3 | 2000 µm (2 mm) | Petits euphausiacés, chaetognathes |
| 4 | 5000 µm (5 mm) | Grands euphausiacés |
| 5 | >5 mm | Micronecton (non capturé efficacement) |

**Formules de calcul de biomasse** (d'après méthodes analytiques HOT) :

**Biomasse par m² (surface horizontale)** :
```
mg (dry wt.) m⁻² = dwt₁ × depth × (volume filtered)⁻¹ × (fraction of tow)⁻¹
```

Où :
- `dwt₁` = poids sec de la fraction (mg)
- `depth` = profondeur du trait (m) depuis le capteur de pression
- `volume filtered` = volume d'eau filtré (m³) depuis le flowmètre
- `fraction of tow` = fraction du tow analysée (typiquement 1/4)

**Note critique** : Les unités en m² représentent une **normalisation par surface horizontale** balayée par le filet, PAS une intégration verticale simple. Le facteur `depth` sert à calculer la surface balayée pendant le trait oblique.

---

## 3. Distribution des profondeurs

### Profondeurs observées
- **Min** : 9 m
- **Médiane** : 167 m
- **Moyenne** : 165.9 m ± 37.6 m
- **Max** : 271 m
- **Quartiles** : Q1=140m, Q3=192m

### Distribution
Les profondeurs sont très **hétérogènes** avec 184 valeurs uniques entre 9m et 271m. La majorité des traits se situent entre 140m et 192m, ce qui correspond approximativement à la profondeur d'échantillonnage nominale de 175m.

**Points critiques** :
- Les profondeurs varient significativement entre les tows (9-271m)
- Cette variabilité rend difficile la comparaison directe des biomasses intégrées
- La conversion en concentration volumique (g/m³) est nécessaire pour standardiser

---

## 4. Workflow de traitement (OLD version)

### Étape 1 : Conversion des unités (m² → m³)

**Transformation appliquée** :
```python
for var in ["wwt", "dwt", "carb", "nit", "abnd"]:
    raw_data[var] = raw_data[var] / raw_data["depth"]
```

**Explication de la conversion** :

Les données brutes sont en g/m² ou mg/m² (biomasse normalisée par surface horizontale). Pour obtenir une concentration volumique (g/m³ ou mg/m³), on divise par la profondeur du trait :

```
Concentration (mg/m³) = Biomasse surfacique (mg/m²) / Profondeur (m)
```

**Équivalence mathématique** :
```
mg/m² / m = mg/m³
```

Cette conversion permet de comparer des traits de profondeurs différentes en ramenant tout à une concentration volumique moyenne.

⚠️ **Hypothèse sous-jacente** : Cette conversion suppose que le zooplancton est **uniformément réparti** sur toute la colonne d'eau échantillonnée (0 à depth). C'est une **simplification** car :
1. Le zooplancton a souvent une distribution verticale hétérogène (layers, thermocline, etc.)
2. Les traits obliques ne capturent pas de manière uniforme chaque profondeur
3. La concentration calculée est une **moyenne** sur toute la colonne, pas la concentration à une profondeur donnée

**Justification du choix** : Sans données de profil vertical détaillé, c'est la meilleure approximation possible pour standardiser des traits de profondeurs variables.

### Étape 2 : Agrégation en bins de profondeur

**Bins appliqués** :
```python
bins=[0, 50, 100, 150, 200, 250, 300, 350, 400]
labels=[50, 100, 150, 200, 250, 300, 350, 400]
```

**Résultat** : Les profondeurs continues (9-271m) sont regroupées en 8 classes de 50m.

⚠️ **Compromis** : Cette agrégation perd la précision des profondeurs réelles mais permet de standardiser les données.

### Étape 3 : Séparation jour/nuit

**Critère** :
```python
raw_data["is_day"] = raw_data.time.dt.hour.isin(range(6, 18))
```

Jour = 06h-18h, Nuit = 18h-06h

**Distribution observée** :
- Nuit (22h-02h) : ~3,800 mesures
- Jour (10h-14h) : ~4,600 mesures

### Étape 4 : Agrégation par tow

**Problème identifié** : Plusieurs tows peuvent avoir lieu le même jour à la même profondeur, créant des duplicatas d'index.

**Solution appliquée** :
```python
preprocessed_data = xr.Dataset.from_dataframe(
    raw_data.groupby(["time", "is_day", "lat", "lon", "depth", "frac"]).mean()
)
```

**Opération** : `mean()` sur tous les tows ayant la même combinaison (time, is_day, depth, frac).

⚠️ **Point critique** : L'utilisation de `.mean()` suppose que tous les tows d'un même jour/profondeur/fraction sont équivalents. Si un tow est de moins bonne qualité, il impacte la moyenne.

### Étape 5 : Suppression de la fraction 5

**Code** :
```python
preprocessed_data = preprocessed_data.where(
    preprocessed_data.frac != 5, drop=True
).assign_coords({"frac": [0.2, 0.5, 1, 2, 5]})
```

**Résultat** : La fraction 5 (>5mm) est **supprimée**.

✅ **Justification (d'après méthodes analytiques)** :
- La fraction 5 capture du **micronecton** (>5mm), pas du mésozooplancton
- Les méthodes HOT indiquent explicitement : *"Since even very large, fast-towed nets [...] are unlikely to sample micronekton quantitatively, neither of the small HOT nets is assumed to capture this fraction well."*
- Les nets de 1m² avec maille 202µm ne sont **pas adaptés** pour capturer efficacement les grands organismes rapides
- La biomasse mesurée dans frac=5 est donc **non représentative** et sous-estime fortement le micronecton réel

**Conclusion** : L'exclusion de frac=5 est **justifiée** car elle éliminerait un biais négatif (sous-estimation systématique du micronecton). Pour SEAPODYM, on se concentre sur le **mésozooplancton** (0.2-5mm) qui est correctement échantillonné.

### Étape 6 : Produit final (release)

**Agrégations supplémentaires** :
1. **Somme des fractions** : `sum("sieve_size")` → perte de la résolution par taille
2. **Moyenne des profondeurs** : `mean("depth")` → intégration verticale
3. **Conversion en mg/m³** :
```python
zoo_hot = zoo_hot.pint.quantify(hot_units).pint.to("mg/m^3").pint.dequantify()
```

⚠️ **Formules de conversion appliquées** :
- `g/m³ → mg/m³` : multiplication par 1000

**Produit final** :
- Deux variables : `day` et `night` (mg/m³)
- Une seule profondeur (layer=0, epipelagic)
- Série temporelle de 548 dates (1994-2022)

---

## 5. Synthèse des choix et compromis

### Choix validés ✓
1. **Conversion m² → m³** : Nécessaire et correcte pour comparer des traits de profondeurs variables
2. **Séparation jour/nuit** : Pertinent pour capturer les migrations verticales
3. **Agrégation temporelle à la journée** : Cohérent avec la fréquence d'échantillonnage (6 tows/cruise)
4. **Exclusion de frac=5** : Justifiée car le net n'échantillonne pas efficacement le micronecton (>5mm)
5. **Conservation de fracs 0-4** : Couvre le mésozooplancton (0.2-5mm) correctement échantillonné

### Points discutables ⚠️

| Choix | Impact | Alternative possible |
|-------|--------|---------------------|
| **Division par profondeur** | Suppose distribution uniforme | Sans alternative simple avec trait oblique intégré |
| **Bins de 50m** | Perte de résolution + bins inadaptés | ⚠️ Problématique (voir ci-dessous) |
| **mean() sur tows** | Peut diluer signal/bruit | ✅ Utiliser median() à la place |
| **Moyenne sur profondeur** | Perte totale de structure verticale | ⚠️ Problématique (voir ci-dessous) |
| **Somme des fractions** | Perte de la distribution de taille | ✅ Acceptable pour produit simplifié |

### Problèmes identifiés 🔴

**1. Agrégation en bins de 50m inadaptée**

Le code crée des bins [0-50m, 50-100m, ..., 350-400m] mais :
- Les traits obliques échantillonnent **toute la colonne** 0→depth→0
- Attribuer un trait de 175m au bin "200m" n'a **pas de sens physique**
- Cette étape ne devrait **pas exister** pour des traits obliques intégrés

**Recommandation** : Supprimer complètement cette étape. La profondeur du trait est déjà utilisée pour la normalisation (conversion en m³), elle ne doit pas servir à découper en layers.

**2. Sur-simplification verticale finale**

Le produit final moyenne toutes les profondeurs (`mean("depth")`) en une seule variable par période jour/nuit. Cela signifie qu'un trait de 50m et un trait de 250m sont moyennés ensemble, ce qui mélange des écosystèmes différents (épipélagique vs mésopélagique).

**Recommandation** : Soit conserver les profondeurs individuelles des traits, soit filtrer pour ne garder qu'une plage cohérente (ex: 150-200m).

---

## 6. Recommandations pour le nouveau workflow

### Profondeur

**Comprendre la nature des données** :
- Les traits obliques échantillonnent **toute la colonne d'eau** de 0 à depth
- La conversion en mg/m³ donne une **concentration moyenne** sur cette colonne
- On ne peut PAS découper artificiellement en layers 0-100m, 100-200m

**Propositions** :

**Option 1 : Regrouper par plage de profondeur de trait**
- **Shallow** : traits de 100-150m → représentent l'épipélagique
- **Deep** : traits de 150-200m → représentent épipélagique + début mésopélagique

**Option 2 : Standardiser sur une profondeur unique**
- Filtrer pour ne garder que les traits dans une plage homogène (ex: 150-200m)
- Sacrifie des données mais améliore la cohérence

**Option 3 : Pondération par profondeur (avancée)**
- Utiliser des profils verticaux moyens de zooplancton pour déconvoluer les traits obliques
- Nécessite des données additionnelles (profils CTD, profils verticaux publiés)

### Fractions de taille
**Choix validé** : **Pas de différenciation par classe de taille**
- Somme des fractions 0-4 (0.2-5mm) → mésozooplancton total
- Exclusion de fraction 5 (>5mm, micronecton mal échantillonné)

Cela simplifie le produit final et évite d'introduire une complexité non nécessaire pour SEAPODYM.

### Types de biomasse
**Conserver les 3 types** séparés :
- `biomass_dry` (dwt) : couverture 99%
- `biomass_carbon` (carb) : couverture 84%
- `biomass_nitrogen` (nit) : couverture 84%

**Formules de conversion** (si nécessaires) :
- Ratio C:N observé ≈ 4.2:1 (d'après les stats du metadata)
- Ratio DW:C ≈ 3:1 (d'après dwt_mean/carb_mean)

### Agrégation des tows
**Proposition** : Utiliser `.median()` au lieu de `.mean()` pour être plus robuste aux outliers.

---

## 7. Variables à produire (nouveau format)

**Structure finale validée** (seuil à 150m) :

```python
Dimensions: (time, latitude, longitude, depth_category, day_night)

Variables:
  - biomass_dry (mg/m³)          # Poids sec, somme fractions 0-4
  - biomass_carbon (mg/m³)       # Carbone, somme fractions 0-4
  - biomass_nitrogen (mg/m³)     # Azote, somme fractions 0-4
  - tow_depth_max (m)            # Profondeur max du trait (traçabilité)

Coordinates:
  - depth_category: ["epipelagic_only", "epipelagic_mesopelagic"]

  - day_night: ["day", "night"]

Attributes:
  depth_category:epipelagic_only:
    description: "Oblique tows 0-150m, samples ONLY epipelagic zone"
    depth_range: "9-150"
    n_tows: 540
    mean_tow_depth: 125.1
    sampled_zones: "epipelagic (0-150m)"

  depth_category:epipelagic_mesopelagic:
    description: "Oblique tows >150m, samples BOTH epipelagic AND mesopelagic zones"
    depth_range: "151-271"
    n_tows: 1018
    mean_tow_depth: 187.5
    sampled_zones: "epipelagic (0-150m) + mesopelagic (150-depth_max)"
```

**⚠️ POINT CRITIQUE : Nature des traits obliques**

Tous les traits sont obliques de **surface (0m) à profondeur max**, puis retour. Cela signifie :

1. **Traits ≤150m** (`epipelagic_only`) :
   - Échantillonnent **UNIQUEMENT** l'épipélagique (0-150m)
   - Concentration moyenne = biomasse moyenne sur zone épipélagique uniquement

2. **Traits >150m** (`epipelagic_mesopelagic`) :
   - Échantillonnent **ÉPIPÉLAGIQUE + MÉSOPÉLAGIQUE** (0 jusqu'à depth_max)
   - Concentration moyenne = biomasse moyenne sur **toute la colonne** 0-depth_max
   - ⚠️ Ne représente PAS seulement le mésopélagique, mais un **mélange des deux zones**

**Exemple** : Un trait de 200m donne une concentration moyenne sur 0-200m, incluant ~75% d'épipélagique (0-150m) et ~25% de mésopélagique (150-200m).

**Justification du seuil 150m** :
- Cohérent avec définition océanographique (zone épipélagique 0-150/200m)
- Proche de la profondeur nominale HOT (~175m)
- Répartition équilibrée : 35% / 65%
- Permet de distinguer les traits purement épipélagiques des traits mixtes

---

## 8. Données à exclure

### Exclusions justifiées

**1. Fraction 5** (>5mm, micronecton)
- **Raison** : Les nets de 1m² avec maille 202µm ne capturent pas efficacement le micronecton
- **Impact** : Exclusion de 1,558 mesures (fraction 5 de tous les tows)
- **Justification** : Documenté dans les méthodes analytiques HOT

**2. Traits aberrants** (depth <50m)
- **Données concernées** :
  - Tow 48 (1995-02-05) : 17m, vol=1043m³
  - Tow 386 (2000-03-28) : 9m, vol=655m³
- **Raison** : Écart de >10× avec profondeur standard (~175m)
- **Impact** : Exclusion de 2 tows sur 1,558 (0.13%)
- **Justification** :
  - Profondeur nominale HOT = ~175m (protocole standard)
  - Médiane observée = 167m
  - Ces 2 traits (9m et 17m) sont probablement issus d'incidents techniques, de conditions météo défavorables, ou d'erreurs de saisie
  - Non représentatifs de l'écosystème pélagique échantillonné habituellement
  - Impact négligeable sur le dataset final (<0.2% des données)

**3. Valeurs aberrantes** (biomasse)
- À identifier lors du processing via percentiles (ex: biomass > Q3 + 3×IQR)
- Traitement au cas par cas

### Données conservées

- **Traits >200m** (17% des données) : Conservés dans la catégorie `epipelagic_mesopelagic`
- **Toutes les fractions 0-4** : Sommées pour biomasse totale du mésozooplancton (0.2-5mm)

---

## 9. Résumé des transformations à appliquer

### Workflow recommandé pour HOT

```python
# 1. Lecture et filtrage initial
df = pd.read_csv('hot_zooplankton.csv')
df = df[df['depth'] >= 50]  # Exclure traits aberrants <50m
df = df[df['frac'] <= 4]     # Exclure fraction 5 (micronecton)

# 2. Conversion temporelle
df['time'] = pd.to_datetime(df['time']).dt.floor('D')
df['day_night'] = df['time'].dt.hour.isin(range(6, 18)).map({True: 'day', False: 'night'})

# 3. Conversion m² → m³
for var in ['dwt', 'carb', 'nit']:
    df[var] = df[var] / df['depth']  # g/m³ ou mg/m³

# 4. Catégorisation profondeur
df['depth_category'] = np.where(df['depth'] <= 150,
                                 'epipelagic_only',
                                 'epipelagic_mesopelagic')

# 5. Stocker tow_depth_max avant agrégation
df['tow_depth_max'] = df.groupby('tow')['depth'].transform('first')

# 6. Agrégation niveau 1 : somme des fractions 0-4 par tow
agg1 = df.groupby(['time', 'day_night', 'depth_category', 'tow']).agg({
    'dwt': 'sum',           # Somme des fractions pour biomasse totale
    'carb': 'sum',
    'nit': 'sum',
    'tow_depth_max': 'first'
}).reset_index()

# 7. Agrégation niveau 2 : médiane des tows d'un même jour/catégorie
final = agg1.groupby(['time', 'day_night', 'depth_category']).agg({
    'dwt': 'median',
    'carb': 'median',
    'nit': 'median',
    'tow_depth_max': 'median'
}).reset_index()

# 8. Conversion en xarray et export NetCDF
ds = xr.Dataset.from_dataframe(final.set_index(['time', 'depth_category', 'day_night']))
ds['biomass_dry'] = ds['dwt'] * 1000  # g/m³ → mg/m³
ds['biomass_carbon'] = ds['carb']      # déjà en mg/m³
ds['biomass_nitrogen'] = ds['nit']     # déjà en mg/m³

# Ajouter métadonnées
ds.attrs['station'] = 'HOT'
ds.attrs['location'] = 'Station ALOHA (22.75°N, -158°W)'
ds.attrs['sampling_method'] = 'Oblique tows from surface to max depth and back'
ds.attrs['mesh_size'] = '202 µm'
ds.attrs['size_range'] = '0.2-5 mm (mesozooplankton, fractions 0-4)'

ds.to_netcdf('hot_zooplankton_obs.nc')
```

### Points clés
- ✅ Pas de différenciation par classe de taille (somme fractions 0-4)
- ✅ Pas d'agrégation en bins de profondeur artificiels
- ✅ Catégorisation basée sur la profondeur réelle du trait (≤150m vs >150m)
- ✅ Conservation de `tow_depth_max` pour traçabilité
- ✅ Utilisation de `sum()` pour les fractions, puis `median()` pour les tows
- ✅ Nommage explicite : `epipelagic_only` vs `epipelagic_mesopelagic`
- ✅ 2 niveaux d'agrégation : fractions → tows → jour/catégorie

### ⚠️ Interprétation des données

**Important pour l'analyse** : La catégorie `epipelagic_mesopelagic` (traits >150m) ne représente **PAS** uniquement le mésopélagique, mais une **concentration moyenne sur toute la colonne échantillonnée** (0 à depth_max), incluant majoritairement de l'épipélagique.

Pour un trait de 200m par exemple :
- 75% de la colonne = épipélagique (0-150m)
- 25% de la colonne = mésopélagique (150-200m)

La biomasse mesurée est donc dominée par le signal épipélagique.
