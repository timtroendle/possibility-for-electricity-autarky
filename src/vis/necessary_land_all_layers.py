"""Plot the land demand of municipalities to become autarkic."""
import click
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from src.potentials_constrained import _constrain_potential, _scaling_factor
from src.eligible_land import Eligibility
from src.vis.potentials_normed import RED, GREEN, BLUE

GENERATION_DENSE = 0.5 # land is generation dense when more than this fraction is used for energy farming


@click.command()
@click.argument("path_to_output")
def necessary_land(path_to_output):
    """Plot the land demand of municipalities to become autarkic."""
    sns.set_context('paper')
    X = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
    all_data = pd.concat([necessary_land_factor(share_from_pv, layer)
                          for share_from_pv in X
                          for layer in ["national", "subnational", "municipal"]])

    fig = plt.figure(figsize=(8, 4), constrained_layout=True)
    ax = fig.add_subplot(111)

    population_sum = all_data.groupby(["rooftop_pv_share", "layer"]).population_sum.sum()
    population_sum_in_dense_regions = all_data[all_data["fraction land necessary"] > 0.5].groupby(
        ["rooftop_pv_share", "layer"]
    ).population_sum.sum()

    sns.barplot(
        data=(population_sum / population_sum).reset_index(),
        x="rooftop_pv_share",
        y="population_sum",
        hue="layer",
        palette=[GREEN, RED, BLUE],
        hue_order=["municipal", "subnational", "national"],
        alpha=0.20,
        ax=ax
    )
    sns.barplot(
        data=(population_sum_in_dense_regions / population_sum).reset_index(),
        x="rooftop_pv_share",
        y="population_sum",
        hue="layer",
        palette=[GREEN, RED, BLUE],
        hue_order=["municipal", "subnational", "national"],
        alpha=0.85,
        ax=ax
    )

    handles, labels = ax.get_legend_handles_labels()
    ax.legend(handles[3:], labels[3:], loc='upper right')
    ax.set_xlabel("Maximal share of demand supplied by rooftop PV")
    ax.set_ylabel("Share of population living in generation dense regions")
    ax.set_xticklabels(["0%", "20%", "40%", "60%", "80%", "100%"])
    ax.set_yticklabels(["0%", "20%", "40%", "60%", "80%", "100%"])
    sns.despine(fig=fig)
    fig.savefig(path_to_output, dpi=300)


def _constrain_eligibility(eligibilities, scenario_config):
    constrained_prefer_pv = pd.DataFrame(
        index=eligibilities.index,
        data={eligibility.area_column_name: _scaling_factor(eligibility, scenario_config, prefer_pv=True)
              for eligibility in Eligibility}
    ) * eligibilities
    constrained_prefer_wind = pd.DataFrame(
        index=eligibilities.index,
        data={eligibility.area_column_name: _scaling_factor(eligibility, scenario_config, prefer_pv=False)
              for eligibility in Eligibility}
    ) * eligibilities
    return constrained_prefer_pv.where(
        constrained_prefer_pv > constrained_prefer_wind,
        other=constrained_prefer_wind
    )


def necessary_land_factor(share_from_pv, layer):
    # how much of the total land area do we need, if the demand can only be satisfied by a factor
    # share_from_pv from the rooftop pv?
    # ignore offshore as it distorts total area sizes
    assert share_from_pv <= 1
    config = {
        "share-protected-areas-used": 0.0,
        "pv-on-farmland": False,
        "share-farmland-used": 1,
        "share-forest-used-for-wind": 1,
        "share-other-land-used": 1,
        "share-offshore-used": 0,
        "share-rooftops-used": 1
    }
    path_to_demand = f"./build/{layer}/demand.csv"
    path_to_unconstrained_potentials_prefer_pv = f"./build/{layer}/unconstrained-potentials-prefer-pv.csv"
    path_to_unconstrained_potentials_prefer_wind = f"./build/{layer}/unconstrained-potentials-prefer-wind.csv"
    path_to_eligibility = f"./build/{layer}/regional-eligibility.csv"
    path_to_population = f"./build/{layer}/population.csv"
    demand = pd.read_csv(path_to_demand, index_col=0)["demand_twh_per_year"]
    unconstrained_potentials_prefer_pv = pd.read_csv(path_to_unconstrained_potentials_prefer_pv,
                                                     index_col=0).reindex(demand.index)
    unconstrained_potentials_prefer_wind = pd.read_csv(path_to_unconstrained_potentials_prefer_wind,
                                                       index_col=0).reindex(demand.index)
    eligibility = pd.read_csv(path_to_eligibility, index_col=0).reindex(demand.index)
    population = pd.read_csv(path_to_population, index_col=0)["population_sum"]

    constrained_potential = _constrain_potential(unconstrained_potentials_prefer_pv,
                                                 unconstrained_potentials_prefer_wind, config)
    constrained_eligibility = _constrain_eligibility(eligibility, config)
    pv = constrained_potential.eligibility_rooftop_pv_twh_per_year.where(
        constrained_potential.eligibility_rooftop_pv_twh_per_year < share_from_pv * demand,
        share_from_pv * demand
    )
    demand_after_rooftops = demand - pv
    assert (demand_after_rooftops >= 0).all()
    constrained_potential_without_rooftops = constrained_potential.copy()
    del constrained_potential_without_rooftops["eligibility_rooftop_pv_twh_per_year"]
    constrained_potential_without_rooftops = constrained_potential_without_rooftops.sum(axis=1)
    factor_available_land = (demand_after_rooftops / constrained_potential_without_rooftops)

    del constrained_eligibility["eligibility_offshore_wind_km2"]
    del eligibility["eligibility_offshore_wind_km2"]
    del constrained_eligibility["eligibility_offshore_wind_protected_km2"]
    del eligibility["eligibility_offshore_wind_protected_km2"]
    del constrained_eligibility["eligibility_rooftop_pv_km2"]
    del eligibility["eligibility_rooftop_pv_km2"]
    total_factor = constrained_eligibility.sum(axis=1) / eligibility.sum(axis=1) * factor_available_land
    total_factor[total_factor > 1] = 1
    total_factor = pd.DataFrame(
        index=total_factor.index,
        data={
            "fraction land necessary": total_factor.values,
            "population_sum": population,
            "layer": layer,
            "rooftop_pv_share": share_from_pv
        }
    )
    return total_factor.reset_index()


if __name__ == "__main__":
    necessary_land()
