"""Rules to generate data that is used for the online map."""

WEB_MERCATOR = "+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0 +k=1.0 "\
               "+units=m +nadgrids=@null +wktext  +no_defs"

localrules: export_for_map, scenario_result


rule export_map_data:
    message: "Export everything."
    input:
        "build/export/map/national-boundaries-national-level.shp",
        "build/export/map/national-boundaries-regional-level.shp",
        "build/export/map/national-boundaries-municipal-level.shp",
        "build/export/map/continental--technical-potential.geojson",
        "build/export/map/national--technical-potential.geojson",
        "build/export/map/regional--technical-potential.geojson",
        "build/export/map/municipal--technical-potential.geojson",


rule national_boundaries:
    message: "Export national boundaries on {wildcards.layer} level."
    input: "build/{layer}/units.geojson"
    output: "build/export/map/national-boundaries-{layer}-level.shp"
    run:
        import geopandas as gpd

        units = gpd.read_file(input[0])[["country_code", "geometry"]]
        units.dissolve(by="country_code").geometry.to_crs(WEB_MERCATOR).to_file(output[0])


rule scenario_result:
    message: "Copy merged result of scenario {wildcards.scenario} of {wildcards.layer} layer."
    input: "build/{layer}/{scenario}/merged-results.geojson"
    output: "build/export/map/{layer}--{scenario}.geojson"
    shell: "cp {input} {output}"
