# Methodology: Observation Operator for Zooplankton Biomass Assimilation

## 1. Context

The SEAPOPYM model simulates zooplankton biomass in two vertical compartments:

- **Surface zooplankton** (`zoo_surface`): epipelagic layer, 0 to 1.5 × Z_eu
- **Migrant zooplankton** (`zoo_migrant`): upper-mesopelagic layer, 1.5 × Z_eu to 4.5 × Z_eu

where Z_eu is the euphotic depth. Migrants undergo diel vertical migration (DVM): they reside in the mesopelagic layer during the day and ascend to the surface layer at night to feed.

Model outputs are **concentrations in mg/m³** for each compartment.

Three in-situ observation networks provide zooplankton dry weight biomass concentration (mg/m³): HOT (Hawaii), BATS (Bermuda), and 7 PAPA stations (NE Pacific). These observations are oblique net tow integrated measurements — they average the zooplankton concentration over the entire water column traversed by the net, from the surface down to the maximum tow depth.

To assimilate these observations in a parameter optimisation (genetic algorithm), we need an **observation operator** H that maps model state to the equivalent of what the net would measure.

## 2. Observation datasets

### 2.1. Station characteristics

| Station | Location | Period | N obs | Median biomass (mg/m³) | Tow depth range (m) | Ecosystem |
|---------|----------|--------|-------|----------------------|---------------------|-----------|
| HOT | 22.75°N, 158°W | 1994–2022 | 1176 | 5.6 | 55–268 | Oligotrophic subtropical N. Pacific |
| BATS | 31.6°N, 64.2°W | 1995–2022 | 810 | 2.4 | 60–306 | Oligotrophic subtropical N. Atlantic |
| PAPA P08 | 48.8°N, 128.7°W | 1997–2020 | 63 | 19.6 | — | Subarctic NE Pacific (coastal) |
| PAPA P12 | 49.0°N, 130.7°W | 1996–2020 | 70 | 20.6 | — | Subarctic NE Pacific |
| PAPA P16 | 49.3°N, 134.7°W | 1997–2020 | 59 | 24.1 | — | Subarctic NE Pacific |
| PAPA P20 | 49.6°N, 138.7°W | 1997–2020 | 64 | 27.0 | — | Subarctic NE Pacific |
| PAPA P26 | 50.0°N, 145.0°W | 1997–2020 | 74 | 25.1 | — | Subarctic NE Pacific (Ocean Station Papa) |
| PAPA LBP7 | 49.9°N, 128.2°W | 1995–2020 | 43 | 19.0 | — | Subarctic NE Pacific (coastal) |
| PAPA CS01 | 50.6°N, 129.7°W | 1998–2020 | 37 | 36.1 | — | Subarctic NE Pacific (shelf break) |

### 2.2. How each dataset reaches mg/m³

The three networks use different raw measurements but all produce mean volumetric concentrations:

| Network | Raw measurement | Normalisation | Result |
|---------|----------------|---------------|--------|
| **HOT** | Dry weight in g/m² (integrated per m² of sea surface over the tow depth) | Divided by tow depth (m) in `process.py`, then converted g → mg | mg/m³ = mean concentration over the sampled water column |
| **BATS** | Dry weight in mg (absolute mass per size fraction) and volume of water filtered in m³ | Pre-computed by data provider: `dry_weight / volume_water` | mg/m³ = mean concentration in the water filtered by the net |
| **PAPA** | Taxonomic biomass per taxon, already reported in mg/m³ by DFO Canada (= dry weight / volume filtered) | Sum of 91 taxa in `process.py` (no further normalisation) | mg/m³ = mean concentration over the sampled water column |

**In all cases, the observation is a vertical average of the true concentration profile, weighted by the volume of water sampled at each depth.**

### 2.3. Observation metadata (per data point)

Each observation in the release NetCDF files carries:

| Field | Variable | Description |
|-------|----------|-------------|
| Time | `time` | Date of the tow |
| Biomass | `biomass_dry` | Dry weight concentration (mg/m³) |
| Tow depth | `tow_depth_max` | Maximum depth reached by the net (m) |
| Depth category | `depth_category` | `epipelagic_only` (≤150 m) or `epipelagic_mesopelagic` (>150 m) |
| Day/Night | `day_night` | `day` or `night` based on local time or Twilight flag |
| Position | `lat`, `lon` | Station coordinates |

**Additional field required for the observation operator** (not in the NetCDF, must be supplied externally):

| Field | Source | Description |
|-------|--------|-------------|
| Z_eu | Satellite climatology (e.g. GlobColour, MODIS) or model output | Euphotic depth (m) at the station location and time |

Typical Z_eu values: HOT ~100–120 m, BATS ~80–110 m, PAPA ~40–60 m.

## 3. Observation operator

### 3.1. Principle

The net integrates zooplankton biomass from the surface to `tow_depth_max`. The measured concentration is the vertical mean over that depth interval. The observation operator reconstructs this measurement from the model's two-layer concentrations.

### 3.2. Vertical layer mapping

Given Z_eu at the observation location and time:

- **Surface layer** (model): 0 to h_s = 1.5 × Z_eu
- **Migrant layer** (model): h_s to h_m = 4.5 × Z_eu
- **Below model**: depths > h_m (assumed zero zooplankton from the model)

For a tow reaching depth D:

- Depth sampled in surface layer: d_s = min(D, h_s)
- Depth sampled in migrant layer: d_m = max(0, min(D, h_m) − h_s)
- Depth sampled below model: d_b = max(0, D − h_m)

### 3.3. DVM parameterisation

The model parameter **f** (0 ≤ f ≤ 1) represents the fraction of the migrant compartment that ascends to the surface layer at night. This parameter can be optimised by the genetic algorithm.

**Effective concentrations seen by the net:**

**Day:**
- In the surface layer: C_s^day = zoo_surface
- In the migrant layer: C_m^day = zoo_migrant

**Night:**
- In the surface layer: C_s^night = zoo_surface + f × zoo_migrant × (h_m − h_s) / h_s
- In the migrant layer: C_m^night = (1 − f) × zoo_migrant

Note: the term `(h_m − h_s) / h_s` accounts for the redistribution of migrants (originally in a thick layer) into the thinner surface layer, conserving total biomass per m².

### 3.4. Simulated observation

```
H(model, obs) = (d_s × C_s + d_m × C_m + d_b × C_b) / D
```

where:
- C_s, C_m are the effective day or night concentrations from §3.3
- C_b = 0 (below-model contribution, negligible)
- D = d_s + d_m + d_b = tow_depth_max

### 3.5. Examples

**HOT, epi-only day tow (D=129 m, Z_eu=110 m):**
- h_s = 165 m, h_m = 495 m
- d_s = 129 m, d_m = 0 m → H = zoo_surface
- The tow sees only the surface compartment.

**HOT, epi+meso night tow (D=184 m, Z_eu=110 m):**
- d_s = 165 m, d_m = 19 m
- H = (165 × C_s^night + 19 × C_m^night) / 184
- The tow is dominated by the surface layer (90%) where migrants have accumulated.

**PAPA P26, epi+meso day tow (D=250 m, Z_eu=50 m):**
- h_s = 75 m, h_m = 225 m
- d_s = 75 m, d_m = 150 m, d_b = 25 m
- H = (75 × zoo_surface + 150 × zoo_migrant) / 250
- The tow is dominated by the migrant layer (60%).

This illustrates why PAPA observations are particularly informative for constraining `zoo_migrant`: deep tows at high latitude (low Z_eu) sample proportionally more of the migrant layer.

## 4. Cost function for parameter optimisation

### 4.1. Log-transformation (and why not NRMSE-std)

Zooplankton biomass is approximately log-normally distributed (range spans 2 orders of magnitude across stations). Residuals are computed in log-space:

```
r_i = ln(H_i + ε) − ln(obs_i + ε)
```

where ε is a small constant (e.g. 0.01 mg/m³) to handle near-zero values.

**Why log-residuals rather than NRMSE normalised by standard deviation?**

A common alternative is NRMSE-std, where residuals are computed in linear space and normalised per station by the standard deviation of observed values:

```
NRMSE_s = sqrt( (1/N_s) × Σ_i (H_i − obs_i)² ) / std(obs_s)
```

Both approaches address the inter-station scale difference (BATS median ~2 mg/m³ vs PAPA CS01 ~36 mg/m³). However, NRMSE-std normalises globally per station, while biomass data is **heteroscedastic** — variance increases with magnitude. This creates a problem *within* each station:

| Observation | Biomass | Model | Abs. error | Rel. error | r² (linear) | r² (log) |
|-------------|---------|-------|-----------|------------|-------------|----------|
| HOT night, epi+meso | 25 mg/m³ | 18 mg/m³ | 7 | 28% | 49 | 0.11 |
| HOT day, epi-only | 1.5 mg/m³ | 3.0 mg/m³ | 1.5 | 100% | 2.25 | 0.48 |

With NRMSE (linear), the night observation dominates (49 vs 2.25) despite a smaller relative error. With log-residuals, the day observation correctly receives more weight — the model is 2× too high, which is worse than 28% too low.

This matters specifically for parameter optimisation because:

1. **Constraining f_migrate** requires balanced day/night weighting. Day observations (low biomass, no migrants) directly constrain `zoo_surface` alone, but they are systematically lower in magnitude. In linear space, the optimizer focuses on fitting the large night values and under-constrains `zoo_surface`.

2. **Cross-station consistency**: within PAPA stations, biomass ranges from 1 to 275 mg/m³. Log-residuals treat a 50% model-observation mismatch identically whether it occurs at 5 or 50 mg/m³.

3. **Statistical justification**: the log-normal distribution assumption means that ln(biomass) has approximately constant variance — the standard assumption for least-squares is satisfied in log-space but not in linear space.

If NRMSE-std is preferred (e.g. for comparison with published benchmarks), it should be applied **per observation category** (station × depth_category × day_night) rather than per station alone, to avoid intra-station heteroscedasticity bias. In practice this converges toward the log-residual approach in complexity without the distributional justification.

### 4.2. Station weighting

Observation counts are highly unbalanced (HOT: 1176, PAPA CS01: 37). Without weighting, the cost function would be dominated by HOT and BATS.

Recommended approach — **weight by inverse station count**:

```
J = Σ_stations [ (1 / N_s) × Σ_{i ∈ station s} r_i² ]
```

This gives each station equal influence regardless of sample size. Alternatively, draw a stratified bootstrap sample (equal N per station) at each generation of the GA.

### 4.3. Complete cost function

**Step-by-step description:**

For each individual in the GA (parameter set θ):

1. Run the model with θ.
2. For each station s (9 stations):
   - For each observation i in that station:
     - (a) Extract `zoo_surface` and `zoo_migrant` from the model at the matching grid cell and time step.
     - (b) Compute H_i using the observation operator (§3) with `tow_depth_max`, `day_night`, and Z_eu.
     - (c) Compute the log-residual: r_i = ln(H_i + ε) − ln(obs_i + ε).
   - Compute the mean squared residual for this station: J_s = (1/N_s) × Σ r_i²
3. Sum over all stations: J(θ) = Σ_s J_s

**In compact notation:**

```
J(θ) = Σ_s  (1/N_s) × Σ_{i ∈ s}  [ ln(H(θ, obs_i) + ε) − ln(obs_i.biomass + ε) ]²
```

where:
- θ is the parameter vector (including f_migrate)
- N_s is the number of observations at station s
- H(θ, obs_i) is the observation operator applied to model output forced by θ, matched to observation i in time and space
- ε = 0.01 mg/m³
- The outer sum runs over all 9 stations; the inner sum over all observations within each station

J(θ) is the fitness to **minimise**. Each station contributes its mean squared log-error, so all 9 stations have equal influence.

### 4.4. What the different observation types constrain

| Observation type | Day | Night |
|-----------------|-----|-------|
| **Epi-only** (shallow tow, D < h_s) | Constrains `zoo_surface` directly | Constrains `zoo_surface + f × zoo_migrant` |
| **Epi+meso** (deep tow, D > h_s) | Constrains weighted average of both compartments | Constrains total biomass with migrants redistributed |

The **day/night contrast within the same station and season** is the primary constraint on the migration fraction f. The **depth-category contrast** constrains the vertical distribution of biomass between the two compartments.

## 5. Practical implementation notes

### 5.1. Matching model to observations

- **Temporal**: match each observation to the nearest model time step (monthly or daily depending on model resolution)
- **Spatial**: match to the model grid cell containing the station coordinates
- **Z_eu**: use the model's own Z_eu if available, otherwise use a satellite-derived monthly climatology

### 5.2. Outlier handling

The statistical analysis (IQR × 1.5) identified 3–7% outliers per station. Two strategies:

1. **Exclude outliers before optimisation** — simpler, avoids extreme residuals distorting the cost function
2. **Use a robust cost function** (e.g. Huber loss instead of squared residuals) — preserves all data but downweights extremes

Strategy 1 is recommended for a first optimisation pass; strategy 2 for refinement.

### 5.3. Known biases and limitations

| Bias | Magnitude | Handled by |
|------|-----------|------------|
| Day/night (DVM) | Night/day ratio 1.2–1.9 | Observation operator (f parameter) |
| Depth dilution (epi vs meso) | Meso/epi ratio 0.74–0.87 | Observation operator (layer weighting) |
| Seasonal sampling gaps | 39–269 month-gaps | Model fills gaps; cost function only evaluated at observed times |
| Inter-station biomass range | 2–36 mg/m³ median | Log-transform + station weighting |
| Net mesh differences | HOT/BATS: 202 µm; PAPA: 236 µm | Not corrected — assumed small effect on total biomass; could add station-specific bias term if needed |
| Below-model zooplankton | Up to 10% of tow depth (PAPA deep tows) | Assumed C_b = 0; conservative |

### 5.4. Sensitivity tests

Recommended sensitivity analyses for the optimised parameters:

1. **Exclude one station at a time** (leave-one-out) to assess robustness
2. **Fix f_migrate** at literature values (0.3, 0.5, 0.7) and compare to optimised value
3. **Vary Z_eu ± 20%** to assess sensitivity to euphotic depth uncertainty
4. **Day-only vs night-only** subsets to verify internal consistency

## 6. Reference

### NetCDF release files used

```
src/hot/release/hot_zooplankton_obs.nc        # HOT: biomass_dry, biomass_carbon, biomass_nitrogen
src/bats/release/bats_zooplankton_obs.nc      # BATS: biomass_dry, biomass_wet
src/papa/release/papa_{P08,P12,P16,P20,P26,LBP7,CS01}_obs.nc  # PAPA: biomass_dry
```

### Processing scripts

```
src/hot/scripts/process.py          # HOT: g/m² → mg/m³ via depth division
src/bats/scripts/process.py         # BATS: pre-normalised mg/m³
src/papa/scripts/process.py         # PAPA aggregated (not used for optimisation)
src/papa/scripts/process_stations.py # PAPA per-station: taxa sum in mg/m³
```

### Statistical analysis

```
src/core/analyze_station.py         # Per-station analysis (outliers, biases, trends)
src/core/compare_stations.py        # Inter-station comparison
```
