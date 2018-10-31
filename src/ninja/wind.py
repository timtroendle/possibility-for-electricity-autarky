import click
import pandas as pd
import geopandas as gpd

from src.utils import Config
from src.ninja import point_raster_on_shapes

ONSHORE_TURBINE = "enercon e126 7000"
OFFSHORE_TURBINE = "vestas v164 7000"
ONSHORE_HUB_HEIGHT = 80
OFFSHORE_HUB_HEIGHT = 120


@click.command()
@click.argument("path_to_shapes_of_land_surface")
@click.argument("path_to_shapes_of_water_surface")
@click.argument("path_to_output")
@click.argument("resolution", type=int)
@click.argument("config", type=Config())
def wind(path_to_shapes_of_land_surface, path_to_shapes_of_water_surface, path_to_output, resolution, config):
    onshore_parameters = parameters(
        bounds=config["scope"]["bounds"],
        resolution=resolution,
        path_to_shapes=path_to_shapes_of_land_surface,
        hub_height=ONSHORE_HUB_HEIGHT,
        turbine=ONSHORE_TURBINE
    )
    offshore_parameters = parameters(
        bounds=config["scope"]["bounds"],
        resolution=resolution,
        path_to_shapes=path_to_shapes_of_water_surface,
        hub_height=OFFSHORE_HUB_HEIGHT,
        turbine=OFFSHORE_TURBINE
    )
    points = pd.concat([onshore_parameters, offshore_parameters]).reset_index(drop=True)
    points.index.name = "site_id"
    points.to_csv(
        path_to_output,
        header=True,
        index=True
    )


def parameters(bounds, resolution, path_to_shapes, hub_height, turbine):
    points = point_raster_on_shapes(
        bounds_wgs84=bounds,
        shapes=gpd.read_file(path_to_shapes),
        resolution_km2=resolution
    )
    return pd.DataFrame(
        data={
            "lat": [point.y for point in points.geometry],
            "long": [point.x for point in points.geometry],
            "hub_height": hub_height,
            "turbine": turbine
        }
    )


if __name__ == "__main__":
    wind()
