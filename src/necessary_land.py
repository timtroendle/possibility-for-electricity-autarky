"""Determines how much fraction of the land is necessary to feed demand."""
from datetime import timedelta

import click
import pandas as pd

from src.utils import Config
from src.eligible_land import Eligibility
from src.conversion import watt_to_watthours


CP_MAP = {
    Eligibility.ROOFTOP_PV: "pv_capacity_factor",
    Eligibility.ONSHORE_WIND_OR_PV_FARM: "pv_capacity_factor",
    Eligibility.ONSHORE_WIND_FARM: "onshore_capacity_factor",
    Eligibility.OFFSHORE_WIND_FARM: "offshore_capacity_factor"
}
ZERO_DEMAND = 0.000001


@click.command()
@click.argument("paths_to_region_attributes", nargs=-1)
@click.argument("path_to_output")
@click.argument("config", type=Config())
def determine_necessary_land(paths_to_region_attributes, path_to_output, config):
    """Determines the fraction of land needed in each region to fulfill the demand."""
    attributes = pd.concat(
        [pd.read_csv(path_to_attribute).set_index("id") for path_to_attribute in paths_to_region_attributes],
        axis=1
    )
    determine_fraction_land_necessary(
        demand_twh_per_year=attributes["demand_twh_per_year"],
        eligibilities=attributes[[eligibility.property_name for eligibility in Eligibility]],
        capacity_factors=attributes[[column for column in attributes.columns if "capacity_factor" in column]],
        config=config
    ).to_csv(path_to_output, header=True)


def determine_fraction_land_necessary(demand_twh_per_year, eligibilities, capacity_factors, config):
    max_yield_watt = pd.DataFrame({
        eligibility: _max_yield_watt(eligibility, eligibilities, capacity_factors, config)
        for eligibility in Eligibility
    })
    max_yield_twh_per_year = watt_to_watthours(
        max_yield_watt.sum(axis=1),
        timedelta(days=365)
    ).div(1e12)
    fraction_land_necessary = demand_twh_per_year / max_yield_twh_per_year
    fraction_land_necessary[demand_twh_per_year <= ZERO_DEMAND] = 0.0 # might be nan otherwise if yield is 0
    fraction_land_necessary.name = "fraction_land_necessary"
    fraction_land_necessary.index.name = "id"
    return fraction_land_necessary


def _max_yield_watt(eligibility, eligibilities, cps, config):
    """Returns a pandas Series of maximum yields in all regions of given eligibility type in Watt."""
    available_area_km2 = eligibilities[eligibility.property_name]
    if eligibility == Eligibility.NOT_ELIGIBLE:
        capacity_factors = pd.Series(0, index=cps.index)
    else:
        capacity_factors = cps.loc[:, CP_MAP[eligibility]]
    return available_area_km2 * _power_density_watt_per_m2(config, eligibility) * 1e6 * capacity_factors


def _power_density_watt_per_m2(config, eligibility):
    power_densities = config["parameters"]["maximum-installable-power-density"]
    if eligibility == Eligibility.ROOFTOP_PV:
        return power_densities["rooftop-pv"]
    elif eligibility == Eligibility.ONSHORE_WIND_OR_PV_FARM:
        return power_densities["pv-farm"]
    elif eligibility == Eligibility.ONSHORE_WIND_FARM:
        return power_densities["onshore-wind"]
    elif eligibility == Eligibility.OFFSHORE_WIND_FARM:
        return power_densities["offshore-wind"]
    elif eligibility == Eligibility.NOT_ELIGIBLE:
        return 0
    else:
        raise ValueError("Unknown eligibility: {}".format(eligibility))


if __name__ == "__main__":
    determine_necessary_land()
