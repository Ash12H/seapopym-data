# HOT Station Processing Report

**Date**: 2026-01-28 16:14:02
**Station**: Hawaii Ocean Time-series (HOT), Station ALOHA
**Location**: 22.75°N, -158°W

---

## Data Processing Summary

- **Input file**: `hot_zooplankton.csv`
- **Output file**: `hot_zooplankton_obs.nc`
- **Initial rows**: 9,348
- **Initial tows**: 1,558
- **Final rows**: 1,176
- **Time period**: 1994-02-17 to 2022-09-02

### Exclusions Applied

1. **Shallow tows** (depth <50m): 2 tows excluded
   - Tow 48: 1995-02-05T11:20:00 | depth=17m
   - Tow 386: 2000-03-28T11:02:00 | depth=9m

2. **Fraction 5** (>5mm micronekton): 1,556 rows excluded

### Depth Categories

- **epipelagic_only** (≤150m): 427 observations
  - Samples ONLY epipelagic zone (0-150m)
  - Mean tow depth: 126.2m

- **epipelagic_mesopelagic** (>150m): 749 observations
  - Samples BOTH epipelagic (0-150m) AND mesopelagic (>150m) zones
  - Mean tow depth: 186.9m

### Biomass Statistics

| Metric | Mean | Median | Min | Max |
|--------|------|--------|-----|-----|
| Dry Weight (mg/m³) | 5.99 | 5.57 | 0.00 | 29.98 |
| Carbon (mg/m³) | 1.73 | 1.65 | 0.00 | 11.21 |
| Nitrogen (mg/m³) | 0.42 | 0.39 | 0.00 | 2.66 |

---

## Figures

### Station Location

![Station Map](figures/map.png)

### Time Series of Biomass

![Time Series](figures/time_series_biomass.png)

---

## Methodology

**Sampling Method**: Oblique tows from surface to maximum depth and back

**Net**: 1 m² with 202 µm mesh (Nitex)

**Size Fractions**: 0 (200µm), 1 (500µm), 2 (1mm), 3 (2mm), 4 (5mm)

**Unit Conversion**: Area density (g/m² or mg/m²) divided by tow depth → concentration (mg/m³)

**Aggregation**:
1. Sum of size fractions 0-4 per tow
2. Median of tows per day/depth_category/day_night

---

*Generated with seapopym-data pipeline*
