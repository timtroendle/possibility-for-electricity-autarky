"""Preprocessing of raw NUTS data to bring it into normalised form."""
import click
import fiona
import shapely.geometry

from administrative_borders import SCHEMA, LAYER_NAME
from conversion import eu_country_code_to_iso3

OUTPUT_DRIVER = "GPKG"


@click.command()
@click.argument("path_to_nuts")
@click.argument("path_to_output")
def normalise_nuts(path_to_nuts, path_to_output):
    """Normalises raw NUTS data.

    Raw data contains all NUTS layers in one layer of one shapefile. The output
    of this function corresponds to the form the data is used in this analysis,
    where each geographical layer is stored in one layer of a GeoPackage.
    """
    with fiona.open(path_to_nuts, "r") as nuts_file:
        for layer_id in range(4):
            print("Building layer {}...".format(layer_id))
            _write_layer(nuts_file, path_to_output, layer_id)


def _write_layer(nuts_file, path_to_output, layer_id):
    with fiona.open(path_to_output,
                    "w",
                    crs=nuts_file.crs,
                    schema=SCHEMA,
                    driver=OUTPUT_DRIVER,
                    layer=LAYER_NAME.format(layer_id=layer_id)) as result_file:
        result_file.writerecords(_layer_features(nuts_file, layer_id))


def _layer_features(nuts_file, layer_id):
    for feature in nuts_file:
        if _feature_layer_id(feature) != layer_id:
            continue
        new_feature = {}
        new_feature["properties"] = {}
        new_feature["properties"]["country_code"] = eu_country_code_to_iso3(feature["properties"]["NUTS_ID"][:2])
        new_feature["properties"]["name"] = feature["properties"]["NUTS_ID"]
        new_feature["properties"]["region_type"] = None
        new_feature["geometry"] = _to_multi_polygon(feature["geometry"])
        yield new_feature


def _feature_layer_id(feature):
    return len(feature["properties"]["NUTS_ID"][2:])


def _to_multi_polygon(geometry):
    polygon_or_multipolygon = shapely.geometry.shape(geometry)
    multi_polygon = shapely.geometry.MultiPolygon(polygons=[polygon_or_multipolygon])
    return shapely.geometry.mapping(multi_polygon)


if __name__ == "__main__":
    normalise_nuts()
