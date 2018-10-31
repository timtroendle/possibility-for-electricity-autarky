import click
import pandas as pd
import geopandas as gpd

from src.utils import Config
from src.ninja import point_raster_on_shapes

EFFICIENCY = 0.16
PERFORMANCE_RATIO = 0.9


@click.command()
@click.argument("path_to_shapes_of_land_surface")
@click.argument("path_to_roof_categories")
@click.argument("path_to_output")
@click.argument("resolution", type=int)
@click.argument("config", type=Config())
def pv_simulation_parameters(path_to_shapes_of_land_surface, path_to_roof_categories, path_to_output,
                             resolution, config):
    points = point_raster_on_shapes(
        bounds_wgs84=config["scope"]["bounds"],
        shapes=gpd.read_file(path_to_shapes_of_land_surface),
        resolution_km2=resolution
    )

    roof_categories = pd.read_csv(path_to_roof_categories)
    lat_long = pd.DataFrame(
        data={
            "lat": [point.y for point in points.geometry],
            "long": [point.x for point in points.geometry]
        }
    )

    index = pd.MultiIndex.from_product((points.index, roof_categories.index), names=["id", "roof_cat_id"])
    data = pd.DataFrame(index=index).reset_index()
    data = data.merge(roof_categories, left_on="roof_cat_id", right_index=True).drop(columns=["share of roof areas"])
    data = data.merge(lat_long, left_on="id", right_index=True)
    data["azim"] = data["orientation"].map(orientation_to_azimuth)
    data["site_id"] = data.apply(
        lambda row: "{}_{}_{}".format(row.id, row.orientation, round(row.tilt)),
        axis=1
    )
    flat_mask = data["orientation"] == "flat"
    data.loc[flat_mask, "tilt"] = data.loc[flat_mask, "lat"].map(optimal_tilt)
    data["efficiency"] = EFFICIENCY
    data["pr"] = PERFORMANCE_RATIO
    data[["site_id", "lat", "long", "tilt", "azim", "efficiency", "pr"]].sort_index().to_csv(
        path_to_output,
        header=True,
        index=False
    )


def orientation_to_azimuth(orientation):
    if orientation == "S":
        return 180
    elif orientation == "W":
        return -90
    elif orientation == "N":
        return 0
    elif orientation == "E":
        return 90
    elif orientation == "flat":
        return 180
    else:
        raise ValueError()


def optimal_tilt(latitude):
    # based on @Jacobson:2018
    optimal_tilt = 1.3793 + latitude * (1.2011 + latitude * (-0.014404 + latitude * 0.000080509))
    assert 90 > optimal_tilt >= 0
    return optimal_tilt


if __name__ == "__main__":
    pv_simulation_parameters()
