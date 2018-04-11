"""Module to decrease the total urban area to the areas that are available for PV."""
import click
import fiona
import rasterio
from rasterstats import zonal_stats

from eligible_land import Eligibility

NO_DATA_VALUE = -1


@click.command()
@click.argument("path_to_rooftop_area_share")
@click.argument("path_to_eligibility")
@click.argument("path_to_regions")
@click.argument("path_to_output")
def rooftop_correction(path_to_rooftop_area_share, path_to_eligibility, path_to_regions, path_to_output):
    """Reduce total urban area to the share that is available for PV.

    This is based on using only those areas that have been identified as roofs in the
    European Settlement Map.
    """
    with rasterio.open(path_to_eligibility, "r") as f_eligibility:
        eligibility = f_eligibility.read(1)
    with rasterio.open(path_to_rooftop_area_share, "r") as f_rooftop_area_share:
        rooftop_area_share = f_rooftop_area_share.read(1)
        affine = f_rooftop_area_share.affine
    rooftop_area_share[eligibility != Eligibility.ROOFTOP_PV] = NO_DATA_VALUE

    with fiona.open(path_to_regions, "r") as src:
        zs = zonal_stats(
            vectors=src,
            raster=rooftop_area_share,
            affine=affine,
            stats="mean",
            nodata=NO_DATA_VALUE
        )
        meta = src.meta.copy()
        meta["schema"]["properties"]["urban_rooftop_area_share"] = "float"
        new_features = [_update_feature(feature, stat["mean"]) for feature, stat in zip(src, zs)]

    with fiona.open(path_to_output, "w", **meta) as dst:
        dst.writerecords(new_features)


def _update_feature(feature, avg_rooftop_share):
    if avg_rooftop_share is None: # happens if there is no urban area in the region
        avg_rooftop_share = 0.0
    feature = feature.copy()
    feature["properties"]["urban_rooftop_area_share"] = avg_rooftop_share
    total_urban_area = feature["properties"][Eligibility.ROOFTOP_PV.property_name]
    feature["properties"][Eligibility.ROOFTOP_PV.property_name] = total_urban_area * avg_rooftop_share
    return feature


if __name__ == "__main__":
    rooftop_correction()
