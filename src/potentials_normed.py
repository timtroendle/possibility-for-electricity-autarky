"""Determines the potential relative to demand."""
import click
import pandas as pd

from src.eligible_land import Eligibility

ZERO_DEMAND = 0.000001


@click.command()
@click.argument("paths_to_region_attributes", nargs=-1)
@click.argument("path_to_output")
def normed_potential(paths_to_region_attributes, path_to_output):
    """Determines the potential relative to demand."""
    attributes = pd.concat(
        [pd.read_csv(path_to_attribute).set_index("id") for path_to_attribute in paths_to_region_attributes],
        axis=1
    )
    determine_normed_potentials(
        demand_twh_per_year=attributes["demand_twh_per_year"],
        potentials=attributes[[eligibility.energy_column_name for eligibility in Eligibility]]
    ).to_csv(path_to_output, header=True)


def determine_normed_potentials(demand_twh_per_year, potentials):
    max_yield_twh_per_year = potentials.sum(axis=1)
    normed_potential = max_yield_twh_per_year / demand_twh_per_year
    normed_potential[demand_twh_per_year <= ZERO_DEMAND] = 0.0 # might be nan otherwise if yield is 0
    normed_potential.name = "normed_potential"
    normed_potential.index.name = "id"
    return normed_potential


if __name__ == "__main__":
    normed_potential()
