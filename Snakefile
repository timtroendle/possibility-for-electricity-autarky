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


rule population:
    message: "Allocate population to regions of layer {wildcards.layer}."
    input:
        regions = rules.regions.output,
        population = RAW_GRIDDED_POP_DATA
    output:
        "build/{layer}/population.csv"
    shell:
        """
        fio cat {input.regions} | \
        rio zonalstats -r {input.population} --prefix 'population_' --stats sum | \
        python src/geojson_to_csv.py -a id -a population_sum | \
        sed -e 's/None/0.0/g' > {output} # some regions are so small, they contain no pixel
        """


rule demand:
    message: "Allocate electricity demand to regions of layer {wildcards.layer}."
    input:
        "src/spatial_demand.py",
        rules.electricity_demand_national.output,
        rules.industry.output,
        rules.regions.output,
        rules.population.output
    output:
        "build/{layer}/demand.csv"
    shell:
        PYTHON_SCRIPT


rule eez_eligibility:
    message: "Allocate eligible land to exclusive economic zones using {threads} threads."
    input:
        src = "src/regional_eligibility.py",
        regions = rules.eez_in_europe.output,
        eligibility = rules.eligible_land.output
    output:
        "build/eez-eligibility.csv"
    threads: config["snakemake"]["max-threads"]
    shell:
        PYTHON + " {input.src} offshore {input.regions} {input.eligibility} {output} {threads}"


rule regional_land_eligibility:
    message: "Allocate eligible land to regions of layer {wildcards.layer} using {threads} threads."
    input:
        src = "src/regional_eligibility.py",
        regions = rules.regions.output,
        eligibility = rules.eligible_land.output
    output:
        "build/{layer}/land-eligibility.csv"
    threads: config["snakemake"]["max-threads"]
    shell:
        PYTHON + " {input.src} land {input.regions} {input.eligibility} {output} {threads}"


rule shared_coast:
    message: "Determine share of coast length between eez and regions of layer {wildcards.layer} using {threads} threads."
    input:
        "src/shared_coast.py",
        rules.regions.output,
        rules.eez_in_europe.output
    output:
        "build/{layer}/shared-coast.csv"
    threads: config["snakemake"]["max-threads"]
    shell:
        PYTHON_SCRIPT + " {threads}"


rule regional_offshore_eligibility:
    message: "Allocate eez eligibilities to regions of layer {wildcards.layer}."
    input:
        "src/allocate_eez.py",
        rules.eez_eligibility.output,
        rules.shared_coast.output
    output:
        "build/{layer}/offshore-eligibility.csv"
    shell:
        PYTHON_SCRIPT


rule regional_eligibility_rooftop_correction:
    message: "Determine share of roof top area in each region of layer {wildcards.layer}."
    input:
        "src/rooftop_correction.py",
        rules.rooftop_area.output,
        rules.eligible_land.output,
        rules.regions.output,
        rules.regional_land_eligibility.output
    output:
        "build/{layer}/land-eligibility-rooftop-corrected.csv"
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
        rules.regions.output,
        rules.population.output,
        rules.demand.output,
        rules.regional_eligibility_rooftop_correction.output,
        rules.regional_offshore_eligibility.output,
        rules.renewable_capacity_factors.output
    output:
        "build/{layer}/result.geojson"
    shell:
        # TODO this approach leads to up to 866 m^2 roof area per citizen -- way too much
        PYTHON_SCRIPT + " {CONFIG_FILE}"


rule necessary_land_plots:
    message: "Plot fraction of land necessary."
    input:
        "src/vis/necessary_land.py",
        expand("build/{layer}/result.geojson", layer=config["layers"].keys()),
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
        "build/national/result.geojson",
        rules.renewable_capacity_factors.output
    output:
        "build/potentials.png"
    shell:
        PYTHON_SCRIPT + " {CONFIG_FILE}"


rule kassel_plot:
    message: "Plot the map of land necessary for Germany and point to Kassel."
    input:
        "src/vis/kassel.py",
        "build/municipal/result.geojson",
        "build/national/regions.geojson"
    output:
        "build/kassel-map.png"
    shell:
        PYTHON_SCRIPT


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
