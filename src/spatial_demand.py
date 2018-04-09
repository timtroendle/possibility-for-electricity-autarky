"""Module and script to determine the spatial distribution of power demand."""
import click
import pandas as pd
import geopandas as gpd


@click.command()
@click.argument("path_to_national_demand")
@click.argument("path_to_regions")
@click.argument("path_to_results")
def spatial_distribution(path_to_national_demand, path_to_regions, path_to_results):
    """Breaks down national demand data to regional level.

    This is done simply by assuming demand is proportional to population.
    """
    demand = pd.read_csv(path_to_national_demand, index_col="country_code")

    regions = gpd.read_file(path_to_regions)
    regions = _fix_population_sum(regions)
    population_share = regions.groupby(
        "country_code"
    )["population_sum"].transform(lambda x: x / sum(x))
    national_demand = regions.country_code.map(demand["twh_per_year"])
    regions["demand_twh_per_year"] = national_demand * population_share
    regions.to_file(path_to_results, driver='GeoJSON')


def _fix_population_sum(regions):
    # FIXME this is because some regions are so small, they contain no pixel
    # of the population data set. Using a higher resolution population data
    # set would help. Currently this impacts ~ 700 of ~ 120000 municipalities.
    # It is hence not criticial.
    regions.loc[regions["population_sum"].isnull(), "population_sum"] = 0
    return regions


if __name__ == "__main__":
    spatial_distribution()
