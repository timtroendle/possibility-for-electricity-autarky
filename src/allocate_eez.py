"""Module to divide eez and allocate their parts to administrative regions."""
from textwrap import dedent
from multiprocessing import Pool
from itertools import cycle

import click
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.prepared import prep

from eligible_land import Eligibility

DRIVER = "GeoJSON"
OFFSHORE_ELIGIBILITY = Eligibility.OFFSHORE_WIND_FARM.property_name
REL_TOLERANCE = 0.005 # 0.5 %
ABS_TOLERANCE = 5 # km^2


@click.command()
@click.argument("path_to_regions")
@click.argument("path_to_eezs")
@click.argument("path_to_output")
@click.argument("threads", type=click.INT)
def allocate_eezs(path_to_regions, path_to_eezs, path_to_output, threads):
    """Divide eez and allocate their parts and eligibilities to administrative regions."""
    regions = gpd.read_file(path_to_regions)
    eezs = gpd.read_file(path_to_eezs)
    with Pool(threads) as pool:
        allocated_eligibilities = pool.map(
            _allocate_eez_eligibility,
            zip((eez[1] for eez in eezs.iterrows()), cycle([regions]))
        )
    regions[OFFSHORE_ELIGIBILITY] = sum(allocated_eligibilities)
    regions.to_file(path_to_output, driver=DRIVER)
    _test_allocation(path_to_eezs, path_to_output)


def _allocate_eez_eligibility(args):
    # How much offshore eligibility of a certain eez goes to which region?
    # I simply allocate offshore eligibility to all regions that share a coast with
    # the eez. The allocation is proportional to the lenght of the shared coastself.
    #
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
        Ignoring eez with area {} km^2 and offshore eligibility of {:.1f} km^2.""".format(
            eez["GeoName"],
            eez["Area_km2"],
            eez[OFFSHORE_ELIGIBILITY]
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
    return share * eez[OFFSHORE_ELIGIBILITY]


def _test_allocation(path_to_eezs, path_to_output):
    total_offshore = gpd.read_file(path_to_eezs)[OFFSHORE_ELIGIBILITY].sum()
    total_allocated = gpd.read_file(path_to_output)[OFFSHORE_ELIGIBILITY].sum()
    below_rel_threshold = abs(total_allocated - total_offshore) < total_offshore * REL_TOLERANCE
    below_abs_threshold = abs(total_allocated - total_offshore) < ABS_TOLERANCE
    below_any_threshold = below_rel_threshold | below_abs_threshold
    assert below_any_threshold,\
        dedent("""Allocated offshore eligibility differs more than {}% and more than {} km^2. Allocated was:
        {}

        Real offshore eligibility is:
        {}

        """.format(REL_TOLERANCE * 100,
                   ABS_TOLERANCE,
                   total_allocated,
                   total_offshore))


if __name__ == "__main__":
    allocate_eezs()
