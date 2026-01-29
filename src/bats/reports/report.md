# BATS Station Report

**Date**: 2026-01-29 19:31:56
**Location**: 31.6°N, -64.2°W

## Summary

- Initial rows: 6,728
- Final rows: 663
- Period: 1995-05-10 to 2022-12-13

### Exclusions

- Depth <50m: 5 rows
- Sieve 5000µm: 1341 rows
- Missing sieve: 22 rows

## Figures

![Map](figures/map.png)

![Time Series](figures/time_series_biomass.png)

## Methodology

**Sampling Method**: Double oblique tows (surface → ~200m → surface, ~30 min)

**Net**: 1 m² rectangular with 202 µm mesh

**Size Fractions**: Wet sieving through nested sieves (5.0, 2.0, 1.0, 0.5, 0.2 mm)

**Fractions analyzed**: 200µm, 500µm, 1mm, 2mm (excluding 5mm)

**Aggregation**:
1. Sum of size fractions per tow
2. Median of tows per day/depth_category/day_night

## Points d'attention et biais potentiels

### 1. Station fixe unique

- **Type** : Station BATS (~31.6°N, -64.2°W)
- **Avantage** : Séries temporelles sans confondant spatial, protocole standardisé
- **Limitation** : Représentativité régionale limitée au gyre subtropical Nord-Atlantique
- **Impact** : Excellente pour tendances temporelles, comparaisons inter-bassins nécessitent prudence

### 2. Fractionnement par taille

- **Méthode** : 5 tamis emboîtés (5.0, 2.0, 1.0, 0.5, 0.2 mm)
- **Fractions** : 200µm (0.2-0.5mm), 500µm (0.5-1mm), 1mm (1-2mm), 2mm (2-5mm), 5mm (>5mm)
- **Somme** : Fractions 200-2000µm uniquement
- **Avantage** : Information sur structure de taille
- **Différence HOT** : Pas de fraction <200µm (HOT a fraction 0)

### 3. Exclusion de la fraction 5000µm (>5mm)

- **Exclus** : 1341 observations (fraction >5mm)
- **Justification** : Capture tout ce qui est >5mm sans limite supérieure, inclut potentiellement du micronecton >20mm mal échantillonné par filet 1m²/202µm
- **Organismes concernés** : Grands euphausiacés, méduses, larves de poissons
- **Impact** : Sous-estimation de la biomasse totale, cohérence avec définition zooplancton <5mm et avec HOT/PAPA/CalCOFI

### 4. Exclusion des traits aberrants (<50m)

- **Exclus** : 5 traits avec profondeur <50m
- **Justification** : Écart majeur avec protocole standard (~200m)
- **Impact** : Amélioration cohérence, perte d'info sur conditions difficiles

### 5. Exclusion des lignes sans sieve_size

- **Exclus** : 22 lignes sans information de tamis
- **Justification** : Impossible de catégoriser par taille sans cette information
- **Impact** : Perte minime ({len(excluded_no_sieve)/initial_rows*100:.1f}% des données)

### 6. Variabilité des profondeurs de trait

- **Profondeur médiane** : 187m
- **Variabilité** : 50-306m (écart-type 35m)
- **Protocole standard** : ~200m (double oblique)
- **Impact** : Variabilité de profondeur affecte volume échantillonné et couverture verticale
- **Mitigation** : Données pré-normalisées en mg/m³ (concentration volumique), catégorisation ≤150m vs >150m

### 7. Concentrations pré-calculées

- **Avantage** : Variables `*_vol_water_ratio` déjà en mg/m³ dans les données brutes
- **Différence HOT** : Pas de conversion m² → m³ nécessaire (HOT fournit mg/m²)
- **Validation** : Ratios vérifiés = poids / volume d'eau filtré
- **Impact** : Moins d'étapes de traitement, moins d'erreurs potentielles

### 8. Absence de données carbone/azote

- **Limitation** : Seulement poids sec et poids humide disponibles
- **Différence HOT** : HOT fournit C et N, permet calculs stoechiométriques
- **Impact** : Comparaisons avec HOT limitées à la biomasse sèche
- **Note** : C et N mesurés 1994-1998 uniquement (4 cruises/an), non exploité ici

### 9. Classification jour/nuit

- **Méthode** : Heure locale simple (06h-18h = jour, 18h-06h = nuit)
- **Simplicité** : Reproductible, cohérent avec HOT
- **Limitation** : Pas de correction saisonnière du lever/coucher du soleil
- **Distribution observée** : 0.0% jour vs 100.0% nuit

### 10. Protocole d'échantillonnage

- **Fréquence** : 2 réplicats jour (09h-15h) et 2 réplicats nuit (20h-02h) par cruise
- **Réplicats** : Permet estimation variabilité intra-journalière
- **Agrégation** : Médiane des réplicats par jour/catégorie

### 11. Couverture temporelle

- **Période** : 1995-2022 (28 ans)
- **Fréquence** : Variable selon périodes
- **Gaps** : À documenter (problèmes logistiques, météo)

