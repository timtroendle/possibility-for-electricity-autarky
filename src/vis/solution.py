"""Module to plot the solution matrix showing how sufficient power supply can be reached."""
import click
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from src.vis.necessary_land import GREEN

NET_IMPORTS = [0.4, 0.3, 0.2, 0.1, 0.0]
PROTECTION_DROPS = [0.0, 0.1, 0.2, 0.3, 1.0]


@click.command()
@click.argument("paths_to_region_attributes", nargs=-1)
@click.argument("path_to_potentials_full")
@click.argument("path_to_potentials_zero")
@click.argument("path_to_plot")
def solution_matrix(paths_to_region_attributes, path_to_potentials_full, path_to_potentials_zero,
                    path_to_plot):
    """Plot the solution matrix showing how sufficient power supply can be reached."""
    sns.set_context('paper')

    attributes = pd.concat(
        [pd.read_csv(path_to_attribute).set_index("id") for path_to_attribute in paths_to_region_attributes],
        axis=1,
        sort=True
    )
    potentials_full = pd.read_csv(path_to_potentials_full).set_index("id").sum(axis=1)
    potentials_zero = pd.read_csv(path_to_potentials_zero).set_index("id").sum(axis=1)

    def __population_share_satisfied(protection_drop, net_import):
        return _population_share_satisfied(
            population=attributes["population_sum"],
            demand=attributes["demand_twh_per_year"],
            potentials_full=potentials_full,
            potentials_zero=potentials_zero,
            protection_drop=protection_drop,
            net_import=net_import)
    heatmap = pd.DataFrame(
        index=NET_IMPORTS,
        data={
            protection_drop: [__population_share_satisfied(protection_drop, net_import)
                              for net_import in NET_IMPORTS]
            for protection_drop in PROTECTION_DROPS
        }
    )

    fig = plt.figure(figsize=(8, 3))
    pal = sns.light_palette(GREEN, reverse=False, as_cmap=True)
    ax = fig.add_subplot(111)
    fig.subplots_adjust(left=0.2, right=0.8, bottom=0.15, top=0.95)
    sns.heatmap(
        heatmap,
        cmap=pal,
        ax=ax,
        cbar_kws={"label": "population share with sufficient supply"}
    )
    ax.set_xlabel("share of protected areas used for energy")
    ax.set_ylabel("electricity imports")
    cbar_axes = fig.axes[-1]
    cbar_axes.set_yticklabels([_to_percentage(float(label.get_text()))
                               for label in cbar_axes.get_yticklabels()])
    ax.set_yticklabels([_to_percentage(float(label.get_text()))
                        for label in ax.get_yticklabels()])
    ax.set_xticklabels([_to_percentage(float(label.get_text()))
                        for label in ax.get_xticklabels()])
    fig.savefig(path_to_plot, dpi=300)


def _population_share_satisfied(population, demand, potentials_full, potentials_zero,
                                protection_drop, net_import):
    demand = (demand - net_import * demand).reindex(potentials_full.index)
    potentials = potentials_full + (potentials_zero - potentials_full) * protection_drop
    satisfied_population = population[potentials > demand].sum()
    return satisfied_population / population.sum()


def _to_percentage(fraction):
    return "{:d}%".format(int(fraction * 100))


if __name__ == "__main__":
    solution_matrix()
