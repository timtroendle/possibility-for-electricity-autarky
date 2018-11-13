"""Create index capacity factor timeseries of renewables."""
from pathlib import Path

import click
import xarray as xr

SIM_ID_DIMENSION = "sim_id"
SITE_ID_VAR = "site_id"
WEIGHT_VAR = "weight"
CAPACITY_FACTOR_VAR = "electricity"
WEIGHTED_CAPACITY_FACTOR_VAR = "weighted_electricity"
ORIENTATION_VAR = "orientation"
FLAT_SURFACE = "flat"
FILE_SUFFIX = "nc"


@click.command()
@click.argument("path_to_folder")
@click.argument("path_to_output")
def timeseries(path_to_folder, path_to_output):
    """Create index capacity factor timeseries of renewables from seperate renewables.ninja runs."""
    ds = merge_time_series_in_folder(path_to_folder)
    if "open-field-pv" in path_to_folder:
        ds = select_flat_surfaces_only(ds)
    ds = groupby_sites(ds)

    ds.to_netcdf(path_to_output, "w")


def merge_time_series_in_folder(path_to_folder):
    path_to_folder = Path(path_to_folder)
    return xr.concat(
        [xr.open_dataset(path_to_file) for path_to_file in path_to_folder.glob(f"*.{FILE_SUFFIX}")],
        dim=SIM_ID_DIMENSION
    )


def groupby_sites(ds):
    ds[CAPACITY_FACTOR_VAR] = ds[CAPACITY_FACTOR_VAR] * ds[WEIGHT_VAR]
    return ds.groupby(SITE_ID_VAR).mean(dim=SIM_ID_DIMENSION)


def select_flat_surfaces_only(ds):
    ds = ds.sel({SIM_ID_DIMENSION: ds[ORIENTATION_VAR] == FLAT_SURFACE})
    ds[WEIGHT_VAR] = 1 # there is only one simulation per site, hence weight must be one
    return ds


if __name__ == "__main__":
    timeseries()
