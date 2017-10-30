"""Module to retrieve administrative borders as vector data."""
import tempfile
import zipfile
import io
from itertools import chain
from pathlib import Path

import click
import fiona
import pycountry
import requests
import requests_cache

from src import WEB_CACHE

COUNTRIES = [
    "Austria",
    "Belgium",
    "Bulgaria",
    "Croatia",
    "Cyprus",
    "Czech Republic",
    "Denmark",
    "Estonia",
    "Finland",
    "France",
    "Germany",
    "Greece",
    "Hungary",
    "Ireland",
    "Italy",
    "Latvia",
    "Lithuania",
    "Luxembourg",
    "Malta",
    "Netherlands",
    "Poland",
    "Portugal",
    "Romania",
    "Slovakia",
    "Slovenia",
    "Spain",
    "Sweden",
    "United Kingdom",
    "Norway",
    "Switzerland"
]

DATA_URL = "http://biogeo.ucdavis.edu/data/gadm2.8/gpkg/{iso_alpha_3}_adm_gpkg.zip"
FILE_NAME = "{iso_alpha_3}_adm.gpkg"
LAYER_NAME = "adm{layer_id}"
LAYER_IDS = [0, 1, 2, 3]
requests_cache.install_cache(WEB_CACHE)
SCHEMA = {
    "properties": {"country_code": "str", "name": "str",
                   "gadm_layer_id": "int", "type": "str"},
    "geometry": "MultiPolygon"
}

COUNTRIES_ISO_ALPHA_3 = [pycountry.countries.lookup(country).alpha_3 for country in COUNTRIES]


@click.command()
@click.argument("path_to_output")
def retrieve_administrative_borders(path_to_output):
    """Retrieves and merges administrative borders from GADM."""
    with tempfile.TemporaryDirectory(prefix='administrative-borders') as tmpdir:
        print("Downloading files...")
        country_paths = [_country(iso_alpha_3, tmpdir)
                         for iso_alpha_3 in COUNTRIES_ISO_ALPHA_3]
        print("Merging files...")
        _merge(country_paths, path_to_output)


def _country(iso_alpha_3, tmpdir):
    r = requests.get(DATA_URL.format(iso_alpha_3=iso_alpha_3))
    print("Downloading {}".format(r.url))
    z = zipfile.ZipFile(io.BytesIO(r.content))
    z.extractall(path=tmpdir)
    return (Path(tmpdir) / FILE_NAME.format(iso_alpha_3=iso_alpha_3)).absolute().as_posix()


def _merge(country_paths, path_to_output):
    for layer_id in LAYER_IDS:
        print("Merging layer {}...".format(layer_id))
        with fiona.open(country_paths[0], "r", layer=layer_id) as first_country:
            crs = first_country.crs
            driver = first_country.driver
        with fiona.open(path_to_output,
                        "w",
                        crs=crs,
                        schema=SCHEMA,
                        driver=driver,
                        layer=LAYER_NAME.format(layer_id=layer_id)) as merged_file:
            merged_file.writerecords(
                [feature for feature in chain(*[_country_features(path_to_country, layer_id)
                                                for path_to_country in country_paths])])


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
