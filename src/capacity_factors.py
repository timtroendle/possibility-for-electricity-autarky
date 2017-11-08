"""Determines capacity factors on different geographic scales."""
from datetime import datetime

import click
import pandas as pd

MAX_LOAD = 200000


@click.command()
@click.argument("path_to_raw_load")
@click.argument("path_to_result")
def capacity_factors(path_to_raw_load, path_to_result):
    """Determines national and European global capacity factors."""
    data = pd.read_csv(path_to_raw_load, nrows=9499818, parse_dates=[3])
    data = data[(data["variable"] == "load") & (data["attribute"] == "new")]
    data.drop(["variable", "attribute"], axis=1, inplace=True)
    data = data[(data.utc_timestamp >= datetime(2016, 1, 1)) &
                (data.utc_timestamp < datetime(2017, 1, 1))]
    data.loc[data.data > MAX_LOAD, "data"] = MAX_LOAD
    cap_factors = data.groupby("region").data.apply(capacity_factor)
    global_cap_factor = capacity_factor(data.groupby("utc_timestamp").data.sum())
    with open(path_to_result, "w") as result_file:
        print("Global capacity factor: {:.2f}".format(global_cap_factor), file=result_file)
        print("Average national capacity factor: {:.2f}".format(cap_factors.mean()),
              file=result_file)


def capacity_factor(time_series):
    return time_series.mean() / time_series.max()


if __name__ == "__main__":
    capacity_factors()
