"""Visualise the theoretic potential of all renewable power technologies."""
import click
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns


@click.command()
@click.argument("path_to_demand")
@click.argument("path_to_technology_potentials")
@click.argument("path_to_plot")
def potentials(path_to_demand, path_to_technology_potentials, path_to_plot):
    """Visualise the theoretic potential of all renewable power technologies."""
    sns.set_context('paper')
    data = _normed_potentials(
        technology_potentials=pd.read_csv(path_to_technology_potentials, index_col=0),
        demand=pd.read_csv(path_to_demand, index_col=0)["demand_twh_per_year"]
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


def _normed_potentials(technology_potentials, demand):
    normed_potentials = technology_potentials.div(demand, axis="index")
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


if __name__ == "__main__":
    potentials()
