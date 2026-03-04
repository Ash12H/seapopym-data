"""
PAPA Per-Station Processing Script
Produces one time-series NetCDF per fixed station (like HOT/BATS format).
Target stations: P08, P12, P16, P20, P26, LBP7, CS01 (>30 observations each).
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
import xarray as xr
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.append(str(PROJECT_ROOT / "src"))

# Stations with >30 observations
TARGET_STATIONS = ["P08", "P12", "P16", "P20", "P26", "LBP7", "CS01"]


def load_and_prepare(input_file: Path) -> pd.DataFrame:
    """Steps 1-7 and 9 from process.py: load through sum taxa (no spatial binning)."""

    # 1. Load
    print("Loading data...")
    df = pd.read_csv(
        input_file, sep=";", decimal=",", on_bad_lines="skip", low_memory=False
    )
    print(f"  Loaded {len(df)} rows")

    # 2. Identify taxonomic columns (before adding new cols)
    taxa_cols = df.columns[20:].tolist()
    excluded_taxa = [
        "ANNE:POLY: >> POLY s1",
        "ANNE:POLY: >> POLY s2",
        "ANNE:POLY: >> POLY s3",
    ]
    taxa_cols_to_sum = [col for col in taxa_cols if col not in excluded_taxa]
    print(f"  {len(taxa_cols_to_sum)} taxa to sum ({len(excluded_taxa)} excluded)")

    # 3. Clean columns
    df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
    df["lon"] = pd.to_numeric(df["lon"], errors="coerce")
    df["DEPTH_STRT"] = pd.to_numeric(df["DEPTH_STRT"], errors="coerce")

    # 4. Filter depth >= 50m
    n_before = len(df)
    df = df[df["DEPTH_STRT"] >= 50]
    print(f"  Filtered depth<50m: {n_before} -> {len(df)} rows")

    # 5. Temporal processing
    df["time"] = pd.to_datetime(df["Date"], format="%d %m %Y", errors="coerce")
    df["date"] = df["time"].dt.floor("D")

    def extract_hour(stn_time):
        try:
            time_str = str(stn_time).strip().zfill(4)
            if len(time_str) > 4:
                time_str = time_str.split(".")[0].zfill(4)
            hh = int(time_str[:2])
            if hh == 24:
                hh = 0
            return hh
        except Exception:
            return None

    df["hour"] = df["STN_TIME"].apply(extract_hour)
    df["day_night"] = df["Twilight"].apply(
        lambda x: "day" if x == "Daylight" else "night"
    )

    # 6. Depth categorization
    df["depth_category"] = np.where(
        df["DEPTH_STRT"] <= 150, "epipelagic_only", "epipelagic_mesopelagic"
    )

    # 7. Store tow metadata
    df["tow_depth_max"] = df["DEPTH_STRT"]

    # 9. Sum taxa
    df["biomass_dry"] = df[taxa_cols_to_sum].sum(axis=1)
    print(f"  Summed {len(taxa_cols_to_sum)} taxa into biomass_dry")

    return df


def process_station(
    df: pd.DataFrame, station_name: str, release_dir: Path
) -> dict | None:
    """Process a single station into a time-series NetCDF. Returns station info dict."""

    sdf = df[df["Station"] == station_name].copy()
    n_rows = len(sdf)
    if n_rows == 0:
        print(f"  {station_name}: no data, skipping")
        return None

    # Median coordinates as fixed station position
    station_lat = float(sdf["lat"].median())
    station_lon = float(sdf["lon"].median())

    # Identify tows (same date + same depth start = same tow)
    sdf["tow_id"] = sdf.groupby(["date", "DEPTH_STRT"]).ngroup()
    n_tows = sdf["tow_id"].nunique()

    # Aggregation L1: mean per tow
    agg1 = (
        sdf.groupby(["date", "day_night", "depth_category", "tow_id"])
        .agg({"biomass_dry": "mean", "tow_depth_max": "first"})
        .reset_index()
    )

    # Aggregation L2: median per day/category
    final = (
        agg1.groupby(["date", "day_night", "depth_category"])
        .agg({"biomass_dry": "median", "tow_depth_max": "median"})
        .reset_index()
    )

    # Convert to xarray
    ds = xr.Dataset.from_dataframe(
        final.set_index(["date", "depth_category", "day_night"])
    )
    ds = ds.rename({"date": "time"})

    # Add lat/lon as size-1 dimensions
    ds = ds.expand_dims(lat=[station_lat], lon=[station_lon])

    # Metadata
    ds.attrs["title"] = f"PAPA {station_name} Zooplankton Observations"
    ds.attrs["station"] = station_name
    ds.attrs["station_lat"] = station_lat
    ds.attrs["station_lon"] = station_lon
    ds.attrs["source"] = "DFO Canada Zooplankton Database"
    ds.attrs["institution"] = "DFO (Department of Fisheries and Oceans Canada)"
    ds.attrs["net_type"] = "Bongo (majority), mesh 236 µm"
    ds.attrs["processing_date"] = datetime.now().isoformat()
    ds.attrs["excluded_data"] = (
        "depth <50m, adult polychaetes (ANNE:POLY s1, s2, s3 - benthic)"
    )
    ds.attrs["conventions"] = "CF-1.8"
    ds.attrs["data_period"] = (
        f"{sdf['time'].min().date()} to {sdf['time'].max().date()}"
    )

    ds["biomass_dry"].attrs = {
        "units": "mg m-3",
        "long_name": "Dry weight biomass concentration",
        "comment": "Sum of 91 planktonic taxa (excludes adult polychaetes)",
    }
    ds["tow_depth_max"].attrs = {
        "units": "m",
        "long_name": "Maximum tow depth",
    }
    ds["lat"].attrs = {
        "units": "degrees_north",
        "long_name": "Latitude",
        "standard_name": "latitude",
        "axis": "Y",
    }
    ds["lon"].attrs = {
        "units": "degrees_east",
        "long_name": "Longitude",
        "standard_name": "longitude",
        "axis": "X",
    }
    ds["time"].attrs = {
        "long_name": "Time",
        "standard_name": "time",
        "axis": "T",
    }
    ds["depth_category"].attrs = {
        "long_name": "Depth category",
        "description": "Categorization based on maximum tow depth",
        "epipelagic_only": "Tows 0-150m",
        "epipelagic_mesopelagic": "Tows >150m",
    }

    # Save
    out_file = release_dir / f"papa_{station_name}_obs.nc"
    ds.to_netcdf(out_file, mode="w")

    n_obs = len(final)
    print(
        f"  {station_name}: {n_rows} rows, {n_tows} tows -> {n_obs} obs "
        f"({station_lat:.2f}N, {station_lon:.2f}E) -> {out_file.name}"
    )
    return {
        "station": station_name,
        "n_rows": n_rows,
        "n_tows": n_tows,
        "n_obs": n_obs,
        "lat": station_lat,
        "lon": station_lon,
        "period_start": sdf["time"].min().date(),
        "period_end": sdf["time"].max().date(),
        "final": final,
        "biomass_stats": final["biomass_dry"].describe(),
    }


def generate_figure(station_results: list[dict], figures_dir: Path):
    """Generate a combined time series figure for all stations."""
    import matplotlib.pyplot as plt

    n = len(station_results)
    fig, axes = plt.subplots(n, 1, figsize=(14, 3 * n), sharex=True)
    if n == 1:
        axes = [axes]

    # Only epipelagic_only+day is distinct (G0 only, DVM migrants are deep).
    # The other 3 combinations (epi night, epi+meso day, epi+meso night) all
    # capture G0+G1, so we group them as a single category.
    cat_style = {
        "Epipelagic day (G0)": {"color": "#2196F3", "marker": "o"},
        "G0+G1": {"color": "#FF5722", "marker": "s"},
    }

    for ax, info in zip(axes, station_results):
        final = info["final"]
        is_epi_day = (final["depth_category"] == "epipelagic_only") & (
            final["day_night"] == "day"
        )
        groups = [
            ("Epipelagic day (G0)", final[is_epi_day]),
            ("G0+G1", final[~is_epi_day]),
        ]
        for label, subset in groups:
            if subset.empty:
                continue
            style = cat_style[label]
            ax.plot(
                subset["date"],
                subset["biomass_dry"],
                marker=style["marker"],
                linestyle="-",
                color=style["color"],
                alpha=0.7,
                markersize=3,
                linewidth=0.8,
                label=label,
            )
        ax.set_ylabel("mg/m\u00b3")
        ax.set_title(
            f"{info['station']} ({info['lat']:.2f}\u00b0N, {info['lon']:.2f}\u00b0E)"
            f" \u2014 {info['n_obs']} obs",
            fontsize=11,
            fontweight="bold",
            loc="left",
        )
        ax.grid(True, alpha=0.3)

    # Legend only in first subplot
    axes[0].legend(fontsize=8, loc="upper right")

    axes[-1].set_xlabel("Date")
    fig.suptitle(
        "PAPA Per-Station Zooplankton Biomass Time Series",
        fontsize=14,
        fontweight="bold",
        y=1.0,
    )
    plt.tight_layout(rect=[0, 0, 1, 0.97])
    out = figures_dir / "stations_time_series.png"
    plt.savefig(out, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Figure saved: {out.name}")


def generate_report(
    station_results: list[dict], report_file: Path, n_initial: int, n_filtered: int
):
    """Generate a markdown report summarizing all station outputs."""
    with open(report_file, "w") as f:
        f.write("# PAPA Per-Station Report\n\n")
        f.write(f"**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**Stations**: {len(station_results)}\n\n")

        f.write("## Summary\n\n")
        f.write(f"- Initial rows (all stations, after depth filter): {n_filtered:,}\n")
        f.write(
            f"- Stations processed: {', '.join(r['station'] for r in station_results)}\n"
        )
        total_obs = sum(r["n_obs"] for r in station_results)
        f.write(f"- Total final observations: {total_obs:,}\n\n")

        f.write("## Stations\n\n")
        f.write("| Station | Rows | Tows | Observations | Lat | Lon | Period |\n")
        f.write("|---------|------|------|-------------|-----|-----|--------|\n")
        for r in station_results:
            f.write(
                f"| {r['station']} | {r['n_rows']} | {r['n_tows']} | {r['n_obs']} "
                f"| {r['lat']:.2f} | {r['lon']:.2f} "
                f"| {r['period_start']} to {r['period_end']} |\n"
            )
        f.write("\n")

        f.write("### Biomass Statistics (mg/m\u00b3)\n\n")
        f.write("| Station | Mean | Median | Min | Max |\n")
        f.write("|---------|------|--------|-----|-----|\n")
        for r in station_results:
            s = r["biomass_stats"]
            f.write(
                f"| {r['station']} | {s['mean']:.2f} | {s['50%']:.2f} "
                f"| {s['min']:.2f} | {s['max']:.2f} |\n"
            )
        f.write("\n")

        f.write("## Figures\n\n")
        f.write("![Time Series](figures/stations_time_series.png)\n\n")

        f.write("## Methodology\n\n")
        f.write("**Source**: DFO Canada Zooplankton Database\n\n")
        f.write("**Net**: Bongo (majority) with 236 \u00b5m mesh\n\n")
        f.write("**Taxonomic Groups**: 91 planktonic taxa (94 total - 3 benthic polychaetes)\n\n")
        f.write("**Aggregation**:\n")
        f.write("1. Sum of 91 taxa per sample row\n")
        f.write("2. Mean per tow (same date + depth)\n")
        f.write("3. Median of tows per day/depth_category\n\n")
        f.write("**Coordinates**: Median lat/lon per station (fixed point)\n\n")

        f.write("## Output Files\n\n")
        for r in station_results:
            f.write(f"- `papa_{r['station']}_obs.nc`\n")
        f.write("\n")

    print(f"  Report saved: {report_file.name}")


def main():
    STATION_DIR = PROJECT_ROOT / "src" / "papa"
    RAW_DIR = STATION_DIR / "data" / "raw"
    RELEASE_DIR = STATION_DIR / "release"
    REPORTS_DIR = STATION_DIR / "reports"
    FIGURES_DIR = REPORTS_DIR / "figures"

    RELEASE_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    INPUT_FILE = RAW_DIR / "papa_zooplankton.csv"

    print("=" * 60)
    print("PAPA Per-Station Processing")
    print("=" * 60)

    if not INPUT_FILE.exists():
        print(f"Error: {INPUT_FILE} not found.")
        return

    df = load_and_prepare(INPUT_FILE)
    n_filtered = len(df)

    # Show station counts
    station_counts = df["Station"].value_counts()
    print(f"\nTarget stations ({len(TARGET_STATIONS)}):")
    for s in TARGET_STATIONS:
        count = station_counts.get(s, 0)
        print(f"  {s}: {count} rows")
    print()

    # Process each station
    results = []
    for station in TARGET_STATIONS:
        info = process_station(df, station, RELEASE_DIR)
        if info is not None:
            results.append(info)

    print(f"\n{len(results)}/{len(TARGET_STATIONS)} station files created")

    # Generate figure and report
    if results:
        print("\nGenerating figure and report...")
        generate_figure(results, FIGURES_DIR)
        generate_report(
            results, REPORTS_DIR / "report_stations.md", len(df), n_filtered
        )

    print("\nDone.")


if __name__ == "__main__":
    main()
