import click
import pandas as pd
import geopandas as gpd

from src.conversion import area_in_squaremeters


@click.command()
@click.argument("path_to_regions")
@click.argument("path_to_wind_capacity_factors")
@click.argument("path_to_national_capacity_factors")
@click.argument("path_to_output")
def allocate_capacity_factors(path_to_regions, path_to_wind_capacity_factors, path_to_national_capacity_factors,
                              path_to_output):
    """Allocate renewable electricity capacity factors to regions.

    PV capacity factors are available on national level only and are allocated based on country code.

    Wind capacity factors are available on NUTS2 level (most countries; only onshore), and those
    capacity factors are used area weighted based on the overlap the NUTS2 regions has with the
    region in question.
    """
    wind_cfs = gpd.read_file(path_to_wind_capacity_factors)
    regions = gpd.read_file(path_to_regions)
    national_cfs = pd.read_csv(path_to_national_capacity_factors, index_col=0)
    national_cfs = national_cfs.reindex(regions.set_index("country_code").index)
    national_cfs.index = regions.id

    overlay = gpd.overlay(regions, wind_cfs, how="identity")
    pd.DataFrame(
        index=regions.id,
        data={
            "onshore_capacity_factor": overlay.groupby("id").apply(
                area_weighted_onshore_capacity_factor
            ).reindex(regions.id),
            "offshore_capacity_factor": overlay.groupby("id").apply(
                area_weighted_offshore_capacity_factor
            ).reindex(regions.id),
            "pv_capacity_factor": national_cfs["pv_capacity_factor"]
        }
    ).to_csv(path_to_output, index=True, header=True)


def area_weighted_onshore_capacity_factor(region):
    area = area_in_squaremeters(region)
    normed_area = area / area.sum()
    return (region["onshore_capacity_factor"] * normed_area).sum()


def area_weighted_offshore_capacity_factor(region):
    area = area_in_squaremeters(region)
    normed_area = area / area.sum()
    return (region["offshore_capacity_factor"] * normed_area).sum()


if __name__ == "__main__":
    allocate_capacity_factors()
