"""Determines capacity factors on different geographic scales."""
from datetime import datetime

import click
import pandas as pd

from src.process_load import read_load_profiles


@click.command()
@click.argument("path_to_raw_load")
@click.argument("path_to_result")
def capacity_factors(path_to_raw_load, path_to_result):
    """Determines national and European global capacity factors."""
    national = read_load_profiles(
        path_to_raw_load,
        start=datetime(2016, 1, 1),
        end=datetime(2017, 1, 1)
    )
    cap_factors = national.apply(capacity_factor, axis="index")
    global_cap_factor = capacity_factor(national.sum(axis="columns"))
    with open(path_to_result, "w") as result_file:
        print("Global capacity factor: {:.2f}".format(global_cap_factor), file=result_file)
        print("Average national capacity factor: {:.2f}".format(cap_factors.mean()),
              file=result_file)


def capacity_factor(time_series):
    return time_series.mean() / time_series.max()


if __name__ == "__main__":
    capacity_factors()
