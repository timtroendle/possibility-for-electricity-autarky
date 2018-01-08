PYTHON_SCRIPT = "PYTHONPATH=./ python {input} {output}"

URL_LOAD = "https://data.open-power-system-data.org/time_series/2017-07-09/time_series_60min_stacked.csv"
URL_REGIONS = "http://ec.europa.eu/eurostat/cache/GISCO/geodatafiles/NUTS_2013_01M_SH.zip"

RAW_GRIDDED_POP_DATA = "./data/gpw-v4-population-count-2015/gpw-v4-population-count_2015.tif"
RAW_REGIONS = "build/NUTS_2013_01M_SH/data/NUTS_RG_01M_2013.shp"


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


rule clean: # removes all generated results
    shell:
        "rm -r ./build/*"


rule force_clean: # removes all builds including protected results
    shell:
        "rm -rf ./build/*"


rule test:
    shell:
        "py.test"
