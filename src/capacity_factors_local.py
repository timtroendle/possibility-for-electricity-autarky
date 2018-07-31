from multiprocessing import Pool
from itertools import cycle

import click
import pandas as pd
import geopandas as gpd
from rtree import index
from shapely.prepared import prep

EPSG_3035_PROJ4 = "+proj=laea +lat_0=52 +lon_0=10 +x_0=4321000 +y_0=3210000 +ellps=GRS80 +units=m +no_defs "


@click.command()
@click.argument("path_to_units")
@click.argument("path_to_wind_capacity_factors")
@click.argument("path_to_pv_capacity_factors")
@click.argument("path_to_output")
@click.argument("threads", type=click.INT)
def allocate_capacity_factors(path_to_units, path_to_wind_capacity_factors, path_to_pv_capacity_factors,
                              path_to_output, threads):
    """Allocate renewable electricity capacity factors to units.

    PV capacity factors are available on regional level and those
    capacity factors are used area weighted based on the overlap the regional units have with the
    unit in question.

    Wind capacity factors are available on NUTS2 level (most countries; only onshore), and those
    capacity factors are used area weighted based on the overlap the NUTS2 units has with the
    unit in question.
    """
    units = gpd.read_file(path_to_units).to_crs(EPSG_3035_PROJ4)

    pv_cfs = _allocate_capacity_factors(
        gpd.read_file(path_to_pv_capacity_factors).to_crs(EPSG_3035_PROJ4),
        units,
        ["flat_pv_capacity_factor", "tilted_pv_capacity_factor"],
        threads
    )
    wind_cfs = _allocate_capacity_factors(
        gpd.read_file(path_to_wind_capacity_factors).to_crs(EPSG_3035_PROJ4),
        units,
        ["onshore_capacity_factor", "offshore_capacity_factor"],
        threads
    )

    pd.DataFrame(
        index=units.id,
        data={
            "onshore_capacity_factor": wind_cfs["onshore_capacity_factor"],
            "offshore_capacity_factor": wind_cfs["offshore_capacity_factor"],
            "flat_pv_capacity_factor": pv_cfs["flat_pv_capacity_factor"],
            "tilted_pv_capacity_factor": pv_cfs["tilted_pv_capacity_factor"]
        }
    ).to_csv(path_to_output, index=True, header=True)


def _allocate_capacity_factors(cfs, units, cf_names, threads):
    with Pool(threads) as pool:
        return pd.DataFrame(
            data=pool.map(
                cf_unit,
                zip(
                    [units.loc[unit_index] for unit_index in units.index],
                    cycle([cfs]),
                    cycle([cf_names])
                )
            ),
            columns=cf_names,
            index=units.id
        )


def cf_unit(args):
    unit, cfs, cf_names = args

    def generator_function():
        for i in cfs.index:
            yield (i, cfs.loc[i, "geometry"].bounds, i)

    cf_index = index.Index(generator_function()) # should be generated only once, but cannot be pickled
    intersection = list(cf_index.intersection(unit.geometry.bounds))
    prep_unit = prep(unit.geometry)
    intersection = list(filter(
        lambda ix: prep_unit.intersects(cfs.loc[ix, "geometry"]),
        intersection
    ))
    if len(intersection) == 1:
        ix = intersection[0]
        return [cfs.loc[ix, cf_name] for cf_name in cf_names]
    elif len(intersection) == 0:
        ix = list(cf_index.nearest(unit.geometry.bounds))[0]
        return [cfs.loc[ix, cf_name] for cf_name in cf_names]
    else:
        area = pd.Series(
            data=[unit.geometry.intersection(cfs.loc[ix, "geometry"]).area
                  for ix in intersection],
            index=intersection
        )
        normed_area = area / area.sum()
        return [(cfs.loc[area.index, cf_name] * normed_area).sum()
                for cf_name in cf_names]


if __name__ == "__main__":
    allocate_capacity_factors()
