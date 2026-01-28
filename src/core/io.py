import pandas as pd
import xarray as xr
from pathlib import Path
from typing import Union

class DataLoader:
    """Standardized data loader for Seapopym data processing."""
    
    @staticmethod
    def load_csv(path: Union[str, Path], **kwargs) -> pd.DataFrame:
        """Load a CSV file using Pandas with standard options."""
        return pd.read_csv(Path(path), **kwargs)

    @staticmethod
    def load_parquet(path: Union[str, Path], **kwargs) -> pd.DataFrame:
        """Load a Parquet file using Pandas."""
        return pd.read_parquet(Path(path), **kwargs)

    @staticmethod
    def load_nc(path: Union[str, Path], **kwargs) -> xr.Dataset:
        """Load a NetCDF file using Xarray."""
        return xr.open_dataset(Path(path), **kwargs)

class DataWriter:
    """Standardized data writer for Seapopym data processing."""

    @staticmethod
    def save_nc(ds: xr.Dataset, path: Union[str, Path], **kwargs) -> None:
        """Save an Xarray Dataset to NetCDF with standard compression."""
        # Standard encoding/compression could be enforced here
        comp = dict(zlib=True, complevel=5)
        encoding = {var: comp for var in ds.data_vars}
        ds.to_netcdf(Path(path), encoding=encoding, **kwargs)
        print(f"Saved NetCDF to {path}")

