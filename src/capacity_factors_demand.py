"""Determines capacity factors on different geographic scales."""
from datetime import datetime

import click

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
    average_cap_factor = average_capacity_factor(cap_factors, national.sum(axis="index"))
    with open(path_to_result, "w") as result_file:
        print("Global capacity factor: {:.2f}".format(global_cap_factor), file=result_file)
        print("Average national capacity factor: {:.2f}".format(average_cap_factor),
              file=result_file)


def capacity_factor(time_series):
    """Returns the capacity factor of a load or supply time series."""
    return time_series.mean() / time_series.max()


def average_capacity_factor(capacity_factors, demands):
    """Returns the average capacity factors weighted by yearly demand."""
    return (capacity_factors * demands).sum() / demands.sum()


if __name__ == "__main__":
    capacity_factors()
