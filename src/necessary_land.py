"""Determines how much fraction of the land is necessary to feed demand."""
from datetime import timedelta

import click
import pandas as pd
import geopandas as gpd

from src.eligible_land import Eligibility
from src.conversion import watt_to_watthours


MAX_YIELD = {
    Eligibility.NOT_ELIGIBLE: 0,
    Eligibility.ROOFTOP_PV: 20,
    Eligibility.WIND_OR_PV_FARM: 20,
    Eligibility.WIND_FARM: 2
}
"""Max yield in [W/m^2] taken from MacKay 2009.

This is not installed power, but delivered power on average. These numbers are valid
for UK only and slightly outdated.
"""


@click.command()
@click.argument("path_to_regions")
@click.argument("path_to_output")
def determine_necessary_land(path_to_regions, path_to_output):
    """Determines the fraction of land needed in each region to fulfill the demand."""
    regions = gpd.read_file(path_to_regions)
    max_yield = pd.DataFrame({
        eligibility: regions[eligibility.property_name] * MAX_YIELD[eligibility] * 1e6
        for eligibility in Eligibility
    })
    regions["max_yield_twh_per_year"] = watt_to_watthours(
        max_yield.sum(axis=1),
        timedelta(days=365)
    ).div(1e12)
    regions["fraction_land_necessary"] = (regions["demand_twh_per_year"] /
                                          regions["max_yield_twh_per_year"])
    regions.to_file(path_to_output, driver='GeoJSON')


if __name__ == "__main__":
    determine_necessary_land()
