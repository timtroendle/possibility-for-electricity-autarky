"""Determines how much fraction of the land is necessary to feed demand."""
import click
import pandas as pd

from src.utils import Config
from src.eligible_land import Eligibility

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
        potentials=attributes[[eligibility.energy_column_name for eligibility in Eligibility]]
    ).to_csv(path_to_output, header=True)


def determine_fraction_land_necessary(demand_twh_per_year, potentials):
    max_yield_twh_per_year = potentials.sum(axis=1)
    fraction_land_necessary = demand_twh_per_year / max_yield_twh_per_year
    fraction_land_necessary[demand_twh_per_year <= ZERO_DEMAND] = 0.0 # might be nan otherwise if yield is 0
    fraction_land_necessary.name = "fraction_land_necessary"
    fraction_land_necessary.index.name = "id"
    return fraction_land_necessary


if __name__ == "__main__":
    determine_necessary_land()
