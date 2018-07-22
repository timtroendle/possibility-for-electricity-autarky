"""Merge renewable capacity factors and replace missing."""
import click
import pycountry
import numpy as np
import pandas as pd

from src.utils import Config


@click.command()
@click.argument("path_to_raw_wind")
@click.argument("path_to_raw_pv")
@click.argument("path_to_results")
@click.argument("config", type=Config())
def renewable_capacity_factors(path_to_raw_wind, path_to_raw_pv, path_to_results, config):
    """Aggregate and merge renewable capacity factors and replace missing.

    * PV are not considered missing.
    * Missing onshore are taken from other countries as defined in the configuration file.
    * Missing offshore are taken from onshore value of the same country.
    """
    country_codes = [pycountry.countries.lookup(country).alpha_2 for country in config["scope"]["countries"]]
    replacements = {pycountry.countries.lookup(key).alpha_2: pycountry.countries.lookup(value).alpha_2
                    for key, value in config["parameters"]["onshore-capacity-factor-replacement"].items()}
    wind_data = pd.read_csv(path_to_raw_wind, parse_dates=True, index_col=0)
    pv_data = pd.read_csv(path_to_raw_pv, parse_dates=True, index_col=0)
    cps = pd.concat(
        [
            wind_data.loc[:, [col for col in wind_data.columns if "ON" in col]].rename(
                columns=lambda name: name[:2]).mean().rename("onshore_capacity_factor").reindex(country_codes),
            wind_data.loc[:, [col for col in wind_data.columns if "OFF" in col]].rename(
                columns=lambda name: name[:2]).mean().rename("offshore_capacity_factor").reindex(country_codes),
            pv_data.mean().rename("pv_capacity_factor").reindex(country_codes)
        ],
        axis=1
    )
    for to_replace, from_replace in replacements.items():
        if np.isnan(cps.loc[to_replace, "onshore_capacity_factor"]):
            cps.loc[to_replace, "onshore_capacity_factor"] = cps.loc[from_replace, "onshore_capacity_factor"]
    missing_offshore = cps["offshore_capacity_factor"].isnull()
    cps.loc[missing_offshore, "offshore_capacity_factor"] = cps.loc[missing_offshore, "onshore_capacity_factor"]
    assert not cps.isnull().any().any()
    cps.index = [pycountry.countries.lookup(country_code).alpha_3 for country_code in cps.index]
    cps.index.name = "country_code"
    cps.to_csv(path_to_results, header=True)


if __name__ == "__main__":
    renewable_capacity_factors()
