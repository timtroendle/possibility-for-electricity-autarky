"""Determine the land footprint of the renewable potential in a given scenario."""
import click
import fiona
import numpy as np
import pandas as pd
import rasterio

from src.utils import Config
from src.technical_eligibility import Eligibility, FOREST, FARM, OTHER
from src.potentials import ProtectedArea, apply_scenario_config, Potential, \
    decide_between_pv_and_wind, potentials_per_shape


@click.command()
@click.argument("path_to_eligibility_categories")
@click.argument("path_to_eligible_areas")
@click.argument("path_to_electricity_yield_pv_prio")
@click.argument("path_to_electricity_yield_wind_prio")
@click.argument("path_to_land_cover")
@click.argument("path_to_protected_areas")
@click.argument("path_to_units")
@click.argument("path_to_result")
@click.argument("scenario")
@click.argument("config", type=Config())
def footprint(path_to_eligibility_categories, path_to_eligible_areas, path_to_electricity_yield_pv_prio,
              path_to_electricity_yield_wind_prio, path_to_land_cover, path_to_protected_areas,
              path_to_units, path_to_result, scenario, config):
    """Determine the land footprint of the renewable potential in a given scenario."""
    with rasterio.open(path_to_eligibility_categories, "r") as src:
        eligibility_categories = src.read(1)
    with rasterio.open(path_to_eligible_areas, "r") as src:
        transform = src.transform
        eligible_areas = src.read(1)
    with rasterio.open(path_to_electricity_yield_pv_prio, "r") as src:
        electricity_yield_pv_prio = src.read(1)
    with rasterio.open(path_to_electricity_yield_wind_prio, "r") as src:
        electricity_yield_wind_prio = src.read(1)
    with rasterio.open(path_to_land_cover, "r") as src:
        land_cover = src.read(1)
    with rasterio.open(path_to_protected_areas, "r") as src:
        protected_areas = src.read(1)
    with fiona.open(path_to_units, "r") as src:
        unit_ids = [feature["properties"]["id"] for feature in src]
        unit_geometries = [feature["geometry"] for feature in src]

    constrained_areas = _apply_scenario_config_to_area(
        eligible_areas=eligible_areas,
        categories=eligibility_categories,
        land_cover=land_cover,
        protected_areas=protected_areas,
        scenario_config=config["scenarios"][scenario]
    )
    electricity_yield_pv_prio, electricity_yield_wind_prio = apply_scenario_config(
        potential_pv_prio=electricity_yield_pv_prio,
        potential_wind_prio=electricity_yield_wind_prio,
        categories=eligibility_categories,
        land_cover=land_cover,
        protected_areas=protected_areas,
        scenario_config=config["scenarios"][scenario]
    )
    constrained_areas_pv, constrained_areas_wind = decide_between_pv_and_wind(
        potential_pv_prio=constrained_areas.copy(),
        potential_wind_prio=constrained_areas.copy(),
        electricity_yield_pv_prio=electricity_yield_pv_prio,
        electricity_yield_wind_prio=electricity_yield_wind_prio,
        eligibility_categories=eligibility_categories
    )

    footprint = pd.DataFrame(
        index=unit_ids,
        data={
            potential.area_name: potentials_per_shape(
                eligibilities=potential.eligible_on,
                potential_map=(constrained_areas_pv if "pv" in str(potential).lower()
                               else constrained_areas_wind),
                eligibility_categories=eligibility_categories,
                shapes=unit_geometries,
                transform=transform
            )
            for potential in Potential.onshore()
        }
    )
    footprint.index.name = "id"
    footprint.to_csv(
        path_to_result,
        header=True,
        index=True
    )


def _apply_scenario_config_to_area(eligible_areas, categories, land_cover, protected_areas, scenario_config):
    """Limit eligibility of each pixel based on scenario config."""

    # share-rooftops-used
    share_rooftops_used = scenario_config["share-rooftops-used"]
    mask = categories == Eligibility.ROOFTOP_PV
    eligible_areas[mask] = eligible_areas[mask] * share_rooftops_used

    # share-forest-used-for-wind
    share_forest_used_for_wind = scenario_config["share-forest-used-for-wind"]
    mask = np.isin(land_cover, FOREST) & (categories != Eligibility.ROOFTOP_PV)
    eligible_areas[mask] = eligible_areas[mask] * share_forest_used_for_wind

    # share-other-land-used
    share_other_land_used = scenario_config["share-other-land-used"]
    mask = np.isin(land_cover, OTHER) & (categories != Eligibility.ROOFTOP_PV)
    eligible_areas[mask] = eligible_areas[mask] * share_other_land_used

    # share-farmland-used
    share_farmland_used = scenario_config["share-farmland-used"]
    mask = np.isin(land_cover, FARM) & (categories != Eligibility.ROOFTOP_PV)
    eligible_areas[mask] = eligible_areas[mask] * share_farmland_used

    # share-offshore-used
    share_offshore_used = scenario_config["share-offshore-used"]
    if share_offshore_used > 0:
        msg = f"Offshore potentials cannot be considered when determining land use. share-offshore-used must be 0, "\
              "but is {share-offshore-used}."
        raise ValueError(msg)

    # share-protected-areas-used
    use_protected_areas = scenario_config["use-protected-areas"]
    if not use_protected_areas:
        mask = (protected_areas == ProtectedArea.PROTECTED) & (categories != Eligibility.ROOFTOP_PV)
        eligible_areas[mask] = 0

    return eligible_areas


if __name__ == "__main__":
    footprint()
