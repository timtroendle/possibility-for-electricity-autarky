"""Visualise patterns in load."""
from datetime import datetime

import click
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from src.process_load import read_load_profiles


@click.command()
@click.argument("path_to_load")
@click.argument("path_to_plot")
def visualise_capacity_factors(path_to_load, path_to_plot):
    sns.set_context('paper')
    national = read_load_profiles(
        path_to_load,
        start=datetime(2016, 1, 1),
        end=datetime(2017, 1, 1)
    )
    cap_factors = national.apply(capacity_factor, axis="index")
    cap_factors["EU"] = capacity_factor(national.sum(axis="columns"))
    fig = plt.figure(figsize=(8, 4))
    ax = fig.add_subplot(111)
    bars = ax.bar(cap_factors.index, cap_factors.values)
    bars[-1].set_color(plt.rcParams['axes.prop_cycle'].by_key()['color'][1])
    ax.axhline(
        cap_factors.mean(),
        color=plt.rcParams['axes.prop_cycle'].by_key()['color'][3],
        linestyle="dashed",
        label="EU average",
        linewidth=0.75
    )
    plt.legend()
    ax.set_xlabel("country")
    ax.set_ylabel("capacity factor")
    plt.tight_layout()
    for tick in ax.get_xticklabels():
        tick.set_rotation(90)
    fig.savefig(path_to_plot, dpi=300)


def capacity_factor(time_series):
    return time_series.mean() / time_series.max()


if __name__ == "__main__":
    visualise_capacity_factors()
