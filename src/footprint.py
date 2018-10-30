"""Determine the land footprint of the renewable potential in a given scenario."""
import click
import fiona
import numpy as np
import pandas as pd
import rasterio
from rasterstats import zonal_stats

from src.utils import Config
from src.technical_eligibility import Eligibility, FOREST, FARM, OTHER
from src.potentials import ProtectedArea, apply_scenario_config, Potential


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
        affine = src.affine
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
    constrained_areas_pv, constrained_areas_wind = _decide_between_pv_and_wind(
        areas=constrained_areas,
        electricity_yield_pv_prio=electricity_yield_pv_prio,
        electricity_yield_wind_prio=electricity_yield_wind_prio,
        categories=eligibility_categories,
        land_cover=land_cover,
        protected_areas=protected_areas,
        scenario_config=config["scenarios"][scenario]
    )

    footprint = pd.DataFrame(
        index=unit_ids,
        data={
            potential.area_name: _areas(
                eligibilities=potential.eligible_on,
                eligible_areas=(constrained_areas_pv if "pv" in str(potential).lower()
                                else constrained_areas_wind),
                eligibility_categories=eligibility_categories,
                unit_geometries=unit_geometries,
                affine=affine
            )
            for potential in Potential
        }
    )
    footprint.index.name = "id"
    footprint.to_csv(
        path_to_result,
        header=True,
        index=True
    )


def _areas(eligibilities, eligible_areas, eligibility_categories, unit_geometries, affine):
    eligible_areas = eligible_areas.copy()
    eligible_areas[~np.isin(eligibility_categories, eligibilities)] = 0
    potentials = zonal_stats(
        unit_geometries,
        eligible_areas,
        affine=affine,
        stats="sum",
        nodata=-999
    )
    return [stat["sum"] for stat in potentials]


def _apply_scenario_config_to_area(eligible_areas, categories, land_cover, protected_areas, scenario_config):
    """Limit eligibility of each pixel based on scenario config."""

    # share-rooftops-used
    share_rooftops_used = scenario_config["share-rooftops-used"]
    mask = categories == Eligibility.ROOFTOP_PV
    eligible_areas[mask] = eligible_areas[mask] * share_rooftops_used

    # share-forest-used-for-wind
    share_forest_used_for_wind = scenario_config["share-forest-used-for-wind"]
    mask = np.isin(land_cover, FOREST)
    eligible_areas[mask] = eligible_areas[mask] * share_forest_used_for_wind

    # share-other-land-used
    share_other_land_used = scenario_config["share-other-land-used"]
    mask = np.isin(land_cover, OTHER)
    eligible_areas[mask] = eligible_areas[mask] * share_other_land_used

    # share-farmland-used
    share_farmland_used = scenario_config["share-farmland-used"]
    mask = np.isin(land_cover, FARM)
    eligible_areas[mask] = eligible_areas[mask] * share_farmland_used

    # share-offshore-used
    # FIXME add somehow

    # share-protected-areas-used
    use_protected_areas = scenario_config["use-protected-areas"]
    if not use_protected_areas:
        mask = protected_areas == ProtectedArea.PROTECTED
        eligible_areas[mask] = 0

    return eligible_areas


def _decide_between_pv_and_wind(areas, electricity_yield_pv_prio, electricity_yield_wind_prio, categories,
                                land_cover, protected_areas, scenario_config):
    """Based on higher yield, choose open field pv or wind where both are possible."""
    electricity_yield_pv_prio, electricity_yield_wind_prio = apply_scenario_config(
        electricity_yield_pv_prio=electricity_yield_pv_prio,
        electricity_yield_wind_prio=electricity_yield_wind_prio,
        categories=categories,
        land_cover=land_cover,
        protected_areas=protected_areas,
        scenario_config=scenario_config
    )
    pv_and_wind_possible = categories == Eligibility.ONSHORE_WIND_AND_PV
    higher_wind_yield = electricity_yield_pv_prio < electricity_yield_wind_prio

    areas_pv = areas.copy()
    areas_wind = areas.copy()
    areas_pv[pv_and_wind_possible & higher_wind_yield] = 0
    areas_wind[pv_and_wind_possible & ~higher_wind_yield] = 0

    return areas_pv, areas_wind


if __name__ == "__main__":
    footprint()
