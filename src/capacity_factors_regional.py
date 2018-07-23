import click
import pandas as pd
import geopandas as gpd
from rtree import index

EPSG_3035_PROJ4 = "+proj=laea +lat_0=52 +lon_0=10 +x_0=4321000 +y_0=3210000 +ellps=GRS80 +units=m +no_defs "


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
    regions = gpd.read_file(path_to_regions).to_crs(EPSG_3035_PROJ4)

    pv_cfs = _allocate_capacity_factors(
        gpd.read_file(path_to_pv_capacity_factors).to_crs(EPSG_3035_PROJ4),
        regions,
        ["flat_pv_capacity_factor", "tilted_pv_capacity_factor"]
    )
    wind_cfs = _allocate_capacity_factors(
        gpd.read_file(path_to_wind_capacity_factors).to_crs(EPSG_3035_PROJ4),
        regions,
        ["onshore_capacity_factor", "offshore_capacity_factor"]
    )

    pd.DataFrame(
        index=regions.id,
        data={
            "onshore_capacity_factor": wind_cfs["onshore_capacity_factor"],
            "offshore_capacity_factor": wind_cfs["offshore_capacity_factor"],
            "flat_pv_capacity_factor": pv_cfs["flat_pv_capacity_factor"],
            "tilted_pv_capacity_factor": pv_cfs["tilted_pv_capacity_factor"]
        }
    ).to_csv(path_to_output, index=True, header=True)


def _allocate_capacity_factors(cfs, regions, cf_names):
    cfs_idx = index.Index()
    for i in cfs.index:
        cfs_idx.insert(i, cfs.loc[i, "geometry"].bounds)

    return pd.DataFrame(
        data=[cf_region(regions.loc[region_index], cfs_idx, cfs, cf_names)
              for region_index in regions.index],
        columns=cf_names,
        index=regions.id
    )


def cf_region(region, cf_index, cfs, cf_names):
    intersection = list(cf_index.intersection(region.geometry.bounds))
    area = pd.Series(
        data=[region.geometry.intersection(cfs.loc[ix, "geometry"]).area
              for ix in intersection],
        index=intersection
    )
    normed_area = area / area.sum()
    return [(cfs.loc[area.index, cf_name] * normed_area).sum()
            for cf_name in cf_names]


if __name__ == "__main__":
    allocate_capacity_factors()
