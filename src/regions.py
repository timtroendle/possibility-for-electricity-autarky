"""Remixes NUTS and GADM data to form the regions of the analysis."""
import click
import pandas as pd
import geopandas as gpd

DRIVER = "GPKG"


@click.command()
@click.argument("path_to_nuts")
@click.argument("path_to_gadm")
@click.argument("path_to_output")
def remix_regions(path_to_nuts, path_to_gadm, path_to_output):
    """Remixes NUTS and GADM data to form the regions of the analysis.

    Heuristic rules for remixing are the following:

    * NUTS 0-3 is the basis
    * minimise changes to stay close to NUTS
    * minimise standard deviation between average region size of countries by:
        * use lower level NUTS if possible (e.g. in layer 1 use NUTS2 instead of NUTS1 for Sweden)
        * use GADM if no lower level NUTS available

    The results of these rules are implemented in this function. The derivation
    of the results can be found in `notebooks/regions.ipynb`.
    """
    nuts0 = gpd.read_file(path_to_nuts, layer="adm0")
    nuts1 = gpd.read_file(path_to_nuts, layer="adm1")
    nuts2 = gpd.read_file(path_to_nuts, layer="adm2")
    nuts3 = gpd.read_file(path_to_nuts, layer="adm3")
    gadm1 = gpd.read_file(path_to_gadm, layer="adm1")
    gadm2 = gpd.read_file(path_to_gadm, layer="adm2")
    gadm3 = gpd.read_file(path_to_gadm, layer="adm3")

    mixer = _Mixer(nuts0, nuts1, nuts2, nuts3, gadm1, gadm2, gadm3)
    mixer.remix_country("NOR", ["nuts2", "nuts3", "gadm2"])
    mixer.remix_country("FIN", ["nuts2", "nuts3", "gadm3"])
    mixer.remix_country("SWE", ["nuts2", "nuts3", "gadm2"])
    mixer.remix_country("LTU", ["nuts1", "nuts3", "nuts3"])
    mixer.remix_country("LVA", ["nuts1", "nuts3", "gadm2"])
    mixer.remix_country("EST", ["nuts1", "nuts3", "nuts3"])

    mixer.to_file(path_to_output)


class _Mixer:

    def __init__(self, nuts0, nuts1, nuts2, nuts3, gadm1, gadm2, gadm3):
        self.__sources = {
            "nuts0": nuts0,
            "nuts1": nuts1,
            "nuts2": nuts2,
            "nuts3": nuts3,
            "gadm1": gadm1,
            "gadm2": gadm2,
            "gadm3": gadm3
        }
        self.layers = {
            0: nuts0,
            1: nuts1,
            2: nuts2,
            3: nuts3
        }
        self.__crs = nuts0.crs

    def remix_country(self, country_code, data_sources):
        for layer_id in [1, 2, 3]:
            self.layers[layer_id] = self._remix_layer(
                country_code=country_code,
                layer_id=layer_id,
                data_source=data_sources[layer_id - 1]
            )

    def _remix_layer(self, country_code, layer_id, data_source):
        layer = pd.DataFrame(self.layers[layer_id])
        src = self.__sources[data_source]
        layer = layer.drop(
            layer[layer.country_code == country_code].index,
            axis="index"
        )
        df = pd.concat([layer, src[src.country_code == country_code]])
        return gpd.GeoDataFrame(df, crs=self.__crs)

    def to_file(self, path_to_file):
        for layer_id in range(4):
            self.layers[layer_id].to_file(
                path_to_file,
                layer="adm{}".format(layer_id),
                driver=DRIVER
            )


if __name__ == "__main__":
    remix_regions()
