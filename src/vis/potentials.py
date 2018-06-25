"""Visualise the theoretic potential of all renewable power technologies."""
import click
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

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
@click.argument("path_to_demand")
@click.argument("paths_to_unconstrained_potential_prefer_pv")
@click.argument("paths_to_unconstrained_potential_prefer_wind")
@click.argument("path_to_plot")
@click.argument("scenario")
@click.argument("config", type=Config())
def potentials(path_to_demand, paths_to_unconstrained_potential_prefer_pv,
               paths_to_unconstrained_potential_prefer_wind, path_to_plot,
               scenario, config):
    """Visualise the theoretic potential of all renewable power technologies."""
    sns.set_context('paper')
    data = _constrained_potentials(
        pd.read_csv(paths_to_unconstrained_potential_prefer_pv, index_col=0),
        pd.read_csv(paths_to_unconstrained_potential_prefer_wind, index_col=0),
        pd.read_csv(path_to_demand, index_col=0)["demand_twh_per_year"],
        config["scenarios"][scenario]
    )

    fig = plt.figure(figsize=(8, 6))
    ax = fig.add_subplot(111)
    ax.set_yscale("log")
    sns.stripplot(
        data=data.reset_index(),
        y="normed yield",
        x="tech",
        jitter=True,
        ax=ax
    )
    ax.axhline(1, color="r", linewidth=0.75, label="national demand")
    ax.set_ylabel("yield relative to national demand [-]")
    fig.savefig(path_to_plot, dpi=300)


def _constrained_potentials(unconstrained_prefer_pv, unconstrained_prefer_wind, demand, scenario_config):
    constrained_prefer_pv = _constrain_potential(unconstrained_prefer_pv, unconstrained_prefer_pv,
                                                 scenario_config)
    constrained_prefer_wind = _constrain_potential(unconstrained_prefer_wind, unconstrained_prefer_wind,
                                                   scenario_config)
    potentials = _absolute_potentials(constrained_prefer_pv, constrained_prefer_wind)
    normed_potentials = _normed_potentials(potentials, demand)

    data = pd.Series(
        index=pd.MultiIndex.from_product([
            demand.index,
            ["rooftop-pv", "pv-farm", "onshore wind", "offshore wind"]
        ], names=["country_code", "tech"]),
        name="normed yield"
    )
    for region in demand.index:
        for tech in ["rooftop-pv", "pv-farm", "onshore wind", "offshore wind"]:
            data.loc[region, tech] = normed_potentials.loc[region, tech]
    return data


def _absolute_potentials(prefer_pv, prefer_wind):
    potentials = pd.DataFrame(
        index=prefer_pv.index,
        columns=["rooftop-pv", "pv-farm", "onshore wind", "offshore wind"]
    )
    potentials["rooftop-pv"] = prefer_pv[Eligibility.ROOFTOP_PV.energy_column_name]
    potentials["pv-farm"] = prefer_pv[[eligibility.energy_column_name for eligibility in PV_FARM]].sum(axis=1)
    potentials["onshore wind"] = prefer_wind[[eligibility.energy_column_name for eligibility in ONSHORE]].sum(axis=1)
    potentials["offshore wind"] = prefer_pv[[eligibility.energy_column_name for eligibility in OFFSHORE]].sum(axis=1)
    return potentials


def _normed_potentials(potentials, demand):
    return potentials.div(demand, axis="index")


if __name__ == "__main__":
    potentials()
