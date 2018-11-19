"""Determines the potential relative to demand."""
import click
import pandas as pd

from src.potentials import Potential


@click.command()
@click.argument("paths_to_unit_attributes", nargs=-1)
@click.argument("path_to_output")
def normed_potential(paths_to_unit_attributes, path_to_output):
    """Determines the potential relative to demand."""
    attributes = pd.concat(
        [pd.read_csv(path_to_attribute).set_index("id") for path_to_attribute in paths_to_unit_attributes],
        axis=1
    )
    determine_normed_potentials(
        demand_twh_per_year=attributes["demand_twh_per_year"],
        potentials=attributes[[str(potential) for potential in Potential]]
    ).to_csv(path_to_output, header=True)


def determine_normed_potentials(demand_twh_per_year, potentials):
    max_yield_twh_per_year = potentials.sum(axis=1)
    normed_potential = max_yield_twh_per_year / demand_twh_per_year
    normed_potential[normed_potential == pd.np.inf] = pd.np.nan # handle regions with no demand
    normed_potential.name = "normed_potential"
    normed_potential.index.name = "id"
    return normed_potential


if __name__ == "__main__":
    normed_potential()
