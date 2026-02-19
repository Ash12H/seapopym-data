# Canary Current System Report

**Date**: 2026-02-19 10:51:57
**Location**: Canary Islands region (28°N, -16°W)

## Summary

- Initial rows: 1,970
- Final rows: 969
- Period: 1971-01-31 to 2021-03-31

### Exclusions

- No exclusions applied (all size fractions ≤250µm)

## Figures

![Map](figures/map.png)

![Time Series](figures/time_series_biomass.png)

## Methodology

**Sampling Method**: Oblique tows from surface to 200m depth

**Nets**: WP-2 (92%), LHPR (6%), Juday Bogorov (1%)

**Size Fractions**: >200µm (98.4%), >250µm (1.3%)

**Unit Conversion**: mg C/m² → mg C/m³ (division by 200m depth)

**Spatial Resolution**: 1° grid

**Aggregation**:
1. Median biomass per date/spatial_cell/depth_category/day_night

## Biomass Statistics

| Metric | Mean | Median | Min | Max |
|--------|------|--------|-----|-----|
| Carbon Biomass (mg C/m³) | 1.94 | 1.54 | 0.06 | 31.19 |

## Points d'attention et biais potentiels

### 1. Multi-sources (compilation 50 ans)

- **Type** : Compilation de ~30 publications scientifiques (1971-2021)
- **Avantage** : Couverture temporelle exceptionnelle, série temporelle longue
- **Limitation** : Hétérogénéité méthodologique entre études, protocoles variables
- **Impact** : Variable `reference` permet traçabilité, mais comparabilité inter-études limitée

### 2. Hétérogénéité des filets

- **WP-2** : 1821 obs (92%)
- **LHPR** : 123 obs (6%)
- **Juday Bogorov** : 26 obs (1%)
- **Impact** : Efficacité de capture variable selon le filet, biais potentiel sur composition taxonomique
- **Mitigation** : Variable `net_type` permet filtrage a posteriori, WP-2 dominant garantit cohérence majoritaire

### 3. Conversion mg C/m² → mg C/m³

- **Formule** : biomass_carbon = biomass_carbon_m² / 200
- **Hypothèse** : Distribution verticale uniforme du zooplancton sur 0-200m
- **Réalité** : Distribution hétérogène (thermocline, DCM, migrations verticales)
- **Impact** : Approximation acceptable pour comparaisons régionales, mais surestimation possible dans couches profondes, sous-estimation en surface
- **Cohérence** : Conversion nécessaire pour compatibilité avec HOT/BATS/PAPA/CalCOFI (mg C/m³)

### 4. Profondeur fixe (0-200m)

- **Profondeur** : Tous les traits à 0-200m (métadonnées PANGAEA)
- **Limitation** : Pas d'information sur variabilité réelle des profondeurs de trait
- **Différence HOT/BATS** : HOT/BATS ont profondeurs variables (50-268m), Canaries homogène
- **Impact** : Meilleure homogénéité inter-observations, mais zone mésopélagique (>200m) non échantillonnée

### 5. Fractions de taille

- **>200µm** : 1944 obs (98.4%)
- **>250µm** : 26 obs (1.3%)
- **Cohérence** : Pas de fraction >5mm détectée, cohérent avec autres stations (exclusion >5mm)
- **Impact** : Homogénéité de taille, pas de biais majeur lié aux grandes fractions

### 6. Zones géographiques agrégées

- **Area_1 (North)** : 278 obs
- **Area_2 (South/Islands)** : 1517 obs
- **Area_3 (Upwelling)** : 175 obs
- **Agrégation** : Les 3 zones sont fusionnées dans le dataset final
- **Impact** : Perte d'information spatiale fine, lissage des gradients océanographiques (upwelling vs gyre)
- **Mitigation** : Variable `area_original` conserve traçabilité

### 7. Agrégation spatiale (1° × 1°)

- **Résolution** : Grille 1° (~111km à l'équateur)
- **Cellules** : 44 cellules uniques
- **Justification** : Couverture spatiale large (Canaries + NW Afrique), hétérogénéité multi-sources
- **Impact** : Lissage variations locales, masquage structures méso-échelle (filaments, tourbillons)

### 8. Pas d'exclusions

- **Aucune exclusion** : Contrairement à HOT/BATS (traits <50m exclus), toutes obs conservées
- **Raison** : Profondeur documentée homogène (0-200m), pas de traits aberrants détectés
- **Impact** : Maximisation des données disponibles, mais risque d'inclure obs de faible qualité

### 9. Classification jour/nuit

- **Méthode** : Calcul astronomique (lever/coucher soleil) via bibliothèque `astral`
- **Avantage** : Précision basée sur position géographique et date réelles
- **Attention** : Canaries (~28°N, -16°W) proche de UTC, pas de wrap-around significatif
- **Distribution observée** : 1601 jour (81.3%) vs 364 nuit (18.5%)

### 10. Couverture temporelle et spatiale

- **Période** : 1971-2021 (50 ans)
- **Échantillonnage** : Irrégulier, opportuniste selon publications
- **Biais temporel** : Concentration possibles sur certaines périodes (campagnes intensives)
- **Biais spatial** : Concentration autour des Canaries, couverture NW Afrique plus sparse

