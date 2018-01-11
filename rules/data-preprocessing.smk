"""This is a Snakemake file defining rules to retrieve raw data from online sources."""

PYTHON_SCRIPT = "PYTHONPATH=./ python {input} {output}"

URL_LOAD = "https://data.open-power-system-data.org/time_series/2017-07-09/time_series_60min_stacked.csv"
URL_REGIONS = "http://ec.europa.eu/eurostat/cache/GISCO/geodatafiles/NUTS_2013_01M_SH.zip"
URL_LAND_COVER = "http://due.esrin.esa.int/files/Globcover2009_V2.3_Global_.zip"
URL_PROTECTED_AREAS = "https://www.protectedplanet.net/downloads/WDPA_Jan2018?type=shapefile"
URL_ELEVATION_TILE = "http://droppr.org/srtm/v4.1/6_5x5_TIFs/" # CGIAR

CGIAR_X_MIN = 34 # x coordinate of CGIAR tile raster
CGIAR_X_MAX = 42
CGIAR_Y_MIN = 1 # y coordinate of CGIAR tile raster
CGIAR_Y_MAX = 6

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
        temp("build/electricity-demand-national.csv")
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
    output: "build/raw-wdpa-jan2018/WDPA_Jan2018-shapefile-polygons.shp"
    shell: "unzip {input} -d build/raw-wdpa-jan2018"


rule raw_elevation_tile:
    output:
        tif = temp("build/srtm_{x}_{y}.tif"),
        zip = temp("build/srtm_{x}_{y}.zip")
    shadow: "full"
    shell:
        """
        curl -Lo {output.zip} '{URL_ELEVATION_TILE}/srtm_{wildcards.x}_{wildcards.y}.zip'
        unzip {output.zip} -d build
        """


rule raw_elevation_data:
    input:
        ["build/srtm_{x:02d}_{y:02d}.tif".format(x=x, y=y)
         for x in range(CGIAR_X_MIN, CGIAR_X_MAX + 1)
         for y in range(CGIAR_Y_MIN, CGIAR_Y_MAX + 1)
         if not (x is 34 and y not in [1, 2])] # these tiles do not exist
    output:
        protected("build/raw-elevation-data.tif")
    shell:
        "rio merge {input} {output} --force-overwrite"


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
    benchmark:
        "build/rasterisation-benchmark.txt"
    shell:
        # TODO misses the 9% protected areas available as points only. How to incorporate those?
        """
        fio cat --rs --bbox {REF_EXTENT_COMMA} {input.raw_protected_areas} | \
        fio filter "f.properties.STATUS == 'Designated'" | \
        fio collect --record-buffered | \
        rio rasterize --like {input.land_cover} --default-value 255 -o {output}
        """
