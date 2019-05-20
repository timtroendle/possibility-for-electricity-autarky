import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import pycountry

WGS_84 = "+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs"
COLUMN_NAME = "hydro_twh_per_year"


def main(path_to_plants, path_to_units, path_to_national_generation, year, path_to_output):
    locations = gpd.read_file(path_to_units).to_crs(WGS_84).set_index("id")
    plants = pd.read_csv(path_to_plants, index_col="id")
    plants["country_code"] = plants["country_code"].map(lambda iso2: pycountry.countries.lookup(iso2).alpha_3)
    annual_national_generation_twh = read_generation(path_to_national_generation, year)
    plants[COLUMN_NAME] = allocate_generation_to_plant(plants, annual_national_generation_twh)

    generation_per_location(plants, locations).to_csv(
        path_to_output,
        header=True,
        index=True
    )


def generation_per_location(plants, locations):
    plant_centroids = gpd.GeoDataFrame(
        crs=WGS_84,
        geometry=list(map(Point, zip(plants.lon, plants.lat))),
        index=plants.index
    )
    location_of_plant = gpd.sjoin(plant_centroids, locations, how="left", op='intersects')["index_right"]
    location_of_plant = location_of_plant[~location_of_plant.index.duplicated()]
    return (plants.groupby(location_of_plant)
                  .sum()
                  .loc[:, COLUMN_NAME]
                  .reindex(index=locations.index, fill_value=0))


def read_generation(path_to_generation, year):
    return pd.read_excel(
        path_to_generation,
        sheet_name="Gen 10-18",
        usecols="A,D:G",
        index_col=[0, 1, 2, 3],
        names=["country_code", "product", "year", "type", "generation"]
    )["generation"].to_xarray().sel(type="ONG", year=year, product="Renewable hydropower").to_series() / 1000 # from GWh to TWh


def allocate_generation_to_plant(plants, annual_national_generation_twh):
    plants = plants[["country_code", "installed_capacity_MW"]]
    capacity_share = plants.groupby("country_code")["installed_capacity_MW"].transform(lambda x: x / x.sum())
    national_generation = (
        plants.reset_index()
              .merge(annual_national_generation_twh, on="country_code", how="left", validate="many_to_one")
              .set_index("id") # without index reset and set, merge removes the index
              .loc[:, "generation"]
    )
    return capacity_share * national_generation


if __name__ == "__main__":
    main(
        path_to_plants=snakemake.input.plants,
        path_to_units=snakemake.input.units,
        path_to_national_generation=snakemake.input.national_generation,
        year=snakemake.params.year,
        path_to_output=snakemake.output[0]
    )
