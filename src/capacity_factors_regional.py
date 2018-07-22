import click
import pandas as pd
import geopandas as gpd

from src.conversion import area_in_squaremeters


@click.command()
@click.argument("path_to_regions")
@click.argument("path_to_wind_capacity_factors")
@click.argument("path_to_pv_capacity_factors")
@click.argument("path_to_output")
def allocate_capacity_factors(path_to_regions, path_to_wind_capacity_factors, path_to_pv_capacity_factors,
                              path_to_output):
    """Allocate renewable electricity capacity factors to regions.

    PV capacity factors are available on subnational level and those
    capacity factors are used area weighted based on the overlap the subnational regions have with the
    region in question.

    Wind capacity factors are available on NUTS2 level (most countries; only onshore), and those
    capacity factors are used area weighted based on the overlap the NUTS2 regions has with the
    region in question.
    """
    wind_cfs = gpd.read_file(path_to_wind_capacity_factors)
    regions = gpd.read_file(path_to_regions)
    pv_cfs = gpd.read_file(path_to_pv_capacity_factors)

    flat_pv_cfs, tilted_pv_cfs = _allocate_capacity_factors(
        pv_cfs,
        regions,
        ["flat_pv_capacity_factor", "tilted_pv_capacity_factor"]
    )
    onshore_cfs, offshore_cfs = _allocate_capacity_factors(
        wind_cfs,
        regions,
        ["onshore_capacity_factor", "offshore_capacity_factor"]
    )

    pd.DataFrame(
        index=regions.id,
        data={
            "onshore_capacity_factor": onshore_cfs,
            "offshore_capacity_factor": offshore_cfs,
            "flat_pv_capacity_factor": flat_pv_cfs,
            "tilted_pv_capacity_factor": tilted_pv_cfs
        }
    ).to_csv(path_to_output, index=True, header=True)


def _allocate_capacity_factors(cfs, regions, column_names):
    cfs["cfs_geometry"] = cfs.geometry
    sjoin = gpd.sjoin(
        regions,
        cfs,
        how="left",
        op="intersects"
    )
    sjoin["intersect_area"] = area_in_squaremeters(
        gpd.GeoSeries(
            sjoin.apply(lambda x: x.geometry.intersection(x.cfs_geometry), axis=1),
            crs=regions.crs
        )
    )
    validate_intersection_area(sjoin, regions)
    normed_area = sjoin.groupby("id")["intersect_area"].transform(lambda x: x / x.sum())
    return [(normed_area * sjoin[column_name]).groupby(sjoin["id"]).sum().reindex(regions.id)
            for column_name in column_names]


def validate_intersection_area(sjoin, regions):
    actual_region_size = area_in_squaremeters(regions).sum()
    rel_mismatch = (abs(sjoin["intersect_area"].sum() - actual_region_size) / actual_region_size)
    assert rel_mismatch < 0.05, rel_mismatch


if __name__ == "__main__":
    allocate_capacity_factors()
