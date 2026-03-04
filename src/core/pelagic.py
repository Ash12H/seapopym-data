"""Utilities for adding pelagic layer depths to observation datasets.

Loads zeu and pelagic_layer_depth from the global forcing zarr and matches
them to observation times at a given station location.
"""

from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

PELAGIC_ZARR = Path(__file__).resolve().parent.parent.parent / "data" / "pelagic_depths.zarr"

# Layer names matching Z index 0, 1, 2
LAYER_NAMES = ["surface", "migrant", "deep"]
LAYER_FACTORS = [1.5, 4.5, 10.5]  # multiples of zeu


def add_pelagic_depths(
    df: pd.DataFrame,
    lat: float,
    lon: float,
    zarr_path: Path | str = PELAGIC_ZARR,
) -> pd.DataFrame:
    """Add zeu and pelagic layer depths to an observation DataFrame.

    Extracts daily zeu and pelagic_layer_depth at the nearest grid cell to
    (lat, lon), then matches to the observation times in `df`.

    Parameters
    ----------
    df : pd.DataFrame
        Observation DataFrame with a 'time' column (datetime64).
    lat, lon : float
        Station coordinates.
    zarr_path : Path
        Path to the pelagic_depths.zarr.

    Returns
    -------
    pd.DataFrame
        Input DataFrame with added columns: zeu, layer_depth_surface,
        layer_depth_migrant, layer_depth_deep.
    """
    forcing = xr.open_zarr(zarr_path)

    # Select nearest grid cell
    point = forcing.sel(Y=lat, X=lon, method="nearest")

    # Match to observation dates: normalize both to date (no hour)
    obs_times = df["time"].values
    forcing_dates = point["T"].values.astype("datetime64[D]")
    obs_dates = np.array(obs_times, dtype="datetime64[D]")

    # For each obs time, find nearest forcing date
    zeu_values = np.full(len(obs_times), np.nan)
    layer_values = {name: np.full(len(obs_times), np.nan) for name in LAYER_NAMES}

    for i, od in enumerate(obs_dates):
        idx = np.argmin(np.abs(forcing_dates - od))
        # Only match if within 1 day
        if np.abs(forcing_dates[idx] - od) <= np.timedelta64(1, "D"):
            zeu_values[i] = float(point["zeu"].isel(T=idx).values)
            for j, name in enumerate(LAYER_NAMES):
                layer_values[name][i] = float(
                    point["pelagic_layer_depth"].isel(T=idx, Z=j).values
                )

    # Add columns to DataFrame
    df = df.copy()
    df["zeu"] = zeu_values
    for name in LAYER_NAMES:
        df[f"layer_depth_{name}"] = layer_values[name]

    # Report coverage
    n_valid = np.sum(~np.isnan(zeu_values))
    n_total = len(obs_times)
    print(f"  Pelagic depths: matched {n_valid}/{n_total} obs times")
    if n_valid < n_total:
        n_miss = n_total - n_valid
        print(f"  ⚠ {n_miss} obs outside forcing period (1998-2022)")

    return df
