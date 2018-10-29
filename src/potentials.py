"""Determine potential of renewable electricity in each administrative unit.

* Take the (only technically restricted) raster data potentials,
* add restrictions based on scenario definitions,
* allocate the potential to the administrative units.
"""

from enum import IntEnum, Enum

import click
import numpy as np
import pandas as pd
import rasterio
from rasterstats import zonal_stats
import fiona

from src.technical_eligibility import Eligibility, FOREST, FARM, OTHER
from src.utils import Config


class ProtectedArea(IntEnum):
    """Derived from UNEP-WCMC data set."""
    PROTECTED = 255
    NOT_PROTECTED = 0


class Potential(Enum):
    """Defining classes of renewable electricity potentials."""
    ROOFTOP_PV = (1, [Eligibility.ROOFTOP_PV])
    OPEN_FIELD_PV = (2, [Eligibility.ONSHORE_WIND_AND_PV])
    ONSHORE_WIND = (3, [Eligibility.ONSHORE_WIND_AND_PV, Eligibility.ONSHORE_WIND])

    def __init__(self, int_id, corresponding_eligibilities):
        self.int_id = int_id
        self.eligible_on = corresponding_eligibilities

    def __repr__(self):
        return "{}_twh_per_year".format(self.name.lower())

    def __str__(self):
        return self.__repr__()


@click.command()
@click.argument("path_to_units")
@click.argument("path_to_energy_yield_pv_prio")
@click.argument("path_to_energy_yield_wind_prio")
@click.argument("path_to_eligibility_categories")
@click.argument("path_to_land_cover")
@click.argument("path_to_protected_areas")
@click.argument("path_to_result")
@click.argument("scenario")
@click.argument("config", type=Config())
def potentials(path_to_units, path_to_energy_yield_pv_prio, path_to_energy_yield_wind_prio,
               path_to_eligibility_categories, path_to_land_cover, path_to_protected_areas,
               path_to_result, scenario, config):
    """Determine potential of renewable electricity in each administrative unit.

    * Take the (only technically restricted) raster data potentials,
    * add restrictions based on scenario definitions,
    * allocate the potential to the administrative units.
    """
    with rasterio.open(path_to_eligibility_categories, "r") as src:
        eligibility_categories = src.read(1)
    with rasterio.open(path_to_energy_yield_pv_prio, "r") as src:
        affine = src.affine
        energy_yield_pv_prio = src.read(1)
    with rasterio.open(path_to_energy_yield_wind_prio, "r") as src:
        energy_yield_wind_prio = src.read(1)
    with rasterio.open(path_to_land_cover, "r") as src:
        land_cover = src.read(1)
    with rasterio.open(path_to_protected_areas, "r") as src:
        protected_areas = src.read(1)
    with fiona.open(path_to_units, "r") as src:
        unit_ids = [feature["properties"]["id"] for feature in src]
        unit_geometries = [feature["geometry"] for feature in src]

    energy_yield_pv_prio, energy_yield_wind_prio = _apply_scenario_config(
        energy_yield_pv_prio=energy_yield_pv_prio,
        energy_yield_wind_prio=energy_yield_wind_prio,
        categories=eligibility_categories,
        land_cover=land_cover,
        protected_areas=protected_areas,
        scenario_config=config["scenarios"][scenario]
    )
    energy_yield_pv_prio, energy_yield_wind_prio = _decide_between_pv_and_wind(
        energy_yield_pv_prio=energy_yield_pv_prio,
        energy_yield_wind_prio=energy_yield_wind_prio,
        eligibility_categories=eligibility_categories
    )

    potentials = pd.DataFrame(
        index=unit_ids,
        data={
            potential: _potentials(
                eligibilities=potential.eligible_on,
                energy_yield=energy_yield_pv_prio if "pv" in str(potential).lower() else energy_yield_wind_prio,
                eligibility_categories=eligibility_categories,
                unit_geometries=unit_geometries,
                affine=affine
            )
            for potential in Potential
        }
    )
    potentials.index.name = "id"
    potentials.to_csv(
        path_to_result,
        header=True,
        index=True
    )


def _apply_scenario_config(energy_yield_pv_prio, energy_yield_wind_prio, categories,
                           land_cover, protected_areas, scenario_config):
    """Limit energy yield of each pixel based on scenario config."""

    # share-rooftops-used
    share_rooftops_used = scenario_config["share-rooftops-used"]
    mask = categories == Eligibility.ROOFTOP_PV
    energy_yield_pv_prio[mask] = energy_yield_pv_prio[mask] * share_rooftops_used
    energy_yield_wind_prio[mask] = energy_yield_wind_prio[mask] * share_rooftops_used

    # share-forest-used-for-wind
    share_forest_used_for_wind = scenario_config["share-forest-used-for-wind"]
    mask = np.isin(land_cover, FOREST)
    energy_yield_pv_prio[mask] = energy_yield_pv_prio[mask] * share_forest_used_for_wind
    energy_yield_wind_prio[mask] = energy_yield_wind_prio[mask] * share_forest_used_for_wind

    # share-other-land-used
    share_other_land_used = scenario_config["share-other-land-used"]
    mask = np.isin(land_cover, OTHER)
    energy_yield_pv_prio[mask] = energy_yield_pv_prio[mask] * share_other_land_used
    energy_yield_wind_prio[mask] = energy_yield_wind_prio[mask] * share_other_land_used

    # share-farmland-used
    share_farmland_used = scenario_config["share-farmland-used"]
    mask = np.isin(land_cover, FARM)
    energy_yield_pv_prio[mask] = energy_yield_pv_prio[mask] * share_farmland_used
    energy_yield_wind_prio[mask] = energy_yield_wind_prio[mask] * share_farmland_used

    # share-offshore-used
    # FIXME add somehow

    # pv-on-farmland
    pv_on_farmland = scenario_config["pv-on-farmland"]
    if not pv_on_farmland:
        mask = np.isin(land_cover, FARM) & categories == Eligibility.ONSHORE_WIND_AND_PV
        energy_yield_pv_prio[mask] = 0

    # share-protected-areas-used
    use_protected_areas = scenario_config["use-protected-areas"]
    if not use_protected_areas:
        mask = protected_areas == ProtectedArea.PROTECTED
        energy_yield_pv_prio[mask] = 0
        energy_yield_wind_prio[mask] = 0

    return energy_yield_pv_prio, energy_yield_wind_prio


def _decide_between_pv_and_wind(energy_yield_pv_prio, energy_yield_wind_prio, eligibility_categories):
    """When both are possible, choose PV when its energy yield is higher, or vice versa."""
    open_field_yield = energy_yield_pv_prio.copy()
    onshore_yield = energy_yield_wind_prio.copy()
    pv_and_wind_possible = eligibility_categories == Eligibility.ONSHORE_WIND_AND_PV
    higher_wind_yield = energy_yield_pv_prio < energy_yield_wind_prio

    open_field_yield[pv_and_wind_possible & higher_wind_yield] = 0
    onshore_yield[pv_and_wind_possible & ~higher_wind_yield] = 0

    return open_field_yield, onshore_yield


def _potentials(eligibilities, energy_yield, eligibility_categories, unit_geometries, affine):
    """Determine energy yield of one eligibility category per administrative unit."""
    energy_yield = energy_yield.copy()
    energy_yield[~np.isin(eligibility_categories, eligibilities)] = 0
    potentials = zonal_stats(
        unit_geometries,
        energy_yield,
        affine=affine,
        stats="sum",
        nodata=-999
    )
    return [stat["sum"] for stat in potentials]


if __name__ == "__main__":
    potentials()
