"""Module to correct the eligibility of roof mounted pv."""
import math

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
@click.argument("path_to_sonnendach_estimate")
@click.argument("path_to_output")
@click.argument("config", type=Config())
def rooftop_correction(path_to_rooftop_area_share, path_to_eligibility, path_to_units,
                       path_to_local_eligibility, path_to_correction_factor,
                       path_to_sonnendach_estimate, path_to_output, config):
    """Calculate the rooftop area that is available in each unit.

    This is based on using only those areas that have been identified as buildings in the
    European Settlement Map and on a correction factor mapping from building footprints to
    available rooftop areas.
    """
    with rasterio.open(path_to_eligibility, "r") as f_eligibility:
        eligibility = f_eligibility.read(1)
    with rasterio.open(path_to_rooftop_area_share, "r") as f_rooftop_area_share:
        rooftop_area_share = f_rooftop_area_share.read(1)
        transform = f_rooftop_area_share.transform
    rooftop_area_share[eligibility != Eligibility.ROOFTOP_PV] = 0

    with fiona.open(path_to_units, "r") as src:
        zs = zonal_stats(
            vectors=src,
            raster=rooftop_area_share,
            affine=transform,
            stats="mean",
            nodata=-999
        )
        building_share = pd.Series(
            index=[feat["properties"]["id"] for feat in src],
            data=[stat["mean"] for stat in zs]
        ).fillna(0.0) # happens if there is no building in the unit
        swiss_mask = pd.Series( # needed for validation below
            index=[feat["properties"]["id"] for feat in src],
            data=[feat["properties"]["country_code"] == "CHE" for feat in src]
        )
    available_rooftop_share = _apply_scaling_factor(building_share, path_to_correction_factor)
    corrected_eligibilites = _correct_eligibilities(path_to_local_eligibility, available_rooftop_share)
    corrected_eligibilites.to_csv(path_to_output, header=True)
    _test_land_allocation(path_to_units, path_to_output)
    _test_sonnendach_comparison(corrected_eligibilites, path_to_sonnendach_estimate, swiss_mask)


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


def _test_sonnendach_comparison(corrected_eligibilites, path_to_sonnendach_estimate, swiss_mask):
    if len(corrected_eligibilites) == 1:
        return # the spatial resolution of this layer is too low to test
    our_estimate = corrected_eligibilites.loc[swiss_mask, Eligibility.ROOFTOP_PV.area_column_name].sum()
    with open(path_to_sonnendach_estimate, "r") as f_sonnendach_estimate:
        sonnendach_estimate = float(f_sonnendach_estimate.readline())
    assert math.isclose(our_estimate, sonnendach_estimate, rel_tol=0.02), our_estimate # 2%


if __name__ == "__main__":
    rooftop_correction()
