# Seapopym-data

Standardize the observation data used by Seapopym.

## What data should be included in the Seapopym data?

Not all data is always available. Seapopym-data will try to standardize the available data to make them usable by Seapopym.

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

Open the notebook in the `data/<location>/scripts` folder and run the cells.

You can also use the voila command to run the notebook as a standalone web application.

```bash
voila <notebook>.ipynb
```

## Folder structure

Data folder is organized as follows:

-   data
    -   location
        -   1_raw : raw data extracted from the source + metadata as markdown file.
        -   2_preprocessed: data pre-processed in CSV format and netcdf (including metadata), cleaned and normalized. No loss of information (round, ceiling, etc...).
        -   3_post_processed: union of all pre-processed data in a single HDF5 style file. Usable by Seapopym.
        -   scripts
            -   1_preprocessed
            -   2_post_processed

## Process

Raw data is cleaned and saved (as preprocessed) with metadata in netcdf format. The preprocessed data is also available in CSV format for conveniance but without metadata.
In the raw directory, there is a `<dataset>_metadata.md` file that describes the dataset as :

-   Variable name
-   Standard name
-   Long name
-   Units
