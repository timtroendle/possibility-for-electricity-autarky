"""Module to Determine share of shared coast between eez and administrative regions."""
from textwrap import dedent
from multiprocessing import Pool
from itertools import cycle

import click
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.prepared import prep

DRIVER = "GeoJSON"


@click.command()
@click.argument("path_to_regions")
@click.argument("path_to_eezs")
@click.argument("path_to_output")
@click.argument("threads", type=click.INT)
def allocate_eezs(path_to_regions, path_to_eezs, path_to_output, threads):
    """Determine share of shared coast between eez and administrative regions."""
    regions = gpd.read_file(path_to_regions)
    regions.set_index("id", inplace=True)
    eezs = gpd.read_file(path_to_eezs)
    with Pool(threads) as pool:
        share_of_coast_length = pool.map(
            _share_of_coast_length,
            zip((eez[1] for eez in eezs.iterrows()), cycle([regions]))
        )
    share = pd.DataFrame(
        index=regions.index,
        data=dict(zip(eezs["id"].values, share_of_coast_length))
    )
    assert (
        ((share.sum() > 0.99) & (share.sum() < 1.01)) |
        (share.sum() == 0.0)
    ).all(), share.sum()
    share.to_csv(path_to_output, header=True)


def _share_of_coast_length(args):
    # How to determine the length of the shared coast?
    # I intersect eez with the region and determine the length of the resulting polygon.
    # This approach is fairly rough, but accurate enough for this analysis.
    eez = args[0]
    regions = args[1]
    length_of_shared_coast = pd.Series(data=0.0, index=regions.index, dtype=np.float32)
    prep_eez = prep(eez["geometry"]) # increase performance
    intersection_mask = ((regions["country_code"] == eez["ISO_Ter1"]) &
                         (regions["geometry"].map(lambda region: prep_eez.intersects(region))))
    if intersection_mask.sum() == 0:
        msg = dedent("""No shared coast found for {}.
        Ignoring eez with area {} km^2.""".format(
            eez["GeoName"],
            eez["Area_km2"]
        ))
        print(msg)
        share = length_of_shared_coast.copy()
    elif intersection_mask.sum() == 1:
        # performance improvement in cases where only one region matches
        share = length_of_shared_coast.copy()
        share[intersection_mask] = 1
    else:
        length_of_shared_coast[intersection_mask] = regions.loc[intersection_mask, "geometry"].map(
            lambda region: eez["geometry"].intersection(region).length
        )
        share = length_of_shared_coast / length_of_shared_coast.sum()
    return share


if __name__ == "__main__":
    allocate_eezs()
