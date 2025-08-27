# Script to interpolate Aragonite so that no Nan is left.
import xarray as xr
import numpy as np
# charger l'aragonite
print("Load Aragonite")
path = '/data/rd_exchange/sroyer/SEAPOPYM/daily_aragonite_global_1998_2022.nc'
ds_ar = xr.open_dataarray(path)

ds_ar = ds_ar.rename({'lon':'longitude','lat':'latitude'}) 

acidity =ds_ar
acidity.attrs['units'] = "dimensionless"
acidity["time"].attrs["standard_name"]="time"
acidity["time"].attrs["axis"]="T"
acidity["latitude"].attrs["standard_name"]="latitude"
acidity["latitude"].attrs["axis"]="Y"
acidity["longitude"].attrs["standard_name"]="longitude"
acidity["longitude"].attrs["axis"]="X" 

print("Interpolate Aragonite")
# interpoler sur les latiudes
ar_lat=acidity.interpolate_na(dim='latitude', method='linear')
# interpoler sur les longitudes
ar_lon=acidity.interpolate_na(dim='longitude', method='linear')
# faire la moyenne des 2
# Créer un masque pour savoir où chacun est défini
is_valid_lat = ~np.isnan(ar_lat)
is_valid_lon = ~np.isnan(ar_lon)

# Fusionner intelligemment
ar_filled = xr.where(is_valid_lat & is_valid_lon, 
                     (ar_lat + ar_lon) / 2,   # moyenne quand les 2 sont définis
                     xr.where(is_valid_lat, ar_lat, ar_lon))  # sinon celui qui est défini

# Charger le masque
ds_forcings = xr.open_zarr('/data/rd_exchange/sroyer/SEAPOPYM/Sophie_GLOBAL_MULTIYEAR_BGC_001_033.zarr')
mask = ds_forcings['mask'] 
#  Masquer le ds
ar_filled = ar_filled.where(mask) 

# Sauvegarder le ds
ar_filled.to_netcdf('/data/rd_exchange/sroyer/SEAPOPYM/d_filled_aragonite_global_1998_2022.nc')
print("Omega Aragonite Saved")