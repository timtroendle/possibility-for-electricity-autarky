"""Module to determine the potential of roof mounted pv."""
import click
import fiona
import pandas as pd
import rasterio
from rasterstats import zonal_stats

from src.eligibility import Eligibility
from src.eligibility_local import _test_land_allocation
from src.utils import Config


@click.command()
@click.argument("path_to_rooftop_area_share")
@click.argument("path_to_eligibility")
@click.argument("path_to_units")
@click.argument("path_to_local_eligibility")
@click.argument("path_to_correction_factor")
@click.argument("path_to_output")
@click.argument("config", type=Config())
def rooftop_correction(path_to_rooftop_area_share, path_to_eligibility, path_to_units,
                       path_to_local_eligibility, path_to_correction_factor, path_to_output, config):
    """Calculate the rooftop area that is available in each unit.

    This is based on using only those areas that have been identified as buildings in the
    European Settlement Map and on a correction factor mapping from building footprints to
    available rooftop areas.
    """
    with rasterio.open(path_to_eligibility, "r") as f_eligibility:
        eligibility = f_eligibility.read(1)
    with rasterio.open(path_to_rooftop_area_share, "r") as f_rooftop_area_share:
        rooftop_area_share = f_rooftop_area_share.read(1)
        affine = f_rooftop_area_share.affine
    rooftop_area_share[eligibility != Eligibility.ROOFTOP_PV] = 0

    with fiona.open(path_to_units, "r") as src:
        zs = zonal_stats(
            vectors=src,
            raster=rooftop_area_share,
            affine=affine,
            stats="mean",
            nodata=-999
        )
        building_share = pd.Series(
            index=[feat["properties"]["id"] for feat in src],
            data=[stat["mean"] for stat in zs]
        ).fillna(0.0) # happens if there is no building in the unit
    available_rooftop_share = _apply_scaling_factor(building_share, path_to_correction_factor)
    corrected_eligibilites = _correct_eligibilities(path_to_local_eligibility, available_rooftop_share)
    corrected_eligibilites.to_csv(path_to_output, header=True)
    _test_land_allocation(path_to_units, path_to_output)


def _apply_scaling_factor(building_share, path_to_correction_factor):
    # This accounts for the fact that not all rooftops areas are usable for PV.
    with open(path_to_correction_factor, "r") as f_factor:
        factor = float(f_factor.readline())
    return building_share * factor


def _correct_eligibilities(path_to_local_eligibility, available_rooftop_share):
    local_eligibility = pd.read_csv(path_to_local_eligibility, index_col=0)
    total_area = local_eligibility.sum(axis=1)
    total_unusable_area = local_eligibility[Eligibility.NOT_ELIGIBLE.area_column_name]
    uncorrected_rooftop_area = local_eligibility[Eligibility.ROOFTOP_PV.area_column_name]
    corrected_rooftop_area = total_area * available_rooftop_share
    rooftop_area_div = uncorrected_rooftop_area - corrected_rooftop_area
    local_eligibility[Eligibility.ROOFTOP_PV.area_column_name] = corrected_rooftop_area
    local_eligibility[Eligibility.NOT_ELIGIBLE.area_column_name] = total_unusable_area + rooftop_area_div
    return local_eligibility


if __name__ == "__main__":
    rooftop_correction()
