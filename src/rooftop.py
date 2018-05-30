"""Module to determine the potential of roof mounted pv."""
import click
import fiona
import pandas as pd
import rasterio
from rasterstats import zonal_stats

from eligible_land import Eligibility
from regional_eligibility import _test_land_allocation

NO_DATA_VALUE = -1


@click.command()
@click.argument("path_to_rooftop_area_share")
@click.argument("path_to_eligibility")
@click.argument("path_to_regions")
@click.argument("path_to_regional_eligibility")
@click.argument("path_to_output")
def rooftop_correction(path_to_rooftop_area_share, path_to_eligibility, path_to_regions,
                       path_to_regional_eligibility, path_to_output):
    """Calculate the rooftop area that is available in each region.

    This is based on using only those areas that have been identified as roofs in the
    European Settlement Map.
    """
    with rasterio.open(path_to_eligibility, "r") as f_eligibility:
        eligibility = f_eligibility.read(1)
    with rasterio.open(path_to_rooftop_area_share, "r") as f_rooftop_area_share:
        rooftop_area_share = f_rooftop_area_share.read(1)
        affine = f_rooftop_area_share.affine
    rooftop_area_share[eligibility != Eligibility.NOT_ELIGIBLE] = NO_DATA_VALUE

    with fiona.open(path_to_regions, "r") as src:
        zs = zonal_stats(
            vectors=src,
            raster=rooftop_area_share,
            affine=affine,
            stats="mean",
            nodata=NO_DATA_VALUE
        )
        building_share = pd.Series(
            index=[feat["properties"]["id"] for feat in src],
            data=[stat["mean"] for stat in zs]
        ).fillna(0.0) # happens if there is no building in the region
    corrected_eligibilites = _correct_eligibilities(path_to_regional_eligibility, building_share)

    corrected_eligibilites.to_csv(path_to_output, header=True)
    _test_land_allocation(path_to_regions, path_to_output)


def _correct_eligibilities(path_to_regional_eligibility, building_share):
    regional_eligibility = pd.read_csv(path_to_regional_eligibility, index_col=0)
    total_unusable_area = regional_eligibility[Eligibility.NOT_ELIGIBLE.property_name]
    rooftop_area = total_unusable_area * building_share
    regional_eligibility[Eligibility.ROOFTOP_PV.property_name] = rooftop_area
    regional_eligibility[Eligibility.NOT_ELIGIBLE.property_name] = total_unusable_area - rooftop_area
    return regional_eligibility


if __name__ == "__main__":
    rooftop_correction()
