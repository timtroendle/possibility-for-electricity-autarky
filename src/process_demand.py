"""Module and script to process power demand data."""
from datetime import timedelta

import click
import pandas as pd

from src.conversion import watt_to_watthours


@click.command()
@click.argument('path_to_raw_data')
@click.argument('path_to_output_data')
def process_data(path_to_raw_data, path_to_output_data):
    """Extracts national energy demand 2016 from raw data."""
    data = pd.read_csv(path_to_raw_data, nrows=9499818, parse_dates=[3])
    data = data[(data["variable"] == "load") & (data["attribute"] == "new")]
    data.drop(["variable", "attribute"], axis=1, inplace=True)
    data = data.pivot(columns="region", index="utc_timestamp", values="data")
    watt_to_watthours(data["2016"].mean(), timedelta(days=365)).div(1000).div(1000).to_csv(
        path_to_output_data
    )


if __name__ == '__main__':
    process_data()
