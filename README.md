# Seapopym-data

Standardize the observation data used by SeapoPym.

## Folder structure

Data folder is organized as follows:

-   data
    -   \<location\>
        -   1_raw : raw data extracted from the source + metadata as markdown file.
        -   2_preprocessed: data pre-processed in CSV format and netcdf (including metadata), cleaned and normalized. No loss of information (round, ceiling, etc...).
        -   3_post_processed: union of all pre-processed data in a single HDF5 style file. Usable by Seapopym.
        -   scripts
            -   0_request : When the data is available on the Web we can request it using an API.
            -   1_preprocessed : Clean the data in each dataset.
            -   2_post_processed : Gather the data in a single usable product.
    -   **zooplankton_product** : This is where you will find the product in a complient format. The format is NetCDF and all necessary metadata are available for the integration of the Pint and CF_xarray libraries.

## What data should be included in the Seapopym data?

Not all data is always available. SeapoPym-data will try to standardize the available data to make them usable by SeapoPym.

List of data to include :

-   Temperature
-   Surface wind
-   Dissolved oxygen
-   Chlorophyll a
-   Primary production
-   Phytoplankton groups
-   Zooplankton groups

## Output resolution

-   Temporal resolution: daily
-   Spatial resolution: 1 degree

## How to vizualize the process

Open the notebook in the `data/stations/<location>/scripts` folder and run the cells.

You can also use the voila command to run the notebook as a standalone web application.

```bash
voila <notebook>.ipynb
```
