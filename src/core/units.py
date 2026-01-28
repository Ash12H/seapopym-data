import pint
import pint_xarray
import xarray as xr
import pandas as pd
from typing import Dict

# Initialize Pint registry
ureg = pint.UnitRegistry()
pint_xarray.setup_registry(ureg)


class UnitManager:
    """Standardized unit manager using Pint."""

    STANDARD_UNITS = {
        "temperature": "degC",
        "salinity": "dimensionless",  # PSU essentially
        "depth": "m",
        "biomass": "mg / m^3",  # Example standard
        "abundance": "count / m^3",
    }

    @staticmethod
    def convert_column(
        df: pd.DataFrame, col: str, from_unit: str, to_unit: str
    ) -> pd.DataFrame:
        """Convert a DataFrame column from one unit to another."""
        if col not in df.columns:
            return df

        quantity = ureg.Quantity(df[col].values, from_unit)
        converted = quantity.to(to_unit)
        df[col] = converted.magnitude
        return df

    @staticmethod
    def enforce_units(ds: xr.Dataset, unit_map: Dict[str, str]) -> xr.Dataset:
        """Enforce standard units on an Xarray Dataset."""
        ds_out = ds.copy()
        for var, unit in unit_map.items():
            if var in ds_out:
                try:
                    # If it already has units, convert
                    if "units" in ds_out[var].attrs:
                        _ = ds_out[var].attrs["units"]
                        # Logic to convert using pint could be added here
                        # if Xarray integration is full
                        # For now, we assume simple checks or manual overrides
                        pass

                    ds_out[var].attrs["units"] = unit
                except Exception as e:
                    print(f"Warning: Could not set units for {var}: {e}")
        return ds_out
