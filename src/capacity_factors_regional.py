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

    onshore_cfs, offshore_cfs = wind_capacity_factors(wind_cfs, regions)

    pd.DataFrame(
        index=regions.id,
        data={
            "onshore_capacity_factor": onshore_cfs,
            "offshore_capacity_factor": offshore_cfs,
            "pv_capacity_factor": national_cfs["pv_capacity_factor"]
        }
    ).to_csv(path_to_output, index=True, header=True)


def wind_capacity_factors(wind_cfs, regions):
    wind_cfs["wind_geometry"] = wind_cfs.geometry
    sjoin = gpd.sjoin(
        regions,
        wind_cfs,
        how="left",
        op="intersects"
    )
    sjoin["intersect_area"] = area_in_squaremeters(
        gpd.GeoSeries(
            sjoin.apply(lambda x: x.geometry.intersection(x.wind_geometry), axis=1),
            crs=regions.crs
        )
    )
    validate_intersection_area(sjoin, regions)
    normed_area = sjoin.groupby("id")["intersect_area"].transform(lambda x: x / x.sum())
    onshore_cfs = (normed_area * sjoin["onshore_capacity_factor"]).groupby(sjoin["id"]).sum().reindex(regions.id)
    offshore_cfs = (normed_area * sjoin["offshore_capacity_factor"]).groupby(sjoin["id"]).sum().reindex(regions.id)
    return onshore_cfs, offshore_cfs


def validate_intersection_area(sjoin, regions):
    actual_region_size = area_in_squaremeters(regions).sum()
    rel_mismatch = (abs(sjoin["intersect_area"].sum() - actual_region_size) / actual_region_size)
    assert rel_mismatch < 0.0, rel_mismatch


if __name__ == "__main__":
    allocate_capacity_factors()
