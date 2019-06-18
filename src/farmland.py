"""Determine farmland areas for each potential type in each administrative unit.

* Take the (only technically restricted) raster data potentials,
* add restrictions based on scenario definitions,
* additionally restrict to farmland only,
* allocate the onshore areas to the administrative units
* set offshore areas to 0 always.

This is in analogy to `areas.py`.
"""
import click
import numpy as np
import pandas as pd
import rasterio
import fiona

from src.technical_eligibility import Eligibility, FARM
from src.areas import apply_scenario_config_to_areas, apply_scenario_config_to_categories, _area
from src.utils import Config


@click.command()
@click.argument("path_to_units")
@click.argument("path_to_eligible_area")
@click.argument("path_to_eligibility_categories")
@click.argument("path_to_land_cover")
@click.argument("path_to_protected_areas")
@click.argument("path_to_result")
@click.argument("scenario")
@click.argument("config", type=Config())
def areas(path_to_units, path_to_eligible_area, path_to_eligibility_categories,
          path_to_land_cover, path_to_protected_areas, path_to_result, scenario, config):
    """Determine farmland areas for each potential type in each administrative unit.

    * Take the (only technically restricted) raster data potentials,
    * add restrictions based on scenario definitions,
    * additionally restrict to farmland only,
    * allocate the onshore areas to the administrative units
    * set offshore areas to 0 always.
    """
    with rasterio.open(path_to_eligibility_categories, "r") as src:
        category_map = src.read(1)
    with rasterio.open(path_to_eligible_area, "r") as src:
        transform = src.transform
        area_map = src.read(1)
    with rasterio.open(path_to_land_cover, "r") as src:
        land_cover = src.read(1)
    with rasterio.open(path_to_protected_areas, "r") as src:
        protected_areas = src.read(1)
    with fiona.open(path_to_units, "r") as src:
        unit_ids = [feature["properties"]["id"] for feature in src]
        unit_geometries = [feature["geometry"] for feature in src]

    area_map = apply_scenario_config_to_areas(
        area_map=area_map,
        category_map=category_map,
        land_cover=land_cover,
        protected_areas=protected_areas,
        scenario_config=config["scenarios"][scenario]
    )
    area_map = restrict_to_farmland(area_map, land_cover)
    category_map = apply_scenario_config_to_categories(
        category_map=category_map,
        land_cover=land_cover,
        protected_areas=protected_areas,
        scenario_config=config["scenarios"][scenario]
    )
    onshore_areas = pd.DataFrame(
        index=unit_ids,
        data={
            eligibility_category.area_column_name: _area(
                eligibility_category=eligibility_category,
                area_map=area_map,
                category_map=category_map,
                shapes=unit_geometries,
                transform=transform
            )
            for eligibility_category in Eligibility.onshore()
        }
    )
    offshore_areas = pd.DataFrame(
        data=0,
        index=onshore_areas.index,
        columns=[cat.area_column_name for cat in Eligibility.offshore()]
    )
    areas = pd.concat([onshore_areas, offshore_areas], axis=1)
    areas.index.name = "id"
    areas.to_csv(
        path_to_result,
        header=True,
        index=True
    )


def restrict_to_farmland(area_map, land_cover):
    area_map[~np.isin(land_cover, FARM)] = 0
    return area_map


if __name__ == "__main__":
    areas()
