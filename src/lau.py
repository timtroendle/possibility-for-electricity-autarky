"""Preprocessing of raw LAU2 data to bring it into normalised form."""
import click
import fiona
import fiona.transform
import shapely.geometry
import pycountry

from gadm import SCHEMA
from nuts import _to_multi_polygon, _study_area
from conversion import eu_country_code_to_iso3
from utils import Config

OUTPUT_DRIVER = "GPKG"


@click.command()
@click.argument("path_to_lau")
@click.argument("path_to_output")
@click.argument("config", type=Config())
def normalise_lau(path_to_lau, path_to_output, config):
    """Normalises raw LAU2 data."""
    with fiona.open(path_to_lau, "r") as lau_file, fiona.open(path_to_output,
                                                              "w",
                                                              crs=config["crs"],
                                                              schema=SCHEMA,
                                                              driver=OUTPUT_DRIVER,
                                                              layer="lau2") as result_file:
        result_file.writerecords(_layer_features(lau_file, config))


def _layer_features(lau_file, config):
    for feature in filter(lambda feature: _in_study_area(config, feature), lau_file):
        new_feature = {}
        new_feature["properties"] = {}
        new_feature["properties"]["country_code"] = eu_country_code_to_iso3(feature["properties"]["COMM_ID"][:2])
        new_feature["properties"]["name"] = feature["properties"]["COMM_ID"]
        new_feature["properties"]["region_type"] = None
        new_feature["geometry"] = _all_parts_in_study_area_and_crs(feature, lau_file.crs, config)
        yield new_feature


def _all_parts_in_study_area_and_crs(feature, src_crs, config):
    study_area = _study_area(config)
    region = _to_multi_polygon(feature["geometry"])
    if not study_area.contains(region):
        print("Removing parts of {} outside of study area.".format(feature["properties"]["COMM_ID"]))
        new_region = shapely.geometry.MultiPolygon([polygon for polygon in region.geoms
                                                    if study_area.contains(polygon)])
        region = new_region
    geometry = shapely.geometry.mapping(region)
    return fiona.transform.transform_geom(
        src_crs=src_crs,
        dst_crs=config["crs"],
        geom=geometry
    )


def _in_study_area(config, feature):
    study_area = _study_area(config)
    countries = [pycountry.countries.lookup(country) for country in config["scope"]["countries"]]
    region = shapely.geometry.shape(feature["geometry"])
    country = pycountry.countries.lookup(eu_country_code_to_iso3(feature["properties"]["COMM_ID"][:2]))
    if (country in countries) and (study_area.contains(region) or study_area.intersects(region)):
        return True
    else:
        print("Removing {} as it is outside of study area.".format(feature["properties"]["COMM_ID"]))
        return False


if __name__ == "__main__":
    normalise_lau()
