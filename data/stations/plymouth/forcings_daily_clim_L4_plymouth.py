# imports
import xarray as xr
from tqdm import tqdm
import gc
# ===================
# Load all datasets
# ===================
print("Loading Datasets")
# Set year and month ranges
years = range(1998, 2017)  # From 1998 to 2017 (1988-1997 not available)
months = ['{:02d}'.format(i) for i in range(1, 13)]  # Months from 01 to 12

# Function to get valid days for each month (excluding Feb 29)
def get_valid_days(month):
    if month == '02':  # February
        # Days in February (28 days for all years)
        return ['{:02d}'.format(day) for day in range(1, 29)]  # Exclude 29th Feb
    elif month in ['04', '06', '09', '11']:  # April, June, September, November
        return ['{:02d}'.format(day) for day in range(1, 31)]  # 30 days
    else:  # Jan, Mar, May, Jul, Aug, Oct, Dec
        return ['{:02d}'.format(day) for day in range(1, 32)]  # 31 days
    
#base directory
dir='/data/rd_exchange/amignot/SEAPODYM_FPHY/' # Temperature + pelagic layer depth

# Prepare the file path pattern for xr.open_mfdataset
file_paths_T = []
for year in tqdm(years, desc="Processing CMEMS Datasets"):
    for month in months:
        valid_days = get_valid_days(month)
        for day in valid_days:
            file_path_T = f'{year}/{month}/cmems_mod_glo_bgc_my_0.083deg-lmtl-Fphy_PT1D-I_{year}{month}{day}.nc'
            file_paths_T.append(dir+file_path_T)

# Open all datasets
ds_phys = xr.open_mfdataset(file_paths_T, combine='by_coords',decode_times=True)

# ===================
# Compute spatial means
# ===================
print("Compute temporal means")
# Select Area of L4 Plymouth station station + surface layer
ds_phys_sel = ds_phys.sel(
    latitude=50.25,     
    longitude=slice(-4.25, -4.15),   
    depth=1                         
).drop_vars("depth")

import gc  # Garbage collector

# delete the big original datasets
del ds_phys
gc.collect()  # Free memory

# Extract variables
ds_temp=ds_phys_sel['T'] # Temperature
ds_pelagic_layer_depth=ds_phys_sel['pelagic_layer_depth']


# Spatial Mean
ds_temp=ds_temp.mean(dim=['longitude'])
ds_pelagic_layer_depth=ds_pelagic_layer_depth.mean(dim=['longitude'])


# ===================
# Save results
# ===================
print("Saving results")
# Daily values 
ds_temp.to_netcdf('/data/rd_exchange/sroyer/SEAPOPYM/daily_temp_L4_plymouth_1998_2017.nc')
print("Daily L4 Plymouth Temperature Saved")
ds_pelagic_layer_depth.to_netcdf('/data/rd_exchange/sroyer/SEAPOPYM/daily_pelagiclayerdepth_L4_plymouth_1998_2017.nc')
print("Daily L4 Plymouth Pelagic Layer Depth Saved")
