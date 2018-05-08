"""Module to plot the solution matrix showing how sufficient power supply can be reached."""
import click
import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from src.vis.necessary_land import GREEN

LAND_THRESHOLD = 1.0 # fraction of land that can be used for energy farming
NET_IMPORTS = [1.0, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1, 0.0]
PROTECTION_DROPS = [0.0, 0.1, 0.2, 0.3, 0.5, 1.0]


@click.command()
@click.argument("path_to_results_full")
@click.argument("path_to_results_zero")
@click.argument("path_to_plot")
def solution_matrix(path_to_results_full, path_to_results_zero, path_to_plot):
    """Plot the solution matrix showing how sufficient power supply can be reached."""
    sns.set_context('paper')
    full_protection = gpd.read_file(path_to_results_full)
    zero_protection = gpd.read_file(path_to_results_zero)

    def __population_share_satisfied(protection_drop, net_import):
        return _population_share_satisfied(full_protection, zero_protection, protection_drop, net_import)
    heatmap = pd.DataFrame(
        index=NET_IMPORTS,
        data={
            protection_drop: [__population_share_satisfied(protection_drop, net_import)
                              for net_import in NET_IMPORTS]
            for protection_drop in PROTECTION_DROPS
        }
    )

    fig = plt.figure(figsize=(8, 3))
    pal = list(reversed(sns.light_palette(GREEN)))
    ax = fig.add_subplot(111)
    fig.subplots_adjust(left=0.2, right=0.8, bottom=0.15, top=0.95)
    sns.heatmap(heatmap, cmap=pal, ax=ax, cbar_kws={"label": "population with sufficient power supply"})
    ax.set_xlabel("share of protected areas used for energy")
    ax.set_ylabel("energy imports")
    fig.savefig(path_to_plot, dpi=300)


def _population_share_satisfied(full_protection, zero_protection, protection_drop, net_import):
    total_population = full_protection.population_sum.sum()
    fraction_land_necessary = full_protection.fraction_land_necessary - net_import # FIXME not correct
    protection_diff = ((full_protection.fraction_land_necessary - net_import) -
                       (zero_protection.fraction_land_necessary - net_import))
    fraction_land_necessary = fraction_land_necessary - protection_diff * protection_drop # FIXME incorrect
    satisfied_population = full_protection[fraction_land_necessary <= LAND_THRESHOLD].population_sum.sum()
    return satisfied_population / total_population


if __name__ == "__main__":
    solution_matrix()
