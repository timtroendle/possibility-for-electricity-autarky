from multiprocessing import Pool
from itertools import cycle

import click
import pandas as pd
import geopandas as gpd
from rtree import index
from shapely.prepared import prep

EPSG_3035_PROJ4 = "+proj=laea +lat_0=52 +lon_0=10 +x_0=4321000 +y_0=3210000 +ellps=GRS80 +units=m +no_defs "


@click.command()
@click.argument("path_to_regions")
@click.argument("path_to_wind_capacity_factors")
@click.argument("path_to_pv_capacity_factors")
@click.argument("path_to_output")
@click.argument("threads", type=click.INT)
def allocate_capacity_factors(path_to_regions, path_to_wind_capacity_factors, path_to_pv_capacity_factors,
                              path_to_output, threads):
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
        ["flat_pv_capacity_factor", "tilted_pv_capacity_factor"],
        threads
    )
    wind_cfs = _allocate_capacity_factors(
        gpd.read_file(path_to_wind_capacity_factors).to_crs(EPSG_3035_PROJ4),
        regions,
        ["onshore_capacity_factor", "offshore_capacity_factor"],
        threads
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


def _allocate_capacity_factors(cfs, regions, cf_names, threads):
    with Pool(threads) as pool:
        return pd.DataFrame(
            data=pool.map(
                cf_region,
                zip(
                    [regions.loc[region_index] for region_index in regions.index],
                    cycle([cfs]),
                    cycle([cf_names])
                )
            ),
            columns=cf_names,
            index=regions.id
        )


def cf_region(args):
    region, cfs, cf_names = args

    def generator_function():
        for i in cfs.index:
            yield (i, cfs.loc[i, "geometry"].bounds, i)

    cf_index = index.Index(generator_function()) # should be generated only once, but cannot be pickled
    intersection = list(cf_index.intersection(region.geometry.bounds))
    prep_region = prep(region.geometry)
    intersection = list(filter(
        lambda ix: prep_region.intersects(cfs.loc[ix, "geometry"]),
        intersection
    ))
    if len(intersection) == 1:
        ix = intersection[0]
        return [cfs.loc[ix, cf_name] for cf_name in cf_names]
    else:
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
