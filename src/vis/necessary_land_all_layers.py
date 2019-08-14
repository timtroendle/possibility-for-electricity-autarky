"""Plot the land demand of municipalities to become autarkic."""
import click
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from src.vis import RED, GREEN, BLUE

GENERATION_DENSE = 0.33 # land is generation dense when more than this fraction is used for energy farming
LIGHT_RED = "#E3D9D9"
LIGHT_GREEN = "#DFE2DB"
LIGHT_BLUE = "#DADCE2"


@click.command()
@click.argument("paths_to_input", nargs=-1)
@click.argument("path_to_output")
def necessary_land(paths_to_input, path_to_output):
    """Plot the land demand of municipalities to become autarkic."""
    sns.set_context('paper')

    paths_to_population = [path for path in paths_to_input if "population" in path]
    paths_to_necessary_land = [path for path in paths_to_input if "population" not in path]
    all_data = _read_all_data(paths_to_population, paths_to_necessary_land)

    fig = plt.figure(figsize=(8, 4), constrained_layout=True)
    ax = fig.add_subplot(111)

    population_sum = all_data.groupby(["rooftop_pv_share", "layer"]).population_sum.sum()
    dense = all_data["fraction_non_built_up_land_necessary"] > GENERATION_DENSE
    population_sum_in_dense_units = all_data[dense].groupby(
        ["rooftop_pv_share", "layer"]
    ).population_sum.sum()

    sns.barplot(
        data=(population_sum / population_sum).reset_index(),
        x="rooftop_pv_share",
        y="population_sum",
        hue="layer",
        palette=[LIGHT_GREEN, LIGHT_RED, LIGHT_BLUE],
        saturation=1,
        hue_order=["municipal", "regional", "national"],
        ax=ax
    )
    sns.barplot(
        data=(population_sum_in_dense_units / population_sum).reset_index(),
        x="rooftop_pv_share",
        y="population_sum",
        hue="layer",
        palette=[GREEN, RED, BLUE],
        saturation=0.85,
        hue_order=["municipal", "regional", "national"],
        ax=ax
    )

    handles, labels = ax.get_legend_handles_labels()
    ax.legend(handles[3:], labels[3:], loc='upper right')
    ax.set_xlabel("Maximum share of demand supplied by rooftop PV")
    ax.set_ylabel("Share of population living in generation dense units")
    ax.set_xticklabels(["{:.0f}%".format(tick) for tick in all_data.rooftop_pv_share.unique()])
    ax.set_yticklabels(["{:.0f}%".format(tick * 100) for tick in ax.get_yticks()])
    sns.despine(fig=fig)
    if path_to_output[-3:] == "png":
        fig.savefig(path_to_output, dpi=600, transparent=False)
    else:
        fig.savefig(path_to_output, dpi=600, transparent=False, pil_kwargs={"compression": "tiff_lzw"})


def _read_all_data(paths_to_population, paths_to_necessary_land):
    # read all data and create one dataframe in long form
    populations = {
        _infer_layer(path_to_population): pd.read_csv(path_to_population)
        for path_to_population in paths_to_population
    }
    return pd.concat([_read_necessary_land(path_to_necessary_land, populations)
                      for path_to_necessary_land in paths_to_necessary_land])


def _read_necessary_land(path_to_necessary_land, populations):
    layer = _infer_layer(path_to_necessary_land)
    pvshare = _infer_pvshare(path_to_necessary_land)
    data = pd.merge(
        pd.read_csv(path_to_necessary_land),
        populations[layer],
        on="id"
    )
    data["layer"] = layer
    data["rooftop_pv_share"] = pvshare
    return data.set_index("id")


def _infer_layer(path):
    return path.split("/")[1]


def _infer_pvshare(path):
    pvshare = int(path.split("%")[0][-2:])
    if pvshare == 0: # pvshare might be 100
        try:
            pvshare = int(path.split("%")[0][-3:])
            assert pvshare == 100
        except ValueError:
            pass # nothing to do, pvshare is 0
        return pvshare
    assert pvshare > 0
    assert pvshare < 100
    return pvshare


if __name__ == "__main__":
    necessary_land()
