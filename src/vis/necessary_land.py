"""Plot the land demand of municipalities to become autarkic."""
import click
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from src.potentials_constrained import _constrain_potential


@click.command()
@click.argument("path_to_unconstrained_potentials_prefer_pv")
@click.argument("path_to_unconstrained_potentials_prefer_wind")
@click.argument("path_to_demand")
@click.argument("path_to_output")
def necessary_land(path_to_unconstrained_potentials_prefer_pv, path_to_unconstrained_potentials_prefer_wind,
                   path_to_demand, path_to_output):
    """Plot the land demand of municipalities to become autarkic."""
    sns.set_context('paper')
    demand = pd.read_csv(path_to_demand, index_col=0)["demand_twh_per_year"]
    unconstrained_potentials_prefer_pv = pd.read_csv(path_to_unconstrained_potentials_prefer_pv,
                                                     index_col=0).reindex(demand.index)
    unconstrained_potentials_prefer_wind = pd.read_csv(path_to_unconstrained_potentials_prefer_wind,
                                                       index_col=0).reindex(demand.index)

    fig = plt.figure(figsize=(8, 4))
    ax = fig.add_subplot(111)
    X = np.linspace(start=0, stop=1, num=41)
    for roof_pv in [0.0, 0.1, 0.5, 0.8, 1.0]:
        factor = necessary_land_factor(
            share_rooftops_used=roof_pv,
            demand=demand,
            unconstrained_potentials_prefer_pv=unconstrained_potentials_prefer_pv,
            unconstrained_potentials_prefer_wind=unconstrained_potentials_prefer_wind
        ).dropna()
        Y = [factor[factor >= x].count() for x in X]
        ax.plot(X, Y, label="{}% roof-mounted pv".format(roof_pv * 100))
    ax.vlines(0.05, 0, 120000, colors="r", linestyles="--", label="5%")
    ax.legend()
    ax.set_ylabel("number municipalities")
    ax.set_xlabel("fraction of land needed to become autarkic")
    fig.savefig(path_to_output, dpi=300)


def necessary_land_factor(share_rooftops_used, demand, unconstrained_potentials_prefer_pv,
                          unconstrained_potentials_prefer_wind):
    config = {
        "share-protected-areas-used": 0.0,
        "share-pv-on-farmland": 0.0,
        "share-farmland-used": 1,
        "share-forest-used-for-wind": 1,
        "share-other-land-used": 1,
        "share-offshore-used": 1,
        "share-rooftops-used": share_rooftops_used
    }
    constrained_potential = _constrain_potential(unconstrained_potentials_prefer_pv,
                                                 unconstrained_potentials_prefer_wind, config)
    demand_after_rooftops = demand - constrained_potential.eligibility_rooftop_pv_twh_per_year
    demand_after_rooftops[demand_after_rooftops < 0] = 0
    constrained_potential_without_rooftops = constrained_potential.copy()
    del constrained_potential_without_rooftops["eligibility_rooftop_pv_twh_per_year"]
    constrained_potential_without_rooftops = constrained_potential_without_rooftops.sum(axis=1)
    necessary_land_factor = (demand_after_rooftops / constrained_potential_without_rooftops)
    return necessary_land_factor


if __name__ == "__main__":
    necessary_land()
