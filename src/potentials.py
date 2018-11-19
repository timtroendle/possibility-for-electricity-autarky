"""Determine potential of renewable electricity in each administrative unit.

* Take the (only technically restricted) raster data potentials,
* add restrictions based on scenario definitions,
* allocate the onshore potentials to the administrative units,
* allocate the offshore potentials to exclusive economic zones (EEZ),
* allocate the offshore potential of EEZ to units based on the fraction of shared coast.
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
    """Classes of renewable electricity potentials."""
    ROOFTOP_PV = (1, [Eligibility.ROOFTOP_PV])
    OPEN_FIELD_PV = (2, [Eligibility.ONSHORE_WIND_AND_PV])
    ONSHORE_WIND = (3, [Eligibility.ONSHORE_WIND_AND_PV, Eligibility.ONSHORE_WIND])
    OFFSHORE_WIND = (4, [Eligibility.OFFSHORE_WIND])

    def __init__(self, int_id, corresponding_eligibilities):
        self.int_id = int_id
        self.eligible_on = corresponding_eligibilities

    @property
    def area_name(self):
        return "{}_km2".format(self.name.lower())

    @property
    def electricity_yield_name(self):
        return "{}_twh_per_year".format(self.name.lower())

    @staticmethod
    def onshore():
        """Returns all onshore potentials."""
        return [
            Potential.ROOFTOP_PV,
            Potential.OPEN_FIELD_PV,
            Potential.ONSHORE_WIND,
        ]

    @staticmethod
    def offshore():
        """Returns all offshore potentials."""
        return [
            Potential.OFFSHORE_WIND
        ]

    def __repr__(self):
        return self.electricity_yield_name

    def __str__(self):
        return self.__repr__()


@click.command()
@click.argument("path_to_units")
@click.argument("path_to_eez")
@click.argument("path_to_shared_coast")
@click.argument("path_to_electricity_yield_pv_prio")
@click.argument("path_to_electricity_yield_wind_prio")
@click.argument("path_to_eligibility_categories")
@click.argument("path_to_land_cover")
@click.argument("path_to_protected_areas")
@click.argument("path_to_result")
@click.argument("scenario")
@click.argument("config", type=Config())
def potentials(path_to_units, path_to_eez, path_to_shared_coast,
               path_to_electricity_yield_pv_prio, path_to_electricity_yield_wind_prio,
               path_to_eligibility_categories, path_to_land_cover, path_to_protected_areas,
               path_to_result, scenario, config):
    """Determine potential of renewable electricity in each administrative unit.

    * Take the (only technically restricted) raster data potentials,
    * add restrictions based on scenario definitions,
    * allocate the onshore potentials to the administrative units,
    * allocate the offshore potentials to exclusive economic zones (EEZ),
    * allocate the offshore potential of EEZ to units based on the fraction of shared coast.
    """
    with rasterio.open(path_to_eligibility_categories, "r") as src:
        eligibility_categories = src.read(1)
    with rasterio.open(path_to_electricity_yield_pv_prio, "r") as src:
        transform = src.transform
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
    with fiona.open(path_to_eez, "r") as src:
        eez_ids = [feature["properties"]["id"] for feature in src]
        eez_geometries = [feature["geometry"] for feature in src]
    shared_coasts = pd.read_csv(path_to_shared_coast, index_col=0)

    electricity_yield_pv_prio, electricity_yield_wind_prio = apply_scenario_config(
        electricity_yield_pv_prio=electricity_yield_pv_prio,
        electricity_yield_wind_prio=electricity_yield_wind_prio,
        categories=eligibility_categories,
        land_cover=land_cover,
        protected_areas=protected_areas,
        scenario_config=config["scenarios"][scenario]
    )
    electricity_yield_pv_prio, electricity_yield_wind_prio = _decide_between_pv_and_wind(
        electricity_yield_pv_prio=electricity_yield_pv_prio,
        electricity_yield_wind_prio=electricity_yield_wind_prio,
        eligibility_categories=eligibility_categories
    )

    onshore_potentials = pd.DataFrame(
        index=unit_ids,
        data={
            potential: _potentials(
                eligibilities=potential.eligible_on,
                electricity_yield=(electricity_yield_pv_prio if "pv" in str(potential).lower()
                                   else electricity_yield_wind_prio),
                eligibility_categories=eligibility_categories,
                shapes=unit_geometries,
                transform=transform
            )
            for potential in Potential.onshore()
        }
    )
    offshore_eez_potentials = pd.DataFrame(
        index=eez_ids,
        data={
            potential: _potentials(
                eligibilities=potential.eligible_on,
                electricity_yield=(electricity_yield_pv_prio if "pv" in str(potential).lower()
                                   else electricity_yield_wind_prio),
                eligibility_categories=eligibility_categories,
                shapes=eez_geometries,
                transform=transform
            )
            for potential in Potential.offshore()
        }
    )
    offshore_potentials = pd.DataFrame(
        data=shared_coasts.dot(offshore_eez_potentials),
        columns=Potential.offshore()
    )
    potentials = pd.concat([onshore_potentials, offshore_potentials], axis=1)
    potentials.index.name = "id"
    potentials.to_csv(
        path_to_result,
        header=True,
        index=True
    )


def apply_scenario_config(electricity_yield_pv_prio, electricity_yield_wind_prio, categories,
                          land_cover, protected_areas, scenario_config):
    """Limit electricity yield of each pixel based on scenario config."""

    # share-rooftops-used
    share_rooftops_used = scenario_config["share-rooftops-used"]
    mask = categories == Eligibility.ROOFTOP_PV
    electricity_yield_pv_prio[mask] = electricity_yield_pv_prio[mask] * share_rooftops_used
    electricity_yield_wind_prio[mask] = electricity_yield_wind_prio[mask] * share_rooftops_used

    # share-forest-used-for-wind
    share_forest_used_for_wind = scenario_config["share-forest-used-for-wind"]
    mask = np.isin(land_cover, FOREST) & (categories != Eligibility.ROOFTOP_PV)
    electricity_yield_pv_prio[mask] = electricity_yield_pv_prio[mask] * share_forest_used_for_wind
    electricity_yield_wind_prio[mask] = electricity_yield_wind_prio[mask] * share_forest_used_for_wind

    # share-other-land-used
    share_other_land_used = scenario_config["share-other-land-used"]
    mask = np.isin(land_cover, OTHER) & (categories != Eligibility.ROOFTOP_PV)
    electricity_yield_pv_prio[mask] = electricity_yield_pv_prio[mask] * share_other_land_used
    electricity_yield_wind_prio[mask] = electricity_yield_wind_prio[mask] * share_other_land_used

    # share-farmland-used
    share_farmland_used = scenario_config["share-farmland-used"]
    mask = np.isin(land_cover, FARM) & (categories != Eligibility.ROOFTOP_PV)
    electricity_yield_pv_prio[mask] = electricity_yield_pv_prio[mask] * share_farmland_used
    electricity_yield_wind_prio[mask] = electricity_yield_wind_prio[mask] * share_farmland_used

    # share-offshore-used
    share_offshore_used = scenario_config["share-offshore-used"]
    mask = categories == Eligibility.OFFSHORE_WIND
    electricity_yield_pv_prio[mask] = electricity_yield_pv_prio[mask] * share_offshore_used
    electricity_yield_wind_prio[mask] = electricity_yield_wind_prio[mask] * share_offshore_used

    # pv-on-farmland
    pv_on_farmland = scenario_config["pv-on-farmland"]
    if not pv_on_farmland:
        mask = np.isin(land_cover, FARM) & (categories == Eligibility.ONSHORE_WIND_AND_PV)
        electricity_yield_pv_prio[mask] = 0

    # share-protected-areas-used
    use_protected_areas = scenario_config["use-protected-areas"]
    if not use_protected_areas:
        mask = (protected_areas == ProtectedArea.PROTECTED) & (categories != Eligibility.ROOFTOP_PV)
        electricity_yield_pv_prio[mask] = 0
        electricity_yield_wind_prio[mask] = 0

    return electricity_yield_pv_prio, electricity_yield_wind_prio


def _decide_between_pv_and_wind(electricity_yield_pv_prio, electricity_yield_wind_prio, eligibility_categories):
    """When both are possible, choose PV when its electricity yield is higher, or vice versa."""
    open_field_yield = electricity_yield_pv_prio.copy()
    onshore_yield = electricity_yield_wind_prio.copy()
    pv_and_wind_possible = eligibility_categories == Eligibility.ONSHORE_WIND_AND_PV
    higher_wind_yield = electricity_yield_pv_prio < electricity_yield_wind_prio

    open_field_yield[pv_and_wind_possible & higher_wind_yield] = 0
    onshore_yield[pv_and_wind_possible & ~higher_wind_yield] = 0

    return open_field_yield, onshore_yield


def _potentials(eligibilities, electricity_yield, eligibility_categories, shapes, transform):
    """Determine electricity yield of one eligibility category per shape."""
    electricity_yield = electricity_yield.copy()
    electricity_yield[~np.isin(eligibility_categories, eligibilities)] = 0
    potentials = zonal_stats(
        shapes,
        electricity_yield,
        affine=transform,
        stats="sum",
        nodata=-999
    )
    return [stat["sum"] for stat in potentials]


if __name__ == "__main__":
    potentials()
