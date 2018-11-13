"""Create maps of time averaged capacitfy factors of renewables."""
import click
import numpy as np
import rasterio
import xarray as xr

from src.capacityfactors.timeseries import CAPACITY_FACTOR_VAR

DTYPE = np.float32


@click.command()
@click.argument("path_to_id_map")
@click.argument("path_to_timeseries")
@click.argument("path_to_output")
def averages_map(path_to_id_map, path_to_timeseries, path_to_output):
    """Create maps of time averaged capacitfy factors of renewables."""
    with rasterio.open(path_to_id_map, "r") as f_ids:
        ids = f_ids.read(1)
        meta = f_ids.meta
    averages = map_id_to_average_capacity_factor(ids, path_to_timeseries, meta)
    meta["dtype"] = DTYPE
    with rasterio.open(path_to_output, "w", **meta) as f_avg:
        f_avg.write(averages, 1)


def map_id_to_average_capacity_factor(ids, path_to_timeseries, meta):
    average_capacity_factors = xr.open_dataset(path_to_timeseries).mean("time")[CAPACITY_FACTOR_VAR].to_dataframe()
    average_capacity_factors.index = average_capacity_factors.index.astype(np.int32)
    average_capacity_factors = average_capacity_factors.to_dict()[CAPACITY_FACTOR_VAR]
    average_capacity_factors[meta["nodata"]] = meta["nodata"]
    mapping_function = np.vectorize(
        lambda site_id: average_capacity_factors[site_id],
        otypes=[DTYPE]
    )
    return mapping_function(ids)


if __name__ == "__main__":
    averages_map()
