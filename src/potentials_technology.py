"""Aggregate the constrained potential per technology."""
import click
import pandas as pd

from src.utils import Config
from src.eligible_land import Eligibility
from src.potentials_constrained import _constrain_potential

PV_FARM = [
    Eligibility.ONSHORE_WIND_AND_PV_OTHER,
    Eligibility.ONSHORE_WIND_AND_PV_FARMLAND,
    Eligibility.ONSHORE_WIND_AND_PV_OTHER_PROTECTED,
    Eligibility.ONSHORE_WIND_AND_PV_FARMLAND_PROTECTED
]
ONSHORE = [
    Eligibility.ONSHORE_WIND_AND_PV_OTHER,
    Eligibility.ONSHORE_WIND_OTHER,
    Eligibility.ONSHORE_WIND_FARMLAND,
    Eligibility.ONSHORE_WIND_FOREST,
    Eligibility.ONSHORE_WIND_AND_PV_FARMLAND,
    Eligibility.ONSHORE_WIND_AND_PV_OTHER_PROTECTED,
    Eligibility.ONSHORE_WIND_OTHER_PROTECTED,
    Eligibility.ONSHORE_WIND_FARMLAND_PROTECTED,
    Eligibility.ONSHORE_WIND_FOREST_PROTECTED,
    Eligibility.ONSHORE_WIND_AND_PV_FARMLAND_PROTECTED,
]
OFFSHORE = [
    Eligibility.OFFSHORE_WIND,
    Eligibility.OFFSHORE_WIND_PROTECTED
]


@click.command()
@click.argument("path_to_unconstrained_potentials_prefer_pv")
@click.argument("path_to_unconstrained_potentials_prefer_wind")
@click.argument("path_to_output")
@click.argument("scenario")
@click.argument("config", type=Config())
def potentials_technology(path_to_unconstrained_potentials_prefer_pv, path_to_unconstrained_potentials_prefer_wind,
                          path_to_output, scenario, config):
    """Aggregate the constrained potential per technology."""
    _technology_potentials(
        pd.read_csv(path_to_unconstrained_potentials_prefer_pv, index_col=0),
        pd.read_csv(path_to_unconstrained_potentials_prefer_wind, index_col=0),
        config["scenarios"][scenario]
    ).to_csv(path_to_output, header=True)


def _technology_potentials(unconstrained_prefer_pv, unconstrained_prefer_wind, scenario_config):
    prefer_pv = _constrain_potential(unconstrained_prefer_pv, unconstrained_prefer_pv,
                                     scenario_config)
    prefer_wind = _constrain_potential(unconstrained_prefer_wind, unconstrained_prefer_wind,
                                       scenario_config)
    potentials = pd.DataFrame(
        index=prefer_pv.index,
        columns=["rooftop-pv", "pv-farm", "onshore wind", "offshore wind"]
    )
    potentials["rooftop-pv"] = prefer_pv[Eligibility.ROOFTOP_PV.energy_column_name]
    potentials["pv-farm"] = prefer_pv[[eligibility.energy_column_name for eligibility in PV_FARM]].sum(axis=1)
    potentials["onshore wind"] = prefer_wind[[eligibility.energy_column_name for eligibility in ONSHORE]].sum(axis=1)
    potentials["offshore wind"] = prefer_pv[[eligibility.energy_column_name for eligibility in OFFSHORE]].sum(axis=1)
    return potentials


if __name__ == "__main__":
    potentials_technology()
