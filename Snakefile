PYTHON = "PYTHONPATH=./ python"
PYTHON_SCRIPT = "PYTHONPATH=./ python {input} {output}"

RAW_GRIDDED_POP_DATA = "data/gpw-v4-population-count-2020/gpw-v4-population-count_2020.tif"
CONFIG_FILE = "config/default.yaml"

configfile: CONFIG_FILE
include: "rules/data-preprocessing.smk"


rule all:
    message: "Run entire analysis and compile report."
    input: "build/paper.pdf"


rule eligible_land:
    message:
        "Determine land eligibility for renewables based on land cover, slope, bathymetry, and protected areas."
    input:
        "src/eligible_land.py",
        rules.land_cover_in_europe.output,
        rules.protected_areas_in_europe.output,
        rules.slope_in_europe.output,
        rules.bathymetry_in_europe.output
    output:
        "build/eligible-land.tif"
    shell:
        PYTHON_SCRIPT


rule regions:
    message: "Form regions of layer {wildcards.layer} by remixing NUTS, LAU, and GADM."
    input:
        "src/regions.py",
        rules.administrative_borders_nuts.output,
        rules.administrative_borders_lau.output,
        rules.administrative_borders_gadm.output
    output:
        "build/{layer}/regions.geojson"
    shell:
        PYTHON_SCRIPT + " {wildcards.layer} {CONFIG_FILE}"


rule regions_with_population:
    message: "Allocate population to regions of layer {wildcards.layer}."
    input:
        regions = rules.regions.output,
        population = RAW_GRIDDED_POP_DATA
    output:
        temp("build/{layer}/regions-population.geojson")
    shell:
        """
        fio cat {input.regions} | \
        rio zonalstats -r {input.population} --prefix 'population_' --stats sum > {output}
        """


rule regions_with_population_and_demand:
    message: "Allocate electricity demand to regions of layer {wildcards.layer}."
    input:
        "src/spatial_demand.py",
        rules.electricity_demand_national.output,
        rules.industry.output,
        rules.regions_with_population.output
    output:
        temp("build/{layer}/regions-population-demand.geojson")
    shell:
        PYTHON_SCRIPT


rule eez_eligibility:
    message: "Allocate eligible land to exclusive economic zones using {threads} threads."
    input:
        src = "src/regional_eligibility.py",
        regions = rules.eez_in_europe.output,
        eligibility = rules.eligible_land.output
    output:
        "build/eez-eligibility.geojson"
    threads: config["snakemake"]["max-threads"]
    shell:
        PYTHON + " {input.src} offshore {input.regions} {input.eligibility} {output} {threads}"


rule regional_land_eligibility:
    message: "Allocate eligible land to regions of layer {wildcards.layer} using {threads} threads."
    input:
        src = "src/regional_eligibility.py",
        regions = rules.regions_with_population_and_demand.output,
        eligibility = rules.eligible_land.output
    output:
        "build/{layer}/regional-land-eligibility.geojson"
    threads: config["snakemake"]["max-threads"]
    shell:
        PYTHON + " {input.src} land {input.regions} {input.eligibility} {output} {threads}"


rule regional_eligibility:
    message: "Allocate eez and their eligibilities to regions of layer {wildcards.layer} using {threads} threads."
    input:
        "src/allocate_eez.py",
        rules.regional_land_eligibility.output,
        rules.eez_eligibility.output
    output:
        "build/{layer}/regional-eligibility.geojson"
    threads: config["snakemake"]["max-threads"]
    shell:
        PYTHON_SCRIPT + " {threads}"


rule regional_eligibility_rooftop_correction:
    message: "Determine share of roof top area in each region of layer {wildcards.layer}."
    input:
        "src/rooftop_correction.py",
        rules.rooftop_area.output,
        rules.eligible_land.output,
        rules.regional_eligibility.output
    output:
        "build/{layer}/regional-eligibility-rooftop-corrected.geojson"
    shell:
        PYTHON_SCRIPT


rule renewable_capacity_factors:
    message: "Merge all renewable capacity factors and replace missing."
    input:
        "src/renewable_capacity_factors.py",
        rules.raw_wind_capacity_factors.output,
        rules.raw_pv_capacity_factors.output
    output:
        "build/national-capacity-factors.csv"
    shell:
        PYTHON_SCRIPT + " {CONFIG_FILE}"


rule necessary_land:
    message: "Determine fraction of land necessary to supply demand per region of layer {wildcards.layer}."
    input:
        "src/necessary_land.py",
        rules.regional_eligibility_rooftop_correction.output,
        rules.renewable_capacity_factors.output
    output:
        "build/{layer}/necessary-land.geojson"
    shell:
        # TODO this approach leads to up to 866 m^2 roof area per citizen -- way too much
        PYTHON_SCRIPT + " {CONFIG_FILE}"


rule necessary_land_plots:
    message: "Plot fraction of land necessary."
    input:
        "src/vis/necessary_land.py",
        expand("build/{layer}/necessary-land.geojson", layer=config["layers"].keys()),
        "build/national/regions.geojson"
    output:
        "build/necessary-land-boxplots.png",
        "build/necessary-land-map.png",
        "build/necessary-land-correlations.png"
    shell:
        PYTHON_SCRIPT


rule potential_plot:
    message: "Plot potentials of renewable power."
    input:
        "src/vis/potentials.py",
        "build/national/regional-eligibility-rooftop-corrected.geojson",
        rules.renewable_capacity_factors.output
    output:
        "build/potentials.png"
    shell:
        PYTHON_SCRIPT + " {CONFIG_FILE}"


rule paper:
    message: "Compile report."
    input:
        "report/literature.bib",
        "report/main.md",
        "report/pandoc-metadata.yml",
        rules.necessary_land_plots.output,
        rules.potential_plot.output
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
        """
        rm -r ./build/*
        echo "Data downloaded to data/ has not been cleaned."
        """


rule test:
    shell:
        "py.test"
