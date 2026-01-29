# CalCOFI Station Report

**Date**: 2026-01-29 19:13:33
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

