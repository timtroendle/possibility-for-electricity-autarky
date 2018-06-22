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
    """Extracts national energy demand 2017 from raw data."""
    data = read_load_profiles(
        path_to_raw_load=path_to_raw_load,
        start=datetime(2017, 1, 1),
        end=datetime(2018, 1, 1),
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
    data = pd.read_csv(path_to_raw_load, nrows=11357638, parse_dates=[3])
    data = data[(data["variable"] == "load")]
    data = data[(data.utc_timestamp >= start) &
                (data.utc_timestamp < end)]
    data = _remove_entsoe_power_statistic_data_where_possible(data)
    data.drop(["variable", "attribute"], axis=1, inplace=True)
    data = data.pivot(columns="region", index="utc_timestamp", values="data")
    national = data.loc[:, country_codes_iso2].copy()
    national.columns.name = "country_code"
    national.rename(columns=lambda iso2: pycountry.countries.lookup(iso2).alpha_3, inplace=True)
    _check_completeness(national)
    return _handle_outliers(national)


def _remove_entsoe_power_statistic_data_where_possible(load):
    sorted_load = load.sort_values(
        "attribute",
        ascending=False
    ) # will end with entsoe-transparency ahead of entsoe-power-statistics
    return sorted_load.drop_duplicates(["region", "utc_timestamp"], keep="first")


def _check_completeness(load):
    for country in load.columns[load.isnull().any()].tolist():
        print("Country {} has missing load values.".format(pycountry.countries.lookup(country).name))


def _handle_outliers(all_time_series):
    # considers all data < 0.25 * mean and > 2 * mean invalid and replaces with last valid value
    normed_load = all_time_series / all_time_series.mean()
    all_time_series[(normed_load < 0.25) | (normed_load > 2)] = np.nan
    return all_time_series.fillna(method="ffill")


if __name__ == '__main__':
    process_data()
