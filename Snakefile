PYTHON_SCRIPT = "PYTHONPATH=./ python {input} {output}"

URL_LOAD = "https://data.open-power-system-data.org/time_series/2017-07-09/time_series_60min_stacked.csv"
URL_REGIONS = "http://ec.europa.eu/eurostat/cache/GISCO/geodatafiles/NUTS_2013_01M_SH.zip"
URL_LAND_COVER = "http://due.esrin.esa.int/files/Globcover2009_V2.3_Global_.zip"
URL_PROTECTED_AREAS = "https://www.protectedplanet.net/downloads/WDPA_Jan2018?type=shapefile"

RAW_GRIDDED_POP_DATA = "data/gpw-v4-population-count-2015/gpw-v4-population-count_2015.tif"
RAW_REGIONS = "build/NUTS_2013_01M_SH/data/NUTS_RG_01M_2013.shp"
RAW_LAND_COVER_DATA = "build/Globcover2009_V2.3_Global_/GLOBCOVER_L4_200901_200912_V2.3.tif"

REF_EXTENT = "-12 17 42 79"
REF_EXTENT_COMMA = "-12,17,42,79"

rule paper:
    input:
        "build/necessary-land-boxplots.png",
        "build/necessary-land-map.png",
        "report/literature.bib",
        "report/main.md",
        "report/pandoc-metadata.yml"
    output:
        "build/paper.pdf"
    shell:
        "cd ./report && \
        pandoc --filter pantable --filter pandoc-fignos --filter pandoc-tablenos \
        --filter pandoc-citeproc main.md pandoc-metadata.yml -t latex -o ../build/paper.pdf"


rule raw_load:
    output:
        protected("build/raw-load-data.csv")
    shell:
        "curl -Lo {output} '{URL_LOAD}'"


rule raw_regions_zipped:
    output:
        protected("build/raw-regions.zip")
    shell:
        "curl -Lo {output} '{URL_REGIONS}'"


rule raw_regions:
    input: rules.raw_regions_zipped.output
    output: RAW_REGIONS
    shell:
        "unzip {input} -d ./build"


rule electricity_demand_national:
    input:
        "src/process_load.py",
        rules.raw_load.output
    output:
        "build/electricity-demand-national.csv"
    shell:
        PYTHON_SCRIPT


rule population_per_region:
    input:
        regions = RAW_REGIONS,
        population = RAW_GRIDDED_POP_DATA
    output:
        "build/regions_population.geojson"
    shell:
        "fio cat {input.regions} | rio zonalstats -r {input.population} --prefix 'population_' --stats sum > {output}"


rule regional_upsampling_demand:
    input:
        "src/spatial_demand.py",
        rules.electricity_demand_national.output,
        rules.population_per_region.output
    output:
        "build/regions_population_demand.geojson"
    shell:
        PYTHON_SCRIPT


rule raw_land_cover_zipped:
    output: protected("build/Globcover2009.zip")
    shell: "curl -Lo {output} '{URL_LAND_COVER}'"


rule raw_land_cover:
    input: rules.raw_land_cover_zipped.output
    output: "build/Globcover2009_V2.3_Global_"
    shell: "unzip {input} -d {output}"


rule raw_protected_areas_zipped:
    output: protected("build/wdpa.zip")
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


rule land_cover_europe:
    input: RAW_LAND_COVER_DATA
    output: "build/land-cover-europe.tif"
    shell: "rio clip {input} {output} --bounds {REF_EXTENT}"


rule slope_in_europe:
    input:
        raw_elevation = rules.raw_elevation_data.output,
        land_cover = rules.land_cover_europe.output
    output:
        "build/slope-europe.tif"
    shell:
        """
        gdaldem slope -s 111120 -compute_edges {input.raw_elevation} build/slope-temp.tif
        rio warp build/slope-temp.tif -o {output} --like {input.land_cover} --resampling bilinear
        rm build/slope-temp.tif
        """


rule protected_areas_europe:
    input:
        raw_protected_areas = rules.raw_protected_areas.output,
        land_cover = rules.land_cover_europe.output
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


rule available_land:
    input:
        "src/available_land.py",
        rules.land_cover_europe.output,
        rules.protected_areas_europe.output,
        rules.slope_in_europe.output
    output:
        "build/available-land.tif"
    shell:
        PYTHON_SCRIPT


rule clean: # removes all generated results
    shell:
        "rm -r ./build/*"


rule force_clean: # removes all builds including protected results
    shell:
        "rm -rf ./build/*"


rule test:
    shell:
        "py.test"
