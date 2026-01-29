# CalCOFI Station Report

**Date**: 2026-01-29 19:29:17
**Region**: California Current System (0.0-54.3°N, -179.8--77.7°E)

## Summary

- Initial rows: 45,310
- Final observations: 32,737
- Unique tows: 28,142
- Period: 1951-01-09 to 2023-01-25
- Spatial cells (1°): 965

### Exclusions

- small_plankton NaN: 0 rows
- small_plankton ≤ 0: 0 rows

### Depth Protocol

- 140m protocol (≤1968): 23594 tows
- 210m protocol (>1968): 21716 tows
- All tows: epipelagic_only (<200m)

### Biomass Statistics

| Metric | Mean | Median | Min | Max |
|--------|------|--------|-----|-----|
| Carbon Biomass (mg C/m³) | 4.68 | 3.39 | 0.19 | 101.39 |

## Figures

![Map](figures/map.png)

![Time Series](figures/time_series_biomass.png)

## Methodology

**Conversion Method**: Lavaniegos & Ohman (2007)

**Formula**: `log10(C) = 0.6664 × log10(DV) + 1.9997`

where C = Carbon biomass (mg C/m²), DV = Displacement Volume (ml/m²)

**Source Variable**: small_plankton (organisms with individual DV <5ml)

**Spatial Resolution**: 1° grid

**Aggregation**:
1. Average biomass per tow
2. Median of tows per day/depth_category/spatial_cell

## Points d'attention et biais potentiels

### 1. Changement de protocole de profondeur (1969)

- **Avant 1969** : Profondeur standard 140m
- **Après 1968** : Profondeur standard 210m
- **Impact** : Différence de volume échantillonné et de couverture verticale. Les traits post-1968 intègrent une partie de la zone mésopélagique (150-210m), potentiellement incluant des organismes non capturés avant 1969.
- **Mitigation** : Conversion en concentration volumique (mg/m³) normalise partiellement l'effet, mais la composition taxonomique peut différer.

### 2. Conversion non-linéaire Lavaniegos & Ohman (2007)

- **Formule empirique** : Basée sur des échantillons CalCOFI (1951-2005)
- **Relation log-log** : Amplification des incertitudes pour les faibles et fortes valeurs
- **Limites de validité** : Formule calibrée sur le système California Current, extrapolation à d'autres régions non validée
- **Incertitude** : Pas d'intervalle de confiance publié pour la formule

### 3. Restriction aux petits organismes (small_plankton)

- **Seuil** : Organismes avec volume individuel <5ml
- **Exclus** : Grands organismes gélatineux (méduses, salpes), euphausiacés adultes, larves de poissons de grande taille
- **Justification** : Cohérence avec HOT/BATS (fraction <5mm), capture hétérogène des grands organismes par les filets standards
- **Impact** : Sous-estimation de la biomasse totale, mais meilleure cohérence inter-stations

### 4. Agrégation spatiale (1° × 1°)

- **Résolution** : Grille 1° (~111km à l'équateur)
- **Justification** : Couverture spatiale large (0-54°N, -180 à -78°W), hétérogénéité des stations
- **Impact** : Lissage des variations locales, perte de résolution côtière
- **Cellules** : 965 cellules uniques sur la période 1951-2023

### 5. Classification jour/nuit

- **Méthode** : Calcul astronomique (lever/coucher soleil) via bibliothèque `astral`
- **Avantage** : Précision basée sur position géographique et date réelles
- **Attention** : Gestion des timezones (UTC vs local) et wrap-around jour suivant
- **Distribution observée** : 22572 jour (49.8%) vs 22738 nuit (50.2%)

### 6. Absence d'exclusions par profondeur/maille

- **Aucune exclusion** : Contrairement à HOT/BATS (traits <50m exclus), tous les traits CalCOFI sont conservés
- **Raison** : Protocole standardisé CalCOFI (140m/210m), pas de traits aberrants détectés
- **Maille** : Variable selon période (majoritairement 202-333µm)

### 7. Couverture temporelle et spatiale

- **Période** : 1951-2023 (72 ans)
- **Échantillonnage** : Irrégulier dans le temps et l'espace (campagnes opportunistes)
- **Biais géographique** : Concentration des observations près des côtes californiennes
- **Biais saisonnier** : À vérifier (campagnes potentiellement concentrées sur certaines saisons)

