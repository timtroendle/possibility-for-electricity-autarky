"""Create index capacity factor timeseries of renewables."""
import click
import xarray as xr

SIM_ID_DIMENSION = "site"
SITE_ID_VAR = "site_id"
LAT_VAR = "lat"
LON_VAR = "lon"
WEIGHT_VAR = "weight"
CAPACITY_FACTOR_VAR = "electricity"
WEIGHTED_CAPACITY_FACTOR_VAR = "weighted_electricity"
ORIENTATION_VAR = "_orientation"
FLAT_SURFACE = "flat"
FILE_SUFFIX = "nc"


@click.command()
@click.argument("path_to_input")
@click.argument("path_to_output")
def timeseries(path_to_input, path_to_output):
    """Create index capacity factor timeseries of renewables from seperate renewables.ninja runs."""
    ds = xr.open_dataset(path_to_input)
    if "open-field-pv" in path_to_input:
        ds = select_flat_surfaces_only(ds)
    ds = groupby_sites(ds)

    ds.to_netcdf(path_to_output, "w")


def groupby_sites(ds):
    ds[CAPACITY_FACTOR_VAR] = ds[CAPACITY_FACTOR_VAR] * ds[WEIGHT_VAR]
    cp = ds[[CAPACITY_FACTOR_VAR, SITE_ID_VAR]].groupby(SITE_ID_VAR).sum(dim=SIM_ID_DIMENSION)
    coords = ds[[LAT_VAR, LON_VAR, SITE_ID_VAR]].groupby(SITE_ID_VAR).first()
    return xr.merge([cp, coords])


def select_flat_surfaces_only(ds):
    ds = ds.sel({SIM_ID_DIMENSION: ds[ORIENTATION_VAR] == FLAT_SURFACE})
    ds[WEIGHT_VAR] = 1 # there is only one simulation per site, hence weight must be one
    return ds


if __name__ == "__main__":
    timeseries()
