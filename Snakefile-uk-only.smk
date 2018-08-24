PYTHON = "PYTHONPATH=./ python"
PANDOC = "pandoc --filter pantable --filter pandoc-fignos --filter pandoc-tablenos --filter pandoc-citeproc"
PYTHON_SCRIPT = "PYTHONPATH=./ python {input} {output}"

include: "Snakefile"

URL_SHAPES = "https://github.com/sjpfenninger/uk-calliope/raw/master/zones.zip"


rule uk_units:
    message: "Create units for UK."
    output:
        "build/uk-only/units.geojson"
    shadow: "full"
    run:
        import geopandas as gpd

        shell("curl -sLo build/uk-shapes.zip '{URL_SHAPES}'")
        shell("unzip build/uk-shapes.zip -d ./build")

        units = gpd.read_file("./build/shapefile/zones.shp")
        units["country_code"] = "GBR"
        units["id"] = units["Name_1"]
        units["name"] = units["Name_1"]
        units["type"] = "grid_zone"
        units["proper"] = 1

        units.to_file(output[0], driver="GeoJSON")


rule uk_only:
    message: "Determine potential for UK only."
    input:
        rules.uk_units.output,
        "build/uk-only/technical-potential/merged-results.geojson",
        "build/uk-only/technical-social-potential/merged-results.geojson"
