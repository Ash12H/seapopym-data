# Workflow State

## Informations générales

- **Projet** : seapopym-data
- **Étape courante** : 9. Finalisation
- **Rôle actif** : Facilitateur
- **Dernière mise à jour** : 2026-01-28T14:23:00+01:00
- **Dernière mise à jour** : 2026-01-28T14:15:00+01:00
- **Dernière mise à jour** : 2026-01-28T14:02:00+01:00
- **Dernière mise à jour** : 2026-01-28T13:58:00+01:00
- **Dernière mise à jour** : 2026-01-28T13:42:00+01:00
- **Hors Périmètre (pour l'instant)** : L'ajout de la station `canaries` se fera dans un second temps, une fois l'architecture validée.

## Rapport d'analyse

### Structure du projet actuelle

Le projet est organisé par station dans `src/`. Chaque station (`bats`, `calcofi`, `hot`, `papa`) suit le schéma :

- `1_raw/`: Données brutes (CSV, Parquet, JSON).
- `2_processed/:` NetCDF intermédiaires.
- `3_post_processed/`: Produits finaux.
- `scripts/`: Notebooks Jupyter organisés en sous-dossiers (`1_preprocessed`, etc.).

### Technologies identifiées

- **Langage** : Python 3.12+
- **Gestionnaire** : Poetry (à migrer vers `uv`).
- **Data** : Pandas, Xarray, NetCDF4, Zarr.
- **Visu** : Plotly, Hvplot (lourds, outputs dans notebooks).
- **Workflow** : Jupyter Notebooks monolithiques (Code + Output + Markdown).

### Points d'attention & Dette

1.  **Poids des Notebooks** : Fichiers `.ipynb` énormes (ex: 39MB) car ils stockent les outputs Plotly interactifs.
2.  **Mélange de périmètres** : Présence de données non-zooplancton (Primary Production, Bottle, CTD) à supprimer.
3.  **Redondance** : Structure de dossiers répétitive mais code dupliqué entre les notebooks des stations.
4.  **Dépendances** : Trop de libs de visualisation interactive inutiles pour des rapports statiques.

### Stratégie de Refactoring

1.  **Nettoyage** : Suppression radicale des fichiers non-zooplancton.
2.  **Aplatissement** : Simplification de l'arborescence des données (`data/raw`, `data/processed`).
3.  **Scripting** : Extraction de la logique des notebooks vers des modules Python réutilisables et des scripts d'exécution.
4.  **Reporting** : Création d'un module de génération de rapport Markdown + PNG.

## Décisions d'architecture

### Choix techniques

| Domaine             | Choix                  | Justification                                                                   |
| ------------------- | ---------------------- | ------------------------------------------------------------------------------- |
| **Gestionnaire**    | `uv`                   | Plus rapide, standard moderne, remplace Poetry.                                 |
| **Langage**         | Python 3.12+ scripts   | Remplacement des Notebooks pour meilleure maintenabilité et gestion de version. |
| **Data Processing** | `pandas`, `xarray`     | Standards déjà en place, conservés.                                             |
| **Reporting**       | `matplotlib`/`seaborn` | Légers, statiques, parfaits pour génération de PNGs dans rapports Markdown.     |
| **Linting/Format**  | `ruff`                 | Déjà en place, rapide et complet.                                               |

### Structure proposée

Refonte de l'organisation par station pour suivre le schéma validé :

```text
seapopym-data/
├── pyproject.toml      (Géré par uv)
├── uv.lock
├── src/
│   ├── core/           (NOUVEAU: Code partagé - IO, Plotting commun, Unités)
│   │   ├── plotting.py
│   │   └── units.py
│   ├── bats/
│   │   ├── data/
│   │   │   ├── raw/    (ex-1_raw)
│   │   │   └── temp/   (ex-2_processed, fichiers intermédiaires)
│   │   ├── scripts/
│   │   │   └── process.py  (Script unique de traitement)
│   │   ├── reports/
│   │   │   ├── report.md
│   │   │   └── figures/
│   │   └── release/    (ex-3_post_processed, produit final netCDF)
│   ├── calcofi/
│   ├── hot/
│   └── papa/
```

### Conventions & Standards

- **Scripts** : Un script principal par station (ex: `process.py`) qui :
    1. Lit les données raw.
    2. Nettoie et standardise (unités, noms variables).
    3. Génère les figures de contrôle dans `reports/figures/`.
    4. Sauvegarde le NetCDF final dans `release/`.
    5. Génère/Met à jour `reports/report.md`.
- **Rapport** : Chaque station aura un `report.md` standardisé contenant les métadonnées de l'exécution et les figures générées.
- **Nettoyage** : Suppression stricte de tout ce qui n'est pas "Zooplankton Abundance/Biomass".

### Interfaces et contrats

- **Input** : Fichiers CSV/Tab dans `data/raw/`.
- **Output** : Un fichier NetCDF standardisé dans `release/` contenant uniquement les variables zooplancton, avec métadonnées conformes (CF conventions).

### Risques identifiés

| Risque                                      | Impact | Mitigation                                                                 |
| ------------------------------------------- | ------ | -------------------------------------------------------------------------- |
| Perte de logique lors conversion NB->Script | Moyen  | Lecture attentive cellule par cellule, comparaison des outputs finaux.     |
| Incohérence des unités entre stations       | Haut   | Création d'un module `core.units` pour conversion explicite (Pint-xarray). |

## Todo List

| État | ID  | Nom                  | Description                                                                                                          | Dépendances      | Résolution                                                                               |
| ---- | --- | -------------------- | -------------------------------------------------------------------------------------------------------------------- | ---------------- | ---------------------------------------------------------------------------------------- | --- |
| ☑    | T1  | Clean Environment    | Supprimer `.venv`, `poetry.lock`. Initialiser `uv`. Créer nouveau `pyproject.toml`.                                  | -                | Environnement nettoyé, `uv` initialisé, dépendances installées.                          |
| ☑    | T2  | Create New Structure | Créer l'arborescence vide `src/core`, et pour chaque station `data/`, `scripts/`, `reports/`, `release/`.            | T1               | Arborescence standardisée créée pour toutes les stations.                                |
| ☑    | T3  | Migrate Data         | Déplacer les fichiers raw/temp/product vers `data/raw`, `data/temp`, `release`. Supprimer les dossiers `1_raw`, etc. | T2               | Données migrées pour BATS, CALCOFI, HOT, PAPA. Anciens dossiers supprimés.               |
| ☑    | T4  | Cleanup Non-Zoo      | Supprimer radicalement tous les fichiers non liés au Zooplancton (CTD, Bottle, PP).                                  | T3               | Tous les fichiers contenant 'primary_production', 'bottle', 'ctd' ont été supprimés.     |
| ☑    | T5  | Implement Core IO    | Créer `src/core/io.py` pour gérer lecture/écriture standardisée.                                                     | T1, T2           | Module IO créé avec DataLoader et DataWriter.                                            |
| ☑    | T6  | Implement Core Plot  | Créer `src/core/plotting.py` pour générer les figures statiques standards.                                           | T1, T2           | Module Plotting créé avec time_series, missing_values, map.                              |
| ☑    | T7  | Implement Core Units | Créer `src/core/units.py` pour gérer les conversions d'unités avec Pint.                                             | T1, T2           | Module Units créé avec UnitManager.                                                      |
| ☑    | T8  | Migrate Bats         | Créer `src/bats/scripts/process.py` en migrant la logique du notebook. Générer rapport.                              | T5, T6, T7       | Script `process.py` fonctionnel. NetCDF et rapport générés.                              |
| ☑    | T9  | Migrate Calcofi      | Créer `src/calcofi/scripts/process.py` en migrant la logique du script/nb existant.                                  | T5, T6, T7       | Script `process.py` fonctionnel. NetCDF et rapport générés.                              |
| ☑    | T10 | Migrate Hot          | Créer `src/hot/scripts/process.py` en migrant la logique du notebook.                                                | T5, T6, T7       | Script `process.py` fonctionnel. NetCDF et rapport générés.                              |
| ☑    | T11 | Migrate Papa         | Créer `src/papa/scripts/process.py` en migrant la logique du notebook.                                               | T5, T6, T7       | Script `process.py` fonctionnel avec options CSV spécifiques. NetCDF et rapport générés. |
| ☑    | T12 | Verify & Validate    | Vérifier la génération des rapports pour toutes les stations.                                                        | T8, T9, T10, T11 | Vérification effectuée. Tous les fichiers cibles (NetCDF, Reports) sont présents.        |     |

## Rapport de revue

### Vérifications automatiques

| Outil | Résultat | Erreurs | Warnings |
| ----- | -------- | ------- | -------- |
| Ruff  | ❌       | 30      | -        |

### Issues identifiées

| ID  | Sévérité | Description          | Fichier          | Statut              |
| --- | -------- | -------------------- | ---------------- | ------------------- |
| I1  | Mineure  | Imports inutilisés   | Tous             | ✅ Corrigé          |
| I2  | Mineure  | Module import - E402 | Script proces.py | ✅ Corrigé (Ignore) |
| I3  | Mineure  | F-strings inutiles   | Tous             | ✅ Corrigé          |
| I4  | Majeure  | Notebooks obsolètes  | src/\*/scripts   | ✅ Corrigé          |

### Vérifications post-correction

| Outil | Résultat     |
| ----- | ------------ |
| Ruff  | ✅ 0 erreurs |

## Historique des transitions

| De                | Vers              | Raison                                                  | Date       |
| ----------------- | ----------------- | ------------------------------------------------------- | ---------- |
| -                 | 1. Initialisation | Démarrage du workflow ASH                               | 2026-01-28 |
| 1. Initialisation | 2. Analyse        | Besoin validé par l'utilisateur                         | 2026-01-28 |
| 2. Analyse        | 3. Architecture   | Analyse complétée                                       | 2026-01-28 |
| 3. Architecture   | 4. Planification  | Architecture validée par l'utilisateur                  | 2026-01-28 |
| 4. Planification  | 5. Execution      | Todo list complétée                                     | 2026-01-28 |
| 5. Execution      | 6. Revue          | Toutes les tâches traitées                              | 2026-01-28 |
| 6. Revue          | 7. Resolution     | 30 erreurs de linting détectées et nettoyage nécessaire | 2026-01-28 |
| 7. Resolution     | 8. Test           | Issues résolues, code propre                            | 2026-01-28 |
| 8. Test           | 9. Finalisation   | Tests Core validés (IO, Units)                          | 2026-01-28 |
