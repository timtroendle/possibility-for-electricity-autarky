"""This is a Snakemake file defining rules to retrieve raw data from online sources."""

PYTHON_SCRIPT = "PYTHONPATH=./ python {input} {output}"

URL_LOAD = "https://data.open-power-system-data.org/time_series/2017-07-09/time_series_60min_stacked.csv"
URL_REGIONS = "http://ec.europa.eu/eurostat/cache/GISCO/geodatafiles/NUTS_2013_01M_SH.zip"
URL_LAND_COVER = "http://due.esrin.esa.int/files/Globcover2009_V2.3_Global_.zip"
URL_PROTECTED_AREAS = "https://www.protectedplanet.net/downloads/WDPA_Jan2018?type=shapefile"

REF_EXTENT = "-12 17 42 79"
REF_EXTENT_COMMA = "-12,17,42,79"

rule raw_load:
    output:
        protected("build/raw-load-data.csv")
    shell:
        "curl -Lo {output} '{URL_LOAD}'"


rule electricity_demand_national:
    input:
        "src/process_load.py",
        rules.raw_load.output
    output:
        "build/electricity-demand-national.csv"
    shell:
        PYTHON_SCRIPT


rule raw_regions_zipped:
    output:
        protected("build/raw-regions.zip")
    shell:
        "curl -Lo {output} '{URL_REGIONS}'"


rule raw_regions:
    input: rules.raw_regions_zipped.output
    output: "build/NUTS_2013_01M_SH/data/NUTS_RG_01M_2013.shp"
    shell:
        "unzip {input} -d ./build"


rule raw_land_cover_zipped:
    output: protected("build/raw-globcover2009.zip")
    shell: "curl -Lo {output} '{URL_LAND_COVER}'"


rule raw_land_cover:
    input: rules.raw_land_cover_zipped.output
    output: "build/raw-globcover2009-v2.3/GLOBCOVER_L4_200901_200912_V2.3.tif"
    shell: "unzip {input} -d ./build/raw-globcover2009-v2.3"


rule raw_protected_areas_zipped:
    output: protected("build/raw-wdpa.zip")
    shell: "curl -Lo {output} -H 'Referer: {URL_PROTECTED_AREAS}' {URL_PROTECTED_AREAS}"


rule raw_protected_areas:
    input: rules.raw_protected_areas_zipped.output
    output: "build/WDPA_Oct2017"
    shell: "unzip {input} -d {output}"


rule raw_elevation_data:
    input: "src/download_elevation_data.py"
    output: protected("build/raw-elevation-data.tif")
    shell:
        PYTHON_SCRIPT


rule land_cover_in_europe:
    input: rules.raw_land_cover.output
    output: "build/land-cover-europe.tif"
    shell: "rio clip {input} {output} --bounds {REF_EXTENT}"


rule slope_in_europe:
    input:
        raw_elevation = rules.raw_elevation_data.output,
        land_cover = rules.land_cover_in_europe.output
    output:
        "build/slope-europe.tif"
    shell:
        """
        gdaldem slope -s 111120 -compute_edges {input.raw_elevation} build/slope-temp.tif
        rio warp build/slope-temp.tif -o {output} --like {input.land_cover} --resampling bilinear
        rm build/slope-temp.tif
        """


rule protected_areas_in_europe:
    input:
        raw_protected_areas = rules.raw_protected_areas.output,
        land_cover = rules.land_cover_in_europe.output
    output:
        "build/protected-areas-europe.tif"
    shell:
        # TODO misses the 9% protected areas available as points only. How to incorporate those?
        """
        fio cat --rs --bbox {REF_EXTENT_COMMA} {input.raw_protected_areas} | \
        fio filter "f.properties.STATUS == 'Designated'" | \
        fio collect --record-buffered | \
        rio rasterize --like {input.land_cover} -o build/protected-areas-europe-temp.tif
        rio convert --dtype uint8 build/protected-areas-europe-temp.tif -o {output}
        rm build/protected-areas-europe-temp.tif
        """
