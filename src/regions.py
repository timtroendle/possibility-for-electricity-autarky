"""Remixes NUTS, LAU, and GADM data to form the regions of the analysis."""
import click
import pandas as pd
import geopandas as gpd
import fiona
import pycountry

from utils import Config

DRIVER = "GPKG"


@click.command()
@click.argument("path_to_nuts")
@click.argument("path_to_lau2")
@click.argument("path_to_gadm")
@click.argument("path_to_output")
@click.argument("config", type=Config())
def remix_regions(path_to_nuts, path_to_lau2, path_to_gadm, path_to_output, config):
    """Remixes NUTS, LAU, and GADM data to form the regions of the analysis."""
    source_layers = _read_source_layers(path_to_nuts, path_to_lau2, path_to_gadm)
    _validate_source_layers(source_layers)
    for layer_name in config["layers"].keys():
        _validate_layer(config, layer_name)
        layer = _build_layer(config["layers"][layer_name], source_layers)
        _write_layer(layer, layer_name, path_to_output)


def _read_source_layers(path_to_nuts, path_to_lau2, path_to_gadm):
    source_layers = {
        layer_name: gpd.read_file(path_to_nuts, layer=layer_name)
        for layer_name in fiona.listlayers(path_to_nuts)
    }
    source_layers["lau2"] = gpd.read_file(path_to_lau2)
    source_layers.update({
        layer_name: gpd.read_file(path_to_gadm, layer=layer_name)
        for layer_name in fiona.listlayers(path_to_gadm)
    })
    return source_layers


def _validate_source_layers(source_layers):
    crs = [layer.crs for layer in source_layers.values()]
    assert not crs or crs.count(crs[0]) == len(crs), "Source layers have different crs. They must match."


def _validate_layer(config, layer_name):
    country_scope = config["scope"]["countries"]
    layer = config["layers"][layer_name]
    assert all(country in layer.keys() for country in country_scope), ("Layer {} is not correctly "
                                                                       "defined.".format(layer_name))


def _build_layer(country_to_source_map, source_layers):
    crs = [layer.crs for layer in source_layers.values()][0]
    layer = pd.concat([
        source_layers[source_layer][source_layers[source_layer].country_code == _iso3(country)]
        for country, source_layer in country_to_source_map.items()
    ])
    assert isinstance(layer, pd.DataFrame)
    return gpd.GeoDataFrame(layer, crs=crs)


def _iso3(country_name):
    return pycountry.countries.lookup(country_name).alpha_3


def _write_layer(gpd, layer_id, path_to_file):
    gpd.to_file(
        path_to_file,
        layer=layer_id,
        driver=DRIVER
    )


if __name__ == "__main__":
    remix_regions()
