"""Module to merge and preprocess administrative borders."""
from itertools import chain

import click
import fiona

LAYER_NAME = "adm{layer_id}"
SCHEMA = {
    "properties": {"country_code": "str", "name": "str",
                   "gadm_layer_id": "int", "region_type": "str"},
    "geometry": "MultiPolygon"
}


@click.command()
@click.argument("path_to_countries", nargs=-1, metavar="COUNTRIES...")
@click.argument("max_layer_depths", type=click.INT)
@click.argument("path_to_output")
def retrieve_administrative_borders(path_to_countries, max_layer_depths, path_to_output):
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
                [feature for feature in chain(*[_country_features(path_to_country, layer_id)
                                                for path_to_country in path_to_countries])])


def _country_features(path_to_file, layer_id):
    max_layer_id = int(fiona.listlayers(path_to_file)[-1][-1])
    layer_id = min(layer_id, max_layer_id)
    with fiona.open(path_to_file, "r", layer=layer_id) as country_file:
        for feature in country_file:
            new_feature = {}
            new_feature["properties"] = {}
            new_feature["properties"]["country_code"] = feature["properties"]["ISO"]
            new_feature["properties"]["name"] = (
                feature["properties"]["NAME_{}".format(layer_id)] if layer_id > 0
                else feature["properties"]["NAME_ENGLISH"]
            )
            new_feature["properties"]["gadm_layer_id"] = layer_id
            new_feature["properties"]["region_type"] = (
                feature["properties"]["ENGTYPE_{}".format(layer_id)] if layer_id > 0
                else "country"
            )
            new_feature["geometry"] = feature["geometry"]
            yield new_feature


if __name__ == "__main__":
    retrieve_administrative_borders()
