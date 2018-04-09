"""Module to determine eligible land per region."""
from textwrap import dedent
from multiprocessing import Pool
from itertools import cycle

import click
import numpy as np
import fiona
import rasterio
import rasterio.mask
from rasterio.warp import calculate_default_transform, reproject, RESAMPLING
import geopandas as gpd

from eligible_land import Eligibility
from conversion import area_in_squaremeters

EQUAL_AREA_PROJECTION = "EPSG:3035" # projection to use to derive area sizes
INVALID_DATA = 255
REL_TOLERANCE = 0.01 # 1%
ABS_TOLERANCE = 3.5 # km^2


@click.command()
@click.argument("path_to_regions")
@click.argument("path_to_eligibility")
@click.argument("path_to_output")
@click.argument("threads", type=click.INT)
def allocate_eligibility_to_regions(path_to_regions, path_to_eligibility, path_to_output, threads):
    """Allocates eligible land to regions defined by vector data."""
    with fiona.open(path_to_regions, "r") as regions:
        meta = regions.meta
        meta["driver"] = "GeoJSON"
        for eligibility in Eligibility:
            meta["schema"]["properties"][eligibility.property_name] = "float"
        with Pool(threads) as pool:
            new_regions = pool.map(
                _allocate_eligibility_to_region,
                zip(regions, cycle([path_to_eligibility]))
            )
        with fiona.open(path_to_output, "w", **meta) as output:
            output.writerecords(new_regions)
    _test_allocation(path_to_output)


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
        region["properties"][eligibility.property_name] = area_size
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


def _test_allocation(path_to_output):
    regions = gpd.read_file(path_to_output)
    regions.set_index("name", inplace=True)
    total_allocated_area = sum(
        [regions[eligibility.property_name] for eligibility in Eligibility]
    )
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
    allocate_eligibility_to_regions()
