from pathlib import Path

import click
import pandas as pd
import geopandas as gpd
import pycountry

from src.utils import Config


@click.command()
@click.argument("path_to_national_capacity_factors")
@click.argument("path_to_nuts2_capacity_factors")
@click.argument("path_to_national_regions")
@click.argument("path_to_nuts_regions")
@click.argument("path_to_output")
@click.argument("config", type=Config())
def wind_capacity_factors(path_to_national_capacity_factors, path_to_nuts2_capacity_factors,
                          path_to_national_regions, path_to_nuts_regions, path_to_output, config):
    """Create wind capacity factors with highest spatial resolution.

    Uses capacity factors on NUTS2 level where available, and otherwise national level.
    """
    nations = gpd.read_file(path_to_national_regions)
    nuts2 = gpd.read_file(path_to_nuts_regions, layer="nuts2")
    national_capacity_factors = pd.read_csv(path_to_national_capacity_factors, index_col=0)
    capacity_factors = pd.concat(
        (capacity_factors_for_country(country, national_capacity_factors, path_to_nuts2_capacity_factors,
                                      nations, nuts2)
         for country in config["scope"]["countries"]),
        ignore_index=True
    ).pipe(gpd.GeoDataFrame)
    capacity_factors.crs = nuts2.crs
    capacity_factors.to_file(path_to_output, driver="GeoJSON")


def capacity_factors_for_country(country, national_capacity_factors,
                                 path_to_nuts2_capacity_factors, nations, nuts2):
    iso2 = pycountry.countries.lookup(country).alpha_2
    path_to_nuts2 = Path(path_to_nuts2_capacity_factors) / f"{iso2}.csv"
    if path_to_nuts2.exists():
        return nuts2_capacity_factors(country, path_to_nuts2, national_capacity_factors, nuts2)
    else:
        return national_capacity_factor(country, national_capacity_factors, nations)


def national_capacity_factor(country, national_capacity_factors, nations):
    iso3 = pycountry.countries.lookup(country).alpha_3
    cf = nations.merge(
        national_capacity_factors.reset_index(),
        on="country_code",
        how="inner"
    )
    return cf.loc[cf.country_code == iso3, ["onshore_capacity_factor", "offshore_capacity_factor", "geometry"]]


def nuts2_capacity_factors(country, path_to_nuts2, national_capacity_factors, nuts2):
    iso3 = pycountry.countries.lookup(country).alpha_3
    capacity_factors = pd.read_csv(path_to_nuts2, index_col=0).reset_index(
        drop=True
    ).mean().transpose().rename("onshore_capacity_factor")
    capacity_factors.index.rename("id", inplace=True)
    capacity_factors = nuts2.merge(
        capacity_factors.reset_index(),
        on="id",
        how="inner"
    )
    capacity_factors["offshore_capacity_factor"] = national_capacity_factors.loc[iso3, "offshore_capacity_factor"]
    return capacity_factors.loc[:, ["onshore_capacity_factor", "offshore_capacity_factor", "geometry"]]


if __name__ == "__main__":
    wind_capacity_factors()
