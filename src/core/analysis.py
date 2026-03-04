"""Pure statistical functions for zooplankton biomass analysis.

All functions operate on pandas DataFrames with columns:
    time, biomass, depth_category, day_night, tow_depth_max
and optionally extra biomass columns (biomass_carbon, biomass_nitrogen, biomass_wet).
"""

import warnings

import numpy as np
import pandas as pd
import xarray as xr
from scipy import stats


def load_release_as_dataframe(
    nc_path: str,
    biomass_var: str = "biomass_dry",
    extra_vars: list[str] | None = None,
) -> pd.DataFrame:
    """Load a NetCDF release file and return a flat DataFrame.

    Squeezes singleton lat/lon dims (PAPA), drops NaN biomass rows.
    """
    ds = xr.open_dataset(nc_path)

    # Squeeze singleton spatial dims (PAPA per-station files have lat=1, lon=1)
    for dim in ("lat", "lon"):
        if dim in ds.dims and ds.sizes[dim] == 1:
            ds = ds.squeeze(dim, drop=True)

    vars_to_load = [biomass_var, "tow_depth_max"]
    if extra_vars:
        vars_to_load.extend(extra_vars)

    # Keep only variables that exist in the dataset
    vars_to_load = [v for v in vars_to_load if v in ds.data_vars]

    # Stack all dims into a flat DataFrame
    records = []
    for var in vars_to_load:
        da = ds[var]
        df_var = da.to_dataframe().reset_index()
        if records:
            records[0][var] = df_var[var]
        else:
            records.append(df_var)

    df = records[0] if records else pd.DataFrame()
    if df.empty:
        return df

    # Drop rows where primary biomass is NaN
    df = df.rename(columns={biomass_var: "biomass"})
    df = df.dropna(subset=["biomass"]).reset_index(drop=True)

    # Ensure time is datetime
    df["time"] = pd.to_datetime(df["time"])

    return df


def detect_outliers_iqr(series: pd.Series, k: float = 1.5) -> pd.Series:
    """Return a boolean mask where True = outlier (IQR method)."""
    q1 = series.quantile(0.25)
    q3 = series.quantile(0.75)
    iqr = q3 - q1
    lower = q1 - k * iqr
    upper = q3 + k * iqr
    return (series < lower) | (series > upper)


def temporal_coverage(df: pd.DataFrame) -> dict:
    """Compute temporal coverage statistics.

    Returns a dict with:
        - matrix: year x month observation count DataFrame
        - total_obs: total observations
        - year_range: (min_year, max_year)
        - gaps: list of (year, month) with 0 observations in range
        - median_monthly_obs: median obs per month across all year-months with data
    """
    df = df.copy()
    df["year"] = df["time"].dt.year
    df["month"] = df["time"].dt.month

    matrix = df.pivot_table(
        index="year", columns="month", values="biomass", aggfunc="count", fill_value=0
    )
    # Ensure all months 1-12 are present
    for m in range(1, 13):
        if m not in matrix.columns:
            matrix[m] = 0
    matrix = matrix.reindex(columns=range(1, 13), fill_value=0)

    year_range = (int(matrix.index.min()), int(matrix.index.max()))

    # Gaps: year-months within range that have 0 obs
    gaps = []
    for y in range(year_range[0], year_range[1] + 1):
        for m in range(1, 13):
            if y in matrix.index and matrix.loc[y, m] == 0:
                gaps.append((y, m))
            elif y not in matrix.index:
                gaps.append((y, m))

    nonzero = matrix.values[matrix.values > 0]
    median_monthly_obs = float(np.median(nonzero)) if len(nonzero) > 0 else 0.0

    return {
        "matrix": matrix,
        "total_obs": len(df),
        "year_range": year_range,
        "gaps": gaps,
        "n_gaps": len(gaps),
        "median_monthly_obs": median_monthly_obs,
    }


def day_night_bias(df: pd.DataFrame) -> dict:
    """Compare biomass between day and night samples.

    Returns stats dict with medians, counts, Mann-Whitney U test results.
    Skips test if either group has < 5 observations.
    """
    day = df.loc[df["day_night"] == "day", "biomass"]
    night = df.loc[df["day_night"] == "night", "biomass"]

    result = {
        "day_n": len(day),
        "night_n": len(night),
        "day_median": float(day.median()) if len(day) > 0 else np.nan,
        "night_median": float(night.median()) if len(night) > 0 else np.nan,
        "day_mean": float(day.mean()) if len(day) > 0 else np.nan,
        "night_mean": float(night.mean()) if len(night) > 0 else np.nan,
    }

    if len(day) > 0 and len(night) > 0:
        result["median_ratio_night_day"] = result["night_median"] / result["day_median"] if result["day_median"] != 0 else np.nan
    else:
        result["median_ratio_night_day"] = np.nan

    if len(day) >= 5 and len(night) >= 5:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            u_stat, p_value = stats.mannwhitneyu(day, night, alternative="two-sided")
        result["mannwhitney_U"] = float(u_stat)
        result["mannwhitney_p"] = float(p_value)
        result["test_performed"] = True
    else:
        result["mannwhitney_U"] = np.nan
        result["mannwhitney_p"] = np.nan
        result["test_performed"] = False

    return result


def depth_category_bias(df: pd.DataFrame) -> dict:
    """Compare biomass between depth categories.

    Returns stats dict with medians, counts, Mann-Whitney U test results.
    Skips test if either group has < 5 observations.
    """
    epi = df.loc[df["depth_category"] == "epipelagic_only", "biomass"]
    meso = df.loc[df["depth_category"] == "epipelagic_mesopelagic", "biomass"]

    result = {
        "epipelagic_n": len(epi),
        "mesopelagic_n": len(meso),
        "epipelagic_median": float(epi.median()) if len(epi) > 0 else np.nan,
        "mesopelagic_median": float(meso.median()) if len(meso) > 0 else np.nan,
        "epipelagic_mean": float(epi.mean()) if len(epi) > 0 else np.nan,
        "mesopelagic_mean": float(meso.mean()) if len(meso) > 0 else np.nan,
    }

    if len(epi) > 0 and len(meso) > 0:
        result["median_ratio_meso_epi"] = result["mesopelagic_median"] / result["epipelagic_median"] if result["epipelagic_median"] != 0 else np.nan
    else:
        result["median_ratio_meso_epi"] = np.nan

    if len(epi) >= 5 and len(meso) >= 5:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            u_stat, p_value = stats.mannwhitneyu(epi, meso, alternative="two-sided")
        result["mannwhitney_U"] = float(u_stat)
        result["mannwhitney_p"] = float(p_value)
        result["test_performed"] = True
    else:
        result["mannwhitney_U"] = np.nan
        result["mannwhitney_p"] = np.nan
        result["test_performed"] = False

    return result


def monthly_climatology(df: pd.DataFrame) -> pd.DataFrame:
    """Compute monthly climatology: median and IQR per month.

    Returns a DataFrame indexed by month (1-12) with columns:
        median, q25, q75, count
    """
    df = df.copy()
    df["month"] = df["time"].dt.month

    clim = df.groupby("month")["biomass"].agg(
        median="median",
        q25=lambda x: x.quantile(0.25),
        q75=lambda x: x.quantile(0.75),
        count="count",
    )

    # Ensure all 12 months present
    clim = clim.reindex(range(1, 13))
    return clim


def compute_anomalies(df: pd.DataFrame, climatology: pd.DataFrame) -> pd.DataFrame:
    """Compute anomalies: observation - monthly climatology median.

    Returns the input DataFrame with an added 'anomaly' column.
    """
    df = df.copy()
    df["month"] = df["time"].dt.month
    df["anomaly"] = df.apply(
        lambda row: row["biomass"] - climatology.loc[row["month"], "median"]
        if pd.notna(climatology.loc[row["month"], "median"])
        else np.nan,
        axis=1,
    )
    return df


def trend_theilsen(times: pd.Series, values: pd.Series) -> dict:
    """Compute Theil-Sen slope and Mann-Kendall trend test.

    Operates on annual medians to avoid bias from uneven sampling.
    Returns dict with slope, intercept, p_value, tau, annual_medians DataFrame.
    Skips if fewer than 5 years of data.
    """
    df = pd.DataFrame({"time": times, "value": values}).copy()
    df["year"] = df["time"].dt.year

    annual = df.groupby("year")["value"].median().dropna()

    result = {
        "annual_medians": annual,
        "n_years": len(annual),
    }

    if len(annual) < 5:
        result.update({
            "slope": np.nan,
            "intercept": np.nan,
            "mk_tau": np.nan,
            "mk_p": np.nan,
            "test_performed": False,
        })
        return result

    x = annual.index.values.astype(float)
    y = annual.values.astype(float)

    # Theil-Sen slope
    ts_result = stats.theilslopes(y, x)
    slope, intercept = ts_result[0], ts_result[1]

    # Mann-Kendall test (manual implementation using scipy's kendalltau)
    # kendalltau against time index gives equivalent trend significance
    tau, mk_p = stats.kendalltau(x, y)

    result.update({
        "slope": float(slope),
        "intercept": float(intercept),
        "mk_tau": float(tau),
        "mk_p": float(mk_p),
        "test_performed": True,
    })

    return result
