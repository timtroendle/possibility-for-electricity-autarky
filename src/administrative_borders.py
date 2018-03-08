"""Module to merge and preprocess administrative borders."""
from itertools import chain

import click
import fiona
import shapely.geometry
from shapely.prepared import prep

from src.utils import Config

LAYER_NAME = "adm{layer_id}"
SCHEMA = {
    "properties": {"country_code": "str", "name": "str",
                   "region_type": "str"},
    "geometry": "MultiPolygon"
}


@click.command()
@click.argument("path_to_countries", nargs=-1, metavar="COUNTRIES...")
@click.argument("max_layer_depths", type=click.INT)
@click.argument("path_to_output")
@click.argument("config", type=Config())
def retrieve_administrative_borders(path_to_countries, max_layer_depths, path_to_output, config):
    study_area = shapely.geometry.box(
        minx=config["scope"]["bounds"]["x_min"],
        maxx=config["scope"]["bounds"]["x_max"],
        miny=config["scope"]["bounds"]["y_min"],
        maxy=config["scope"]["bounds"]["y_max"]
    )
    study_area = prep(study_area) # improves performance
    with fiona.open(path_to_countries[0], "r", layer=0) as first_country:
        crs = first_country.crs
        driver = first_country.driver
    for layer_id in range(max_layer_depths + 1):
        print("Merging layer {}...".format(layer_id))
        with fiona.open(path_to_output,
                        "w",
                        crs=crs,
                        schema=SCHEMA,
                        driver=driver,
                        layer=LAYER_NAME.format(layer_id=layer_id)) as merged_file:
            merged_file.writerecords(
                [feature for feature in chain(
                    *[_country_features(path_to_country, layer_id, study_area)
                      for path_to_country in path_to_countries])
                 ]
            )


def _country_features(path_to_file, layer_id, study_area):
    max_layer_id = int(fiona.listlayers(path_to_file)[-1][-1])
    layer_id = min(layer_id, max_layer_id)
    with fiona.open(path_to_file, "r", layer=layer_id) as country_file:
        for feature in filter(_in_study_area(study_area), country_file):
            new_feature = {}
            new_feature["properties"] = {}
            new_feature["properties"]["country_code"] = feature["properties"]["ISO"]
            new_feature["properties"]["name"] = (
                feature["properties"]["NAME_{}".format(layer_id)] if layer_id > 0
                else feature["properties"]["NAME_ENGLISH"]
            )
            new_feature["properties"]["region_type"] = (
                feature["properties"]["ENGTYPE_{}".format(layer_id)] if layer_id > 0
                else "country"
            )
            new_feature["geometry"] = _all_parts_in_study_area(feature, study_area)
            yield new_feature


def _in_study_area(study_area):
    def _in_study_area(feature):
        region = shapely.geometry.shape(feature["geometry"])
        if study_area.contains(region) or study_area.intersects(region):
            return True
        else:
            print("Removing {} as it is outside of study area.".format(_feature_name(feature)))
            return False
    return _in_study_area


def _all_parts_in_study_area(feature, study_area):
    region = shapely.geometry.shape(feature["geometry"])
    if not study_area.contains(region):
        print("Removing parts of {} outside of study area.".format(_feature_name(feature)))
        new_region = shapely.geometry.MultiPolygon([polygon for polygon in region.geoms
                                                    if study_area.contains(polygon)])
        region = new_region
    return shapely.geometry.mapping(region)


def _feature_name(feature):
    # brute force way of finding name
    # the problem is that the name of the feature depends on the layer
    for property_name in ["NAME_7", "NAME_6", "NAME_5", "NAME_4", "NAME_3", "NAME_2", "NAME_1",
                          "NAME_ENGLISH"]:
        try:
            name = feature["properties"][property_name]
            break
        except KeyError:
            pass # nothing to do here
    return name


if __name__ == "__main__":
    retrieve_administrative_borders()
