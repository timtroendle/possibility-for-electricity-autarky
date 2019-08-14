"""Rules to generate data that is used for the online map."""

WEB_MERCATOR = "+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0 +k=1.0 "\
               "+units=m +nadgrids=@null +wktext  +no_defs"

localrules: export_map_data


rule export_map_data:
    message: "Export everything."
    input:
        "build/export/map/national-boundaries-national-level.shp",
        "build/export/map/national-boundaries-regional-level.shp",
        "build/export/map/national-boundaries-municipal-level.shp",
        "build/export/map/continental--technical-social-potential.mbtiles",
        "build/export/map/national--technical-social-potential.mbtiles",
        "build/export/map/regional--technical-social-potential.mbtiles",
        "build/export/map/municipal--technical-social-potential.mbtiles",


rule national_boundaries:
    message: "Export national boundaries on {wildcards.layer} level."
    input: "build/{layer}/units.geojson"
    output: "build/export/map/national-boundaries-{layer}-level.shp"
    run:
        import geopandas as gpd

        units = gpd.read_file(input[0])[["country_code", "geometry"]]
        units.dissolve(by="country_code").geometry.to_crs(WEB_MERCATOR).to_file(output[0])


rule scenario_result:
    message: "Export data of {wildcards.layer} layer together with our rating of possibility."
    input:
        technical_potential = "build/{layer}/technical-potential/merged-results.gpkg",
        technical_social_potential = "build/{layer}/technical-social-potential/merged-results.gpkg",
    output: "build/export/map/{layer}--technical-social-potential.geojson"
    run:
        import pandas as pd
        import geopandas as gpd

        technical_potential = (gpd
                               .read_file(input.technical_potential)
                               .rename(columns={"id": "unit_id"})
                               .set_index("unit_id"))
        technical_social_potential = (gpd
                                      .read_file(input.technical_social_potential)
                                      .rename(columns={"id": "unit_id"})
                                      .set_index("unit_id"))

        def our_rating(technical_potential, technical_social_potential):
            rating = pd.Series(index=technical_social_potential.index, data=None, dtype=pd.np.object)
            rating[technical_social_potential >= 1] = "is likely possible"
            rating[(technical_social_potential < 1)
                   & (technical_potential >= 2)] = "is maybe possible"
            rating[(technical_social_potential < 1)
                   & (technical_potential < 2)
                   & (technical_potential >= 1)] = "is likely impossible"
            rating[technical_potential < 1] = "is impossible"
            return rating

        technical_social_potential["our_rating"] = our_rating(
            technical_potential=technical_potential["normed_potential"],
            technical_social_potential=technical_social_potential["normed_potential"]
        )
        technical_social_potential["total_potential_twh_per_year"] = (
            technical_social_potential["offshore_wind_twh_per_year"]
            + technical_social_potential["onshore_wind_twh_per_year"]
            + technical_social_potential["rooftop_pv_twh_per_year"]
            + technical_social_potential["open_field_pv_twh_per_year"]
        )
        technical_social_potential.to_file(output[0], driver="GeoJSON")


def zoom_range_parameters(wildcards):
    filename = wildcards.filename
    if "continental" in filename:
        return "-z4"
    elif "national" in filename:
        return "-Z3 -z6"
    elif "regional" in filename:
        return "-Z6 -z9"
    elif "municipal" in filename:
        return "-Z9 -z12"
    else:
        return "-zg" # determine automatically


rule tiles:
    message: "Create tiles from '{wildcards.filename}.geojson'."
    input: "build/export/map/{filename}.geojson"
    params: zoom_range = zoom_range_parameters
    output: "build/export/map/{filename}.mbtiles"
    conda: "../envs/webmap.yaml"
    shell: "tippecanoe -o {output} {params.zoom_range} --generate-ids {input}"
