"""Determines how much fraction of the land is necessary to feed demand."""
from datetime import timedelta

import click
import pandas as pd
import geopandas as gpd

from src.utils import Config
from src.eligible_land import Eligibility
from src.conversion import watt_to_watthours

ZERO_DEMAND = 0.000001


@click.command()
@click.argument("path_to_regions")
@click.argument("paths_to_region_attributes", nargs=-1)
@click.argument("path_to_capacity_factors")
@click.argument("path_to_output")
@click.argument("config", type=Config())
def determine_necessary_land(path_to_regions, paths_to_region_attributes, path_to_capacity_factors,
                             path_to_output, config):
    """Determines the fraction of land needed in each region to fulfill the demand."""
    regions = gpd.read_file(path_to_regions)
    for path_to_region_attribute in paths_to_region_attributes:
        regions = regions.merge(pd.read_csv(path_to_region_attribute), on='id')
    cps = pd.read_csv(path_to_capacity_factors, index_col=0)
    max_yield_watt = pd.DataFrame({
        eligibility: _max_yield_watt(eligibility, regions, cps, config)
        for eligibility in Eligibility
    })
    regions["max_yield_twh_per_year"] = watt_to_watthours(
        max_yield_watt.sum(axis=1),
        timedelta(days=365)
    ).div(1e12)
    regions["fraction_land_necessary"] = (regions["demand_twh_per_year"] /
                                          regions["max_yield_twh_per_year"])
    regions.loc[regions["demand_twh_per_year"] <= ZERO_DEMAND, "fraction_land_necessary"] = 0.0 # nan otherwise
    regions.to_file(path_to_output, driver='GeoJSON')


def _max_yield_watt(eligibility, regions, cps, config):
    """Returns a pandas Series of maximum yields in all regions of given eligibility type in Watt."""
    available_area_km2 = regions[eligibility.property_name]
    capacity_factors = regions.country_code.map(lambda country_code: _cp(cps, country_code, eligibility))
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


def _cp(cps, country_code, eligibility):
    if eligibility in [Eligibility.ROOFTOP_PV, Eligibility.ONSHORE_WIND_OR_PV_FARM]:
        return cps.loc[country_code, "pv_capacity_factor"]
    elif eligibility == Eligibility.ONSHORE_WIND_FARM:
        return cps.loc[country_code, "onshore_capacity_factor"]
    elif eligibility == Eligibility.OFFSHORE_WIND_FARM:
        return cps.loc[country_code, "offshore_capacity_factor"]
    elif eligibility == Eligibility.NOT_ELIGIBLE:
        return 0
    else:
        raise ValueError("Unknown eligibility: {}".format(eligibility))


if __name__ == "__main__":
    determine_necessary_land()
