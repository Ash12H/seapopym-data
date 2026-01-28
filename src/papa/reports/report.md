# PAPA Station Report

**Date**: 2026-01-28 17:12:12
**Region**: North Pacific (47.0-57.9°N, -156.8--128.1°W)

## Summary

- Initial rows: 1,077
- Final observations: 820
- Unique tows: 861
- Period: 1995-09-24 to 2020-08-31
- Spatial cells (0.5°): 161

### Exclusions

- Depth <50m: 16 rows
- Adult polychaetes: 3 taxa columns (benthic species)

### Depth Categories

- Epipelagic only (≤150m): 324 observations
  - Mean tow depth: 141.4m
- Epipelagic + Mesopelagic (>150m): 496 observations
  - Mean tow depth: 241.4m

### Biomass Statistics

| Metric | Mean | Median | Min | Max |
|--------|------|--------|-----|-----|
| Dry Weight (mg/m³) | 34.95 | 24.69 | 1.15 | 274.83 |

## Figures

![Map](figures/map.png)

![Time Series](figures/time_series_biomass.png)

## Methodology

**Sampling Method**: Oblique tows from surface to maximum depth

**Net**: Bongo (majority) with 236 µm mesh

**Taxonomic Groups**: 91 planktonic taxa (94 total - 3 benthic polychaetes)

**Spatial Resolution**: 0.5° grid

**Aggregation**:
1. Sum of 91 taxa per tow
2. Median of tows per day/depth_category/spatial_cell

