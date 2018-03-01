"""This module estimates the shape of protected areas, for which only centroids are known.

This procedure is applied by the provider of the database, UNEP-WCMC, as well. See:
https://www.protectedplanet.net/c/calculating-protected-area-coverage
or the manual of the database for further information.
"""
import math

import click
import geopandas as gpd
import pycountry

from src.utils import Config

# from https://epsg.io/3035
EPSG_3035_PROJ4 = "+proj=laea +lat_0=52 +lon_0=10 +x_0=4321000 +y_0=3210000 +ellps=GRS80 +units=m +no_defs "


@click.command()
@click.argument("path_to_input")
@click.argument("path_to_output")
@click.argument("config", type=Config())
def estimate_shapes(path_to_input, path_to_output, config):
    """Estimates the shap of protected areas for which only centroids are known."""
    points = gpd.read_file(path_to_input)
    points_in_scope = filter_points(points, config)
    original_crs = points_in_scope.crs
    # convert points to circles
    points_in_scope = points_in_scope.to_crs(EPSG_3035_PROJ4)
    points_in_scope.geometry = [rec[1].geometry.buffer(radius_meter(rec[1]["REP_AREA"]))
                                for rec in points_in_scope.iterrows()]
    test_area_size(points_in_scope)
    points_in_scope.to_crs(original_crs).to_file(path_to_output, driver="GeoJSON")


def filter_points(points, config):
    x_min, x_max, y_min, y_max = [config["scope"]["bounds"][z]
                                  for z in ["x_min", "x_max", "y_min", "y_max"]]
    countries = [pycountry.countries.lookup(country).alpha_3
                 for country in config["scope"]["countries"]]
    return points.cx[x_min:x_max, y_min:y_max].loc[
        (points.ISO3.isin(countries)) &
        (points.REP_AREA > 0)
    ].copy()


def radius_meter(area_squarekilometer):
    area_squaremeter = area_squarekilometer * 1e6
    return math.sqrt(area_squaremeter / math.pi)


def test_area_size(points):
    area_size_calculated = points.area.sum() / 1e6
    area_size_reported = points.REP_AREA.sum()
    assert abs(area_size_calculated - area_size_reported) < (area_size_reported / 100)


if __name__ == "__main__":
    estimate_shapes()
