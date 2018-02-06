PYTHON_SCRIPT = "PYTHONPATH=./ python {input} {output}"

RAW_GRIDDED_POP_DATA = "data/gpw-v4-population-count-2015/gpw-v4-population-count_2015.tif"

configfile: "config/snakemake.yaml"
include: "rules/data-preprocessing.smk"

rule all:
    message: "Run entire analysis and compile report."
    input: "build/paper.pdf"


rule available_land:
    message:
        "Determine land available for renewables based on land cover, slope, and protected areas."
    input:
        "src/available_land.py",
        rules.land_cover_in_europe.output,
        rules.protected_areas_in_europe.output,
        rules.slope_in_europe.output
    output:
        "build/available-land.tif"
    shell:
        PYTHON_SCRIPT


rule regions_with_population:
    message: "Allocate population to regions."
    input:
        regions = rules.raw_regions.output,
        population = RAW_GRIDDED_POP_DATA
    output:
        temp("build/regions_population.geojson")
    shell:
        "fio cat {input.regions} | rio zonalstats -r {input.population} --prefix 'population_' --stats sum > {output}"


rule regions_with_population_and_demand:
    message: "Allocate electricity demand to regions."
    input:
        "src/spatial_demand.py",
        rules.electricity_demand_national.output,
        rules.regions_with_population.output
    output:
        "build/regions_population_demand.geojson"
    shell:
        PYTHON_SCRIPT


rule regions:
    message: "Allocate available land to regions."
    input:
        regions = rules.regions_with_population_and_demand.output,
        available_land = rules.available_land.output
    output:
        "build/regions.geojson"
    shell:
        "fio cat {input.regions} | rio zonalstats -r {input.available_land} --categorical --prefix availability > {output}"


rule necessary_land:
    message: "Determine fraction of land necessary to supply demand per region."
    input:
        "src/necessary_land.py",
        rules.regions.output
    output:
        "build/necessary-land.geojson"
    shell:
        # TODO this approach leads to up to 866 m^2 roof area per citizen -- way too much
        PYTHON_SCRIPT


rule necessary_land_plots:
    message: "Plot fraction of land necessary."
    input:
        "src/vis/necessary_land.py",
        rules.necessary_land.output
    output:
        "build/necessary-land-boxplots.png",
        "build/necessary-land-map.png"
    shell:
        PYTHON_SCRIPT


rule paper:
    message: "Compile report."
    input:
        "report/literature.bib",
        "report/main.md",
        "report/pandoc-metadata.yml",
        rules.necessary_land_plots.output
    output:
        "build/paper.pdf"
    shell:
        """
        cd ./report
        pandoc --filter pantable --filter pandoc-fignos --filter pandoc-tablenos \
        --filter pandoc-citeproc main.md pandoc-metadata.yml -t latex -o ../build/paper.pdf
        """


rule clean: # removes all generated results
    shell:
        "rm -r ./build/*"


rule force_clean: # removes all builds including protected results
    shell:
        "rm -rf ./build/*"


rule test:
    shell:
        "py.test"
