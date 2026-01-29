# Workflow State - CalCOFI Zooplankton Processing

## Informations générales

- **Projet** : CalCOFI Zooplankton Data Processing
- **Étape courante** : 8. Test
- **Rôle actif** : Testeur
- **Dernière mise à jour** : 2026-01-29

---

## Résumé du besoin

Convertir les volumes de déplacement CalCOFI (ml/1000m³) en biomasse carbone (mg C/m³) en utilisant la formule de Lavaniegos & Ohman (2007), aligné avec le pattern des autres stations (HOT, BATS, PAPA).

**Formule** : `log10(C) = 0.6664 × log10(DV) + 1.9997`

**Spécificités CalCOFI** :
- Profondeur fixe par protocole : 140m (≤1968), 210m (>1968)
- Variable source : `small_plankton` (exclut organismes >5ml DV)
- Grille spatiale : 1° (couverture large, multi-stations)
- Classification jour/nuit : via `astral` (lever/coucher soleil réel)

---

## Rapport d'analyse

[Section identique, conservée pour référence...]

---

## Décisions d'architecture

[Section identique, conservée pour référence...]

---

## Todo List

| État | ID | Nom | Description | Dépendances | Résolution |
|------|-----|-----|-------------|-------------|------------|
| ☑ | T1 | Ajouter dépendance astral | Ajouter `astral>=3.2` dans `pyproject.toml` | - | Dépendance ajoutée en tête de liste |
| ☑ | T2 | Définir chemins et imports | Réécrire section PATHS dans `process.py` avec chemins CalCOFI | - | Chemins définis (RAW_DIR, RELEASE_DIR, REPORTS_DIR, FIGURES_DIR) |
| ☑ | T3 | Section 1: Load data | Implémenter chargement parquet avec pandas dans `process.py` | T2 | Chargement via pd.read_parquet() |
| ☑ | T4 | Section 2: Filter data | Implémenter filtrage (NaN, ≤0) dans `process.py` avec logs | T3 | Filtrage avec exclusions documentées (0 exclusions au final) |
| ☑ | T5 | Section 3: Temporal processing | Implémenter parsing time + classification jour/nuit astral dans `process.py` | T1, T4 | Fonction classify_day_night() avec gestion timezone wrap-around |
| ☑ | T6 | Section 4: Spatial binning | Implémenter binning lat/lon 1° dans `process.py` | T5 | Binning via .round(0) |
| ☑ | T7 | Section 5: Depth assignment | Implémenter assignation profondeur (140m/210m) + depth_category dans `process.py` | T5 | Profondeur conditionnelle sur year ≤ 1968 |
| ☑ | T8 | Section 6: Lavaniegos conversion | Créer fonction `lavaniegos_dv_to_carbon()` et appliquer conversion dans `process.py` | T7 | Fonction avec 3 étapes (ml/1000m³ → ml/m² → mg/m² → mg/m³) |
| ☑ | T9 | Section 7: Identify tows | Implémenter identification tow_id dans `process.py` | T6, T7 | tow_id via groupby().ngroup() |
| ☑ | T10 | Section 8: Aggregation level 1 | Implémenter agrégation par tow (mean) dans `process.py` | T8, T9 | Agrégation par tow avec mean(biomass_carbon) |
| ☑ | T11 | Section 9: Aggregation level 2 | Implémenter agrégation par cellule/jour (median) dans `process.py` | T10 | Agrégation finale avec median |
| ☑ | T12 | Section 10: Convert to xarray | Implémenter conversion DataFrame → xarray Dataset dans `process.py` | T11 | Conversion via xr.Dataset.from_dataframe() |
| ☑ | T13 | Section 11: Add metadata | Implémenter ajout métadonnées CF-1.8 dans `process.py` | T12 | Métadonnées complètes (global + variables) |
| ☑ | T14 | Section 12: Save NetCDF | Implémenter export NetCDF avec to_netcdf() dans `process.py` | T13 | Export vers release/ (1.3GB) |
| ☑ | T15 | Section 13: Generate figures | Implémenter génération figures (time_series, map) dans `process.py` | T11 | 2 figures générées (time_series_biomass.png 253KB, map.png 321KB) |
| ☑ | T16 | Section 14: Generate report | Implémenter génération report.md dans `process.py` | T14, T15 | Rapport markdown avec statistiques et méthodologie |

---

## Rapport de revue

### Vérifications automatiques

| Outil | Résultat | Erreurs | Warnings |
|-------|----------|---------|----------|
| ruff (linter) | ⚠️ | 0 | 8 (E501 line length) |
| Script execution | ✅ | 0 | 0 |

### Issues identifiées

| ID | Sévérité | Description | Fichier | Action |
|----|----------|-------------|---------|--------|
| I1 | Info | 8 lignes dépassent 88 caractères (89-111 chars) | process.py:62,174,175,202,349,358,385,386 | Optionnel (lisibilité OK) |
| I2 | Mineure | Bug timezone dans classification jour/nuit (fixé) | process.py:classify_day_night() | ✅ Corrigé |
| I3 | Mineure | Import inutilisé Plotter (fixé par ruff) | process.py:20 | ✅ Corrigé |

### Analyse des tâches échouées

| Tâche | Cause | Recommandation |
|-------|-------|----------------|
| Aucune | - | Toutes les tâches complétées avec succès |

### Qualité du code

**✅ Cohérence** : Le code suit exactement les patterns de HOT/BATS/PAPA
- Sections numérotées avec emojis
- Agrégation en 2 niveaux
- Métadonnées CF-1.8 complètes
- Génération automatique figures + rapport

**✅ Lisibilité** : Code clair avec docstrings détaillées

**✅ Robustesse** :
- Gestion des timezones pour astral (wrap-around UTC)
- Filtrage des valeurs invalides
- Try/except avec fallback sur classification jour/nuit

**✅ Résultats** :
- NetCDF généré : 1.3 GB (32,737 observations)
- Distribution jour/nuit réaliste : 49.8% / 50.2%
- Biomasse carbone : 0.19 - 143.94 mg C/m³ (moyenne 4.68)
- Période : 1951-01-09 à 2023-01-25 (72 ans)
- Couverture : 965 cellules spatiales 1°

### Décision

**→ Passer directement à Test** : Issues mineures uniquement (formatage), fonctionnalité validée

---

## Historique des transitions

| De | Vers | Raison | Date |
|----|------|--------|------|
| - | 1. Initialisation | Démarrage du projet | 2026-01-29 |
| 1. Initialisation | 2. Analyse | Besoin validé par l'utilisateur | 2026-01-29 |
| 2. Analyse | 3. Architecture | Analyse complétée | 2026-01-29 |
| 3. Architecture | 4. Planification | Architecture validée par l'utilisateur | 2026-01-29 |
| 4. Planification | 5. Execution | Todo list complétée | 2026-01-29 |
| 5. Execution | 6. Revue | Toutes les tâches implémentées | 2026-01-29 |
| 6. Revue | 8. Test | Aucune issue critique (skip Resolution) | 2026-01-29 |
