"""Determines how much fraction of the land is necessary to feed demand."""
from datetime import timedelta
from pathlib import Path

import click
import pandas as pd
import geopandas as gpd

from src.available_land import Availability
from src.conversion import watt_to_watthours, area_in_squaremeters


MAX_YIELD = {
    Availability.NOT_AVAILABLE: 0,
    Availability.ROOFTOP_PV: 20,
    Availability.WIND_OR_PV_FARM: 20,
    Availability.WIND_FARM: 2
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
    available_land = pd.DataFrame({
        availability: regions["availability{}".format(int(availability))]
        for availability in Availability
    })
    area_sizes = area_in_squaremeters(regions)
    available_land = ((available_land.transpose() / available_land.sum(axis=1)) *
                      area_sizes).transpose()
    max_yield = pd.DataFrame({
        availability: available_land[availability] * MAX_YIELD[availability]
        for availability in Availability
    })
    regions["max_yield_twh_per_year"] = watt_to_watthours(
        max_yield.sum(axis=1),
        timedelta(days=365)
    ).div(1e12)
    regions["fraction_land_necessary"] = (regions["DEMAND_TWH_PER_YEAR"] /
                                          regions["max_yield_twh_per_year"])
    if Path(path_to_output).exists():
        Path(path_to_output).unlink() # somehow fiona cannot overwrite existing GeoJSON
    regions.to_file(path_to_output, driver='GeoJSON')


if __name__ == "__main__":
    determine_necessary_land()
