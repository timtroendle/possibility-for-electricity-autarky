"""Preprocess industrial load."""
import click
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point

from src.conversion import coordinate_string_to_decimal

CRS = "+init=epsg:4326" # WGS84
DRIVER = "GeoJSON"
COLUMNS = ["Installation", "Type", "Average electricity cons (MW)", "Coordinates"]
CHLORALKALI_COLUMNS = ["Company", "Average electricity cons (MW)", "Coordinates"]
OUTPUT_COLUMNS = {
    "Installation": "installation",
    "Type": "type",
    "Average electricity cons (MW)": "average-load-mw"
}


@click.command()
@click.argument("path_to_raw_data")
@click.argument("path_to_output")
def preprocess_industries(path_to_raw_data, path_to_output):
    """Preprocess raw industry data by creating a geo database of all plants."""
    industries = _read_raw_data(path_to_raw_data)
    geometries = industries["Coordinates"].map(lambda coords: Point(*coordinate_string_to_decimal(coords)))
    gdf = gpd.GeoDataFrame(
        industries.drop("Coordinates", axis="columns"),
        geometry=geometries,
        crs=CRS
    )
    gdf.to_file(path_to_output, driver=DRIVER)


def _read_raw_data(path_to_raw_data):
    steel = pd.read_excel(
        path_to_raw_data,
        sheetname="Total steel",
        skipfooter=1
    ).loc[:, COLUMNS]
    primary_aluminium = pd.read_excel(
        path_to_raw_data,
        sheetname="Total aluminium",
        skipfooter=27
    ).loc[:, COLUMNS]
    secondary_aluminium = pd.read_excel(
        path_to_raw_data,
        sheetname="Total aluminium",
        skiprows=27,
        skipfooter=1
    ).loc[:, COLUMNS]
    cement = pd.read_excel(
        path_to_raw_data,
        sheetname="Total cement",
        skipfooter=1
    ).loc[:, COLUMNS]
    chloralkali = pd.read_excel(
        path_to_raw_data,
        sheetname="Total chloralkali",
        skipfooter=1
    ).loc[:, CHLORALKALI_COLUMNS]
    chloralkali.rename(columns={"Company": "Installation"}, inplace=True)
    chloralkali["Type"] = "chloralkali"
    chloralkali.drop(21, axis="index", inplace=True)
    return pd.concat([steel, primary_aluminium, secondary_aluminium, cement, chloralkali]).rename(
        columns=OUTPUT_COLUMNS
    )


if __name__ == "__main__":
    preprocess_industries()
