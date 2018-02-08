"""Module and script to process load data."""
from datetime import timedelta, datetime

import click
import pandas as pd
import numpy as np
import pycountry

from src.conversion import watt_to_watthours
from src.utils import Config


@click.command()
@click.argument('path_to_raw_load')
@click.argument('path_to_output_data')
@click.argument('config', type=Config())
def process_data(path_to_raw_load, path_to_output_data, config):
    """Extracts national energy demand 2016 from raw data."""
    data = read_load_profiles(
        path_to_raw_load=path_to_raw_load,
        start=datetime(2016, 1, 1),
        end=datetime(2017, 1, 1),
        country_codes_iso2=[pycountry.countries.lookup(country).alpha_2
                            for country in config["scope"]["countries"]]
    )
    watt_to_watthours(data.mean(), timedelta(days=365)).div(1000).div(1000).to_csv(
        path_to_output_data,
        header=["twh_per_year"],
        index_label="country_code"
    )


def read_load_profiles(path_to_raw_load, start, end, country_codes_iso2):
    """Reads national load data and handles outliers."""
    data = pd.read_csv(path_to_raw_load, nrows=9499818, parse_dates=[3])
    data = data[(data["variable"] == "load") & (data["attribute"] == "new")]
    data.drop(["variable", "attribute"], axis=1, inplace=True)
    data = data[(data.utc_timestamp >= start) &
                (data.utc_timestamp < end)]
    data = data.pivot(columns="region", index="utc_timestamp", values="data")
    national = data.loc[:, country_codes_iso2].copy()
    national.columns.name = "country_code"
    national.rename(columns=lambda iso2: pycountry.countries.lookup(iso2).alpha_3, inplace=True)
    return _handle_outliers(national)


def _handle_outliers(all_time_series):
    # considers all data < 1 and > 2 * mean invalid and replaces with last valid value
    all_time_series[all_time_series < 1] = np.nan
    for region in all_time_series:
        ts = all_time_series[region]
        all_time_series.loc[ts > 2 * ts.mean(), region] = np.nan
    return all_time_series.fillna(method="ffill")


if __name__ == '__main__':
    process_data()
