"""Quantify the constrained potentials for renewable power in regions.

Based on the unconstrained potentials and rules to constrain it.
"""
import click
import pandas as pd

from src.utils import Config
from src.eligible_land import Eligibility


@click.command()
@click.argument("path_to_unconstrained_potentials_prefer_pv")
@click.argument("path_to_unconstrained_potentials_prefer_wind")
@click.argument("path_to_result")
@click.argument("scenario")
@click.argument("config", type=Config())
def constrained_potentials(path_to_unconstrained_potentials_prefer_pv, path_to_unconstrained_potentials_prefer_wind,
                           path_to_result, scenario, config):
    unconstrained_prefer_pv = pd.read_csv(path_to_unconstrained_potentials_prefer_pv, index_col=0)
    unconstrained_prefer_wind = pd.read_csv(path_to_unconstrained_potentials_prefer_wind, index_col=0)

    constrained = _constrain_potential(unconstrained_prefer_pv, unconstrained_prefer_wind,
                                       config["scenarios"][scenario])
    constrained.to_csv(path_to_result, header=True)


def _constrain_potential(unconstrained_prefer_pv, unconstrained_prefer_wind, scenario_config):
    if not scenario_config["pv-on-farmland"]:
        unconstrained_prefer_pv[Eligibility.ONSHORE_WIND_AND_PV_FARMLAND.energy_column_name] = 0
        unconstrained_prefer_pv[Eligibility.ONSHORE_WIND_AND_PV_FARMLAND_PROTECTED.energy_column_name] = 0
    constrained = unconstrained_prefer_pv.copy()
    constrained = constrained.where(unconstrained_prefer_pv > unconstrained_prefer_wind, unconstrained_prefer_wind)
    if not scenario_config["re-on-protected-areas"]:
        for eligibility in Eligibility.protected():
            constrained[eligibility.energy_column_name] = 0
    return constrained


if __name__ == "__main__":
    constrained_potentials()
