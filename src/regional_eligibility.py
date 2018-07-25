"""Module to determine eligible land per region."""
from textwrap import dedent
from multiprocessing import Pool
from itertools import cycle

import click
import numpy as np
import pandas as pd
from shapely.geometry import shape
import fiona
import rasterio
import rasterio.mask
from rasterio.warp import calculate_default_transform, reproject, RESAMPLING
import geopandas as gpd

from eligible_land import Eligibility
from conversion import area_in_squaremeters

EQUAL_AREA_PROJECTION = "EPSG:3035" # projection to use to derive area sizes
INVALID_DATA = 255
REL_TOLERANCE = 0.015 # 1.5%
ABS_TOLERANCE = 3.5 # km^2


@click.group()
def regional_eligibility():
    pass


@regional_eligibility.command()
@click.argument("path_to_regions")
@click.argument("path_to_eligibility")
@click.argument("path_to_output")
@click.argument("threads", type=click.INT)
def land(path_to_regions, path_to_eligibility, path_to_output, threads):
    """Allocates eligible land to regions defined by vector data.

    Land is assumed to be land mass only, i.e. no maritime areas. Should any offshore
    eligibility be found, it is assumed to be wrong and converted to not eligible land.
    """
    _allocation_eligibility_to_regions(path_to_regions, path_to_eligibility, path_to_output,
                                       threads, offshore=False)


@regional_eligibility.command()
@click.argument("path_to_regions")
@click.argument("path_to_eligibility")
@click.argument("path_to_output")
@click.argument("threads", type=click.INT)
def offshore(path_to_regions, path_to_eligibility, path_to_output, threads):
    """Allocates eligible land to regions defined by vector data.

    Regions are assumed to be maritime/offshore regions.
    """
    _allocation_eligibility_to_regions(path_to_regions, path_to_eligibility, path_to_output,
                                       threads, offshore=True)


def _allocation_eligibility_to_regions(path_to_regions, path_to_eligibility, path_to_output, threads, offshore):
    eligibilities = [eligibility for eligibility in Eligibility]
    if not offshore:
        eligibilities.remove(Eligibility.OFFSHORE_WIND)
        eligibilities.remove(Eligibility.OFFSHORE_WIND_PROTECTED)
    with fiona.open(path_to_regions, "r") as regions:
        with Pool(threads) as pool:
            # start with largest (=slowest) region to optimise the multi processing
            sorted_regions = sorted(
                regions,
                key=lambda region: shape(region["geometry"]).area,
                reverse=True
            )
            new_regions = pool.map(
                _allocate_eligibility_to_region,
                zip(sorted_regions, cycle([path_to_eligibility]))
            )
        if not offshore:
            new_regions = _remove_offshore(new_regions)

        data = pd.DataFrame(
            index=[region["properties"]["id"] for region in new_regions],
            data={
                eligibility.area_column_name: [region["properties"][eligibility.area_column_name]
                                               for region in new_regions]
                for eligibility in eligibilities
            }
        ).reindex([region["properties"]["id"] for region in regions])
        data.index.name = "id"
        data.to_csv(path_to_output, header=True)
    _test_allocation(path_to_regions, path_to_output, offshore)


def _allocate_eligibility_to_region(args):
    region = args[0].copy()
    with rasterio.open(args[1], "r") as eligibility_raster:
        raster_crs = eligibility_raster.crs
        crop, crop_transform = rasterio.mask.mask(
            eligibility_raster,
            [region["geometry"]],
            crop=True,
            nodata=INVALID_DATA
        )
    crop, pixel_width, pixel_height = _reproject_raster(
        crop,
        src_crs=raster_crs,
        src_bounds=rasterio.features.bounds(region),
        src_transform=crop_transform
    )
    for eligibility in Eligibility:
        area_size = float((crop == eligibility).sum() * pixel_width * pixel_height / 1000 / 1000)
        region["properties"][eligibility.area_column_name] = area_size
    return region


def _reproject_raster(src, src_crs, src_bounds, src_transform):
    dst_transform, dst_width, dst_height = calculate_default_transform(
        src_crs=src_crs,
        dst_crs=EQUAL_AREA_PROJECTION,
        width=src.shape[1],
        height=src.shape[2],
        left=src_bounds[0],
        bottom=src_bounds[1],
        right=src_bounds[2],
        top=src_bounds[3]
    )
    result = np.zeros((dst_height, dst_width), dtype=src.dtype)
    reproject(
        source=src,
        destination=result,
        src_transform=src_transform,
        src_crs=src_crs,
        dst_transform=dst_transform,
        dst_crs=EQUAL_AREA_PROJECTION,
        resampling=RESAMPLING.nearest
    )
    pixel_width = abs(dst_transform[0])
    pixel_height = abs(dst_transform[4])
    return result, pixel_width, pixel_height


def _remove_offshore(regions):
    # There is sometimes offshore eligibility inside land regions.
    # This should not be possible, hence I am resetting them here to not eligible.
    for region in regions:
        offshore_potential = (region["properties"][Eligibility.OFFSHORE_WIND.area_column_name] +
                              region["properties"][Eligibility.OFFSHORE_WIND_PROTECTED.area_column_name])
        not_eligible = region["properties"][Eligibility.NOT_ELIGIBLE.area_column_name]
        region["properties"][Eligibility.OFFSHORE_WIND.area_column_name] = 0.0
        region["properties"][Eligibility.OFFSHORE_WIND_PROTECTED.area_column_name] = 0.0
        region["properties"][Eligibility.NOT_ELIGIBLE.area_column_name] = not_eligible + offshore_potential
    return regions


def _test_land_allocation(path_to_regions, path_to_eligibilities):
    _test_allocation(path_to_regions, path_to_eligibilities, offshore=False)


def _test_allocation(path_to_regions, path_to_eligibilities, offshore):
    eligibilities = [eligibility for eligibility in Eligibility]
    if offshore is False:
        eligibilities.remove(Eligibility.OFFSHORE_WIND)
        eligibilities.remove(Eligibility.OFFSHORE_WIND_PROTECTED)
    regions = gpd.read_file(path_to_regions)
    regions = regions.merge(
        pd.read_csv(path_to_eligibilities, dtype={"id": np.object}), # id must be object, otherwise merge fails
        on="id"
    )
    total_allocated_area = regions.loc[:, [eligibility.area_column_name
                                           for eligibility in eligibilities]].sum(axis="columns")
    region_size = area_in_squaremeters(regions) / 1000 / 1000
    below_rel_threshold = abs(total_allocated_area - region_size) < region_size * REL_TOLERANCE
    below_abs_threshold = abs(total_allocated_area - region_size) < ABS_TOLERANCE
    below_any_threshold = (below_rel_threshold | below_abs_threshold)
    assert below_any_threshold.all(),\
        dedent("""Allocated area differs more than {}% and more than {} km^2 from real area. Allocated was:
        {}

        Real area is:
        {}

        """.format(REL_TOLERANCE * 100,
                   ABS_TOLERANCE,
                   total_allocated_area[~below_any_threshold],
                   region_size[~below_any_threshold]))


if __name__ == "__main__":
    regional_eligibility()
