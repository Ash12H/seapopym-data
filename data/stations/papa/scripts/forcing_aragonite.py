# imports
import xarray as xr
from tqdm import tqdm
import gc
import xesmf as xe
import numpy as np
# ===================
# Load all datasets
# ===================
print("Loading Datasets")
# Set year and month ranges
years = range(1998, 2023)  # From 1998 to 2022
months = ['{:02d}'.format(i) for i in range(1, 13)]  # Months from 01 to 12

    
#base directory
dir='/data/rd_exchange/amignot/MULTIOBS_GLO_BIO_CARBON_SURFACE_MYNRT_015_008/cmems_obs-mob_glo_bgc-car_my_irr-i_202411/' 

# Prepare the file path pattern for xr.open_mfdataset
file_paths = []
# add december 1997 for coherent daily interpolation
file_paths.append(dir+'1997/cmems_obs-mob_glo_bgc-car_my_irr-i_199712.nc')
for year in tqdm(years, desc="Processing CMEMS Datasets"):
    for month in months:
        file_path = f'{year}/cmems_obs-mob_glo_bgc-car_my_irr-i_{year}{month}.nc'
        file_paths.append(dir+file_path)
# add january 2023 for coherent daily interpolation 
file_paths.append(dir+'2023/cmems_obs-mob_glo_bgc-car_my_irr-i_202301.nc')        
# Open all datasets
ds_ar = xr.open_mfdataset(file_paths, combine='by_coords',decode_times=True)
data_ar=ds_ar['omega_ar'] # Aragonite sursaturation

# ===================
# convert longitudes 0;360 into -180;180
# ===================

data_ar = data_ar.assign_coords(longitude=(((data_ar.longitude + 180) % 360) - 180)).sortby('longitude')

# ===================
# Delete original dataset to free memory
# ===================
del ds_ar
gc.collect()  # Free memory

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
regridder = xe.Regridder(data_ar, target_grid, method='bilinear', periodic=True)

data_ar_regridded = regridder(data_ar)
del data_ar
gc.collect()
# ===================
# Interpolate into daily values (from monthly values)
# ===================
print("Interpolating to daily time resolution...")
data_ar_daily = data_ar_regridded.resample(time='1D').interpolate('linear')
#then remove december 1997 and january 2023
data_ar_daily=data_ar_daily.sel(
    time=slice('1998-01-01', '2022-12-31'),
    lat=slice(-80,89)
)
# ===================
# Save results
# ===================
print("Saving extracted aragonite")

data_ar_daily.to_netcdf('/data/rd_exchange/sroyer/SEAPOPYM/daily_aragonite_global_1998_2020.nc')
print("Omega Aragonite Saved")
