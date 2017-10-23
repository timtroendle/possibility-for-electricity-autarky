"""Module and script to determine the spatial distribution of power demand."""
import click
import numpy as np
import pandas as pd
import geopandas as gpd


@click.command()
@click.argument("path_to_national_demand")
@click.argument("path_to_nuts")
@click.argument("path_to_results")
def spatial_distribution(path_to_national_demand, path_to_nuts, path_to_results):
    """Breaks down national demand data to NUTS3 level.

    This is done simply by assuming demand is proportional to population.
    """
    demand = pd.read_csv(path_to_national_demand, index_col="region")
    demand = demand["twh_per_year"]

    nuts = gpd.read_file(path_to_nuts)
    countries = nuts[nuts.STAT_LEVL_ == 0].copy()
    third_level = nuts[nuts.STAT_LEVL_ == 3].copy()
    third_level["COUNTRY_CODE"] = third_level["NUTS_ID"].map(lambda nuts_id: nuts_id[:-3])
    third_level["POPULATION_SHARE"] = third_level.groupby(
        "COUNTRY_CODE"
    )["population_sum"].transform(lambda x: x / sum(x))

    third_level["DEMAND_TWH_PER_YEAR"] = third_level.apply(
        _determine_national_demand_share(demand),
        axis=1
    )
    third_level.to_file(path_to_results)


def _determine_national_demand_share(demand):
    def determine_national_demand_share(row):
        country_code = row["COUNTRY_CODE"]
        if country_code == "EL":
            country_code = "GR" # Greece is GR in demand data.
        elif country_code == "UK":
            country_code = "GB" # UK is GB in demand data.
        try:
            return row["POPULATION_SHARE"] * demand[country_code]
        except KeyError:
            print("Demand value missing for country {}.".format(country_code))
            return np.nan
    return determine_national_demand_share


if __name__ == "__main__":
    spatial_distribution()
