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
@click.argument("path_to_output")
@click.argument("config", type=Config())
def determine_necessary_land(path_to_regions, path_to_output, config):
    """Determines the fraction of land needed in each region to fulfill the demand."""
    regions = gpd.read_file(path_to_regions)
    max_yield = pd.DataFrame({
        eligibility: regions[eligibility.property_name] * _max_yield(config, eligibility) * 1e6
        for eligibility in Eligibility
    })
    regions["max_yield_twh_per_year"] = watt_to_watthours(
        max_yield.sum(axis=1),
        timedelta(days=365)
    ).div(1e12)
    regions["fraction_land_necessary"] = (regions["demand_twh_per_year"] /
                                          regions["max_yield_twh_per_year"])
    regions.loc[regions["demand_twh_per_year"] <= ZERO_DEMAND, "fraction_land_necessary"] = 0.0 # nan otherwise
    regions.to_file(path_to_output, driver='GeoJSON')


def _max_yield(config, eligibility):
    specific_energy_yield = config["parameters"]["specific-energy-yield"]
    return {
        Eligibility.NOT_ELIGIBLE: 0,
        Eligibility.ROOFTOP_PV: specific_energy_yield["rooftop-pv"],
        Eligibility.ONSHORE_WIND_OR_PV_FARM: max(specific_energy_yield["pv-farm"],
                                                 specific_energy_yield["onshore-wind"]),
        Eligibility.ONSHORE_WIND_FARM: specific_energy_yield["onshore-wind"],
        Eligibility.OFFSHORE_WIND_FARM: specific_energy_yield["offshore-wind"]
    }[eligibility]


if __name__ == "__main__":
    determine_necessary_land()
