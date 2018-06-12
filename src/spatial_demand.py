"""Module and script to determine the spatial distribution of power demand."""
from datetime import timedelta
import math

import click
import numpy as np
import pandas as pd
import geopandas as gpd

from src.conversion import watt_to_watthours

ZERO_DEMAND = 0.000001


@click.command()
@click.argument("path_to_national_demand")
@click.argument("path_to_industry_load")
@click.argument("path_to_regions")
@click.argument("path_to_population")
@click.argument("path_to_results")
def spatial_distribution(path_to_national_demand, path_to_industry_load, path_to_regions,
                         path_to_population, path_to_results):
    """Breaks down national demand data to regional level.

    This is done in two steps:
        (1) allocating industrial demand to the regions,
        (2) allocating non-industrial demand proportional to population.
    """
    total_demand = pd.read_csv(path_to_national_demand, index_col="country_code")
    industries = gpd.read_file(path_to_industry_load)
    industries["demand_twh_per_year"] = _determine_industry_demand(industries)
    regions = gpd.read_file(path_to_regions)
    regions = regions.merge(pd.read_csv(path_to_population), on='id')

    regional_industry_demand = _allocate_industry_demand_to_regions(industries, regions)
    assert math.isclose(regional_industry_demand.sum(), industries.demand_twh_per_year.sum())
    regional_non_industry_demand = _determine_non_industry_demand(total_demand, regional_industry_demand, regions)
    regions["demand_twh_per_year"] = regional_industry_demand + regional_non_industry_demand
    assert math.isclose(regions["demand_twh_per_year"].sum(), total_demand["twh_per_year"].sum())
    pd.DataFrame(regions).set_index("id")["demand_twh_per_year"].to_csv(path_to_results, header=True)


def _determine_industry_demand(industries):
    average_load_mw = industries["average-load-mw"]
    demand_mwh = watt_to_watthours(average_load_mw, timedelta(days=365))
    return demand_mwh / 1e6


def _determine_non_industry_demand(total_demand, regional_industry_demand, regions):
    national_industry_demand = regional_industry_demand.groupby(regions.country_code).sum()
    national_non_industry_demand = total_demand["twh_per_year"].sub(national_industry_demand, fill_value=0.0)
    population_share = regions.groupby(
        "country_code"
    )["population_sum"].transform(lambda x: x / sum(x))
    return regions.country_code.map(national_non_industry_demand) * population_share


def _allocate_industry_demand_to_regions(industries, regions):
    industries_and_regions = gpd.sjoin(industries, regions, how="left", op='within')
    for buffer_distance in np.linspace(start=0.01, stop=0.1, num=10):
        mask_industries_outside_regions = industries_and_regions["index_right"].isnull()
        if mask_industries_outside_regions.sum() == 0:
            break
        print("Could not allocate all industry plants to regions. Increasing the size of "
              "industry plants with distance {}.".format(buffer_distance))
        buffered_industry = industries.copy()
        buffered_industry.geometry = industries.buffer(distance=buffer_distance)
        matched = gpd.sjoin(
            buffered_industry[mask_industries_outside_regions],
            regions,
            how="left",
            op='intersects'
        ) # this might lead to more than one match, hence take only the first in next line
        industries_and_regions[mask_industries_outside_regions] = matched.groupby(matched.index).first()
    return industries_and_regions.groupby("index_right").demand_twh_per_year.sum().reindex(
        regions.index, fill_value=0.0
    )


if __name__ == "__main__":
    spatial_distribution()
