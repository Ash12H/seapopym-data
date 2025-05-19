# imports
import xarray as xr
from tqdm import tqdm
import gc
# ===================
# Load all datasets
# ===================
print("Loading Datasets")
# Set year and month ranges
years = range(1998, 2021)  # From 1998 to 2020
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
dir_pp='/data/rd_exchange/amignot/SEAPODYM/' # Primary Productivity

# Prepare the file path pattern for xr.open_mfdataset
file_paths_T = []
file_paths_pp = []
for year in tqdm(years, desc="Processing CMEMS Datasets"):
    for month in months:
        valid_days = get_valid_days(month)
        for day in valid_days:
            file_path_T = f'{year}/{month}/cmems_mod_glo_bgc_my_0.083deg-lmtl-Fphy_PT1D-I_{year}{month}{day}.nc'
            file_paths_T.append(dir+file_path_T)
            file_path_pp = f'{year}/{month}/cmems_mod_glo_bgc_my_0.083deg-lmtl_PT1D-I_{year}{month}{day}.nc'
            file_paths_pp.append(dir_pp+file_path_pp)
# Open all datasets
ds_phys = xr.open_mfdataset(file_paths_T, combine='by_coords',decode_times=True)
ds_bio = xr.open_mfdataset(file_paths_pp, combine='by_coords',decode_times=True)

# ===================
# Compute spatial and temporal means
# ===================
print("Compute spatial and temporal means")
# Select Area of Papa station + surface layer
ds_phys_2deg = ds_phys.sel(
    latitude=slice(48.5, 50.5),  
    longitude=slice(-130.5, -128.5),
    depth=1 # Selection of the layer one : epipelagic layer
).drop_vars('depth')
# ds_pp just no depth dim, everything at the surface
ds_bio_2deg = ds_bio.sel(
    latitude=slice(48.5, 50.5),  
    longitude=slice(-130.5, -128.5),
)
import gc  # Garbage collector

# delete the big original datasets
del ds_phys
del ds_bio
gc.collect()  # Free memory

# Extract variables
ds_temp=ds_phys_2deg['T'] # Temperature
ds_pelagic_layer_depth=ds_phys_2deg['pelagic_layer_depth']
ds_pp=ds_bio_2deg['npp'] # net primary production

# Spatial Mean
ds_temp=ds_temp.mean(dim=['latitude','longitude'])
ds_pelagic_layer_depth=ds_pelagic_layer_depth.mean(dim=['latitude','longitude'])
ds_pp=ds_pp.mean(dim=['latitude','longitude'])

# Temporal mean
# define dayofyear to avoid problem with leap year 
#(29/02 ignored in the loading of the datasets, so with this method dayofyear= 365 days)
dayofyear = ds_temp['time'].dt.strftime('%m-%d').data  # 'MM-DD' string
ds_temp.coords['day'] = ('time', dayofyear)
ds_pelagic_layer_depth.coords['day'] = ('time', dayofyear)
ds_pp.coords['day'] = ('time', dayofyear)

temp_clim=ds_temp.groupby('day').mean('time')
pelagic_lyr_depth_clim=ds_pelagic_layer_depth.groupby('day').mean('time')
pp_clim=ds_pp.groupby('day').mean('time')

# ===================
# Save results
# ===================
print("Saving results")
# Daily Climatologies
temp_clim.to_netcdf('/data/rd_exchange/sroyer/SEAPOPYM/daily_clim_temp_papa_1998_2020.nc')
print("Papa Temperature Climatology Saved")
pelagic_lyr_depth_clim.to_netcdf('/data/rd_exchange/sroyer/SEAPOPYM/daily_clim_pelagiclayerdepth_papa_1998_2020.nc')
print("Papa Pelagic Layer Depth Climatology Saved")
pp_clim.to_netcdf('/data/rd_exchange/sroyer/SEAPOPYM/daily_clim_pp_papa_1998_2020.nc')
print("Papa Primary Productivity Climatology Saved")
# Daily values in the 2 deg area
ds_temp.to_netcdf('/data/rd_exchange/sroyer/SEAPOPYM/daily_temp_papa_1998_2020.nc')
print("Daily Papa Temperature Saved")
ds_pelagic_layer_depth.to_netcdf('/data/rd_exchange/sroyer/SEAPOPYM/daily_pelagiclayerdepth_papa_1998_2020.nc')
print("Daily Papa Pelagic Layer Depth Saved")
ds_pp.to_netcdf('/data/rd_exchange/sroyer/SEAPOPYM/daily_pp_papa_1998_2020.nc')
print("Daily Papa Primary Productivity Saved")