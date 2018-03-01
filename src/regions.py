"""Module to determine availability per region."""
from textwrap import dedent

import click
import numpy as np
import fiona
import rasterio
import rasterio.mask
from rasterio.warp import calculate_default_transform, reproject, RESAMPLING
import geopandas as gpd

from available_land import Availability
from conversion import area_in_squaremeters

EQUAL_AREA_PROJECTION = "EPSG:3035" # projection to use to derive area sizes
INVALID_DATA = 255
PRECISION = 0.01 # 1%


@click.command()
@click.argument("path_to_regions")
@click.argument("path_to_availability")
@click.argument("path_to_output")
def allocate_availability_to_regions(path_to_regions, path_to_availability, path_to_output):
    """Allocates available land to regions defined by vector data."""
    with fiona.open(path_to_regions, "r") as regions:
        meta = regions.meta
        meta["driver"] = "GeoJSON"
        for availability in Availability:
            meta["schema"]["properties"][availability.property_name] = "float"
        with fiona.open(path_to_output, "w", **meta) as output,\
                rasterio.open(path_to_availability) as availability_raster:
            for region in regions:
                region = _allocate_availability_to_region(region, availability_raster)
                output.write(region)
    _test_allocation(path_to_output)


def _allocate_availability_to_region(region, availability_raster):
    region = region.copy()
    crop, crop_transform = rasterio.mask.mask(
        availability_raster,
        [region["geometry"]],
        crop=True,
        nodata=INVALID_DATA
    )
    crop, pixel_width, pixel_height = _reproject_raster(
        crop,
        src_crs=availability_raster.crs,
        src_bounds=rasterio.features.bounds(region),
        src_transform=crop_transform
    )
    for availability in Availability:
        area_size = float((crop == availability).sum() * pixel_width * pixel_height / 1000 / 1000)
        region["properties"][availability.property_name] = area_size
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
        [regions[availability.property_name] for availability in Availability]
    )
    region_size = area_in_squaremeters(regions) / 1000 / 1000
    below_threshold = abs(total_allocated_area - region_size) < region_size * PRECISION
    assert below_threshold.all(),\
        dedent("""Allocated area differs more than {}% from real area. Allocated was:
        {}

        Real area is:
        {}

        """.format(PRECISION * 100, total_allocated_area[~below_threshold],
                   region_size[~below_threshold]))


if __name__ == "__main__":
    allocate_availability_to_regions()
