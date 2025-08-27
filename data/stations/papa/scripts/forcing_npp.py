# imports
import xarray as xr
import gc
import xesmf as xe
import numpy as np
# ===================
# Load all datasets
# ===================
print("Loading Datasets")
directory="/scratch/sroyer/SEAPOPYM/NPP"
ds_cafe=xr.open_dataset(dir+"1998_2022_NPP_SILSBE_CAFE_25KM_8D.nc")['CAFE']
ds_west=xr.open_dataset(dir+"1998_2022_NPP_WESTBERRY_CBPM_25KM_8D.nc")['CbPM']
ds_behr=xr.open_dataset(dir+"1998_2022_NPP_BEHRENFELD_CBPM_25KM_8D.nc")['CbPM']

# ===================
# Regrid from 0.25° to 1° (using esmf)
# ===================
print("Regridding to 1° resolution")
# Define target grid
target_grid = {
    'lon': np.arange(-180, 180, 1),
    'lat': np.arange(-90,  90+1, 1),
}
# Build the regridder
regridder = xe.Regridder(ds_cafe, target_grid, method='bilinear', periodic=True)
# Regrid
cafe_regridded = regridder(ds_cafe)
west_regridded = regridder(ds_west)
behr_regridded = regridder(ds_behr)
del ds_cafe
del ds_west
del ds_behr
gc.collect()

# ===================
# Interpolate into daily values (from 8 day values)
# Replace missing values with VGPM values
# ===================
path_vgpm="/scratch/sroyer/SEAPOPYM/Sophie_GLOBAL_MULTIYEAR_BGC_001_033.zarr"
ds_vgpm=xr.open_zarr(path_vgpm)
da_vgpm=ds_vgpm['primary_production'].sel(latitude=slice(-80,80))
mask=ds_vgpm['mask'].sel(latitude=slice(-80,80))
with xr.set_options(keep_attrs=True):
        # primary production 
        ds_vgpm = ds_vgpm.where(mask)

def preprocess_production(prod_ds, vgpm_ref, mask):
    # Recalage temporel : interpolation linéaire à la résolution journalière
    prod_ds=prod_ds.rename({'lon': 'longitude','lat':'latitude'})
    prod_ds=prod_ds.sel(latitude=slice(-80,80))
    new_time = vgpm_ref.time
    prod_ds_interp = prod_ds.interp(time=new_time, method='linear')
    # Remplacer les NaN (en mer uniquement) par les valeurs VGPM
    prod_clean = prod_ds_interp.where(~prod_ds_interp.isnull() & mask, vgpm_ref)
    return prod_clean
cafe_clean=preprocess_production(cafe_regridded,da_vgpm,mask)
west_clean=preprocess_production(west_regridded,da_vgpm,mask)
behr_clean=preprocess_production(behr_regridded,da_vgpm,mask)

del cafe_regridded
del west_regridded
del behr_clean
gc.collect()
# ===================
# Save results
# ===================
print("Saving Cafe")
cafe_clean.to_netcdf(dir+'CAFE_daily_global_1deg.nc')
print("Saving CbPM Westberry")
west_clean.to_netcdf(dir+'CbPM_west_daily_global_1deg.nc')
print("Saving CbPM Behrenfeld")
behr_clean.to_netcdf(dir+'CbPM_behr_daily_global_1deg.nc')
print("All Datasets Saved")