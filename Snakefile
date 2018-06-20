PYTHON = "PYTHONPATH=./ python"
PYTHON_SCRIPT = "PYTHONPATH=./ python {input} {output}"

CONFIG_FILE = "config/default.yaml"

configfile: CONFIG_FILE
include: "rules/data-preprocessing.smk"


rule all:
    message: "Run entire analysis and compile report."
    input: "build/report.pdf"


rule eligible_land:
    message:
        "Determine land eligibility for renewables based on land cover, slope, bathymetry, buildings, "
        "and protected areas for scenario {wildcards.scenario}."
    input:
        "src/eligible_land.py",
        rules.land_cover_in_europe.output,
        rules.protected_areas_in_europe.output,
        rules.slope_in_europe.output,
        rules.bathymetry_in_europe.output,
        rules.settlements.output
    output:
        "build/{scenario}/eligible-land.tif"
    shell:
        PYTHON_SCRIPT + " {wildcards.scenario} {CONFIG_FILE}"


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


rule regional_land_cover:
    message: "Land cover statistics per region of layer {wildcards.layer}."
    input:
        regions = rules.regions.output,
        land_cover = rules.land_cover_in_europe.output,
        src = "src/geojson_to_csv.py"
    output:
        "build/{layer}/land-cover.csv"
    shell:
        """
        fio cat {input.regions} | \
        rio zonalstats -r {input.land_cover} --prefix 'lc_' --categorical | \
        {PYTHON} {input.src} -a id -a lc_11 -a lc_14 -a lc_20 -a lc_30 -a lc_40 \
        -a lc_50 -a lc_60 -a lc_70 -a lc_90 -a lc_100 -a lc_110 -a lc_120 -a lc_130 \
        -a lc_140 -a lc_150 -a lc_160 -a lc_170 -a lc_180 -a lc_190 -a lc_200 \
        -a lc_210 -a lc_220 -a lc_230 > \
        {output}
        """


rule regional_protected_areas:
    message: "Protected area statistics per region of layer {wildcards.layer}."
    input:
        regions = rules.regions.output,
        protected_areas = rules.protected_areas_in_europe.output,
        src = "src/geojson_to_csv.py"
    output:
        "build/{layer}/protected-areas.csv"
    shell:
        """
        fio cat {input.regions} | \
        rio zonalstats -r {input.protected_areas} --prefix 'pa_' --categorical --nodata -1 | \
        {PYTHON} {input.src} -a id -a pa_0 -a pa_255 > \
        {output}
        """


rule population:
    message: "Allocate population to regions of layer {wildcards.layer}."
    input:
        regions = rules.regions.output,
        population = rules.population_in_europe.output,
        src_geojson = "src/geojson_to_csv.py",
        src_population = "src/population.py",
        land_cover = rules.regional_land_cover.output
    output:
        "build/{layer}/population.csv"
    shell:
        """
        crs=$(rio info --crs {input.population})
        fio cat --dst_crs "$crs" {input.regions} | \
        rio zonalstats -r {input.population} --prefix 'population_' --stats sum | \
        {PYTHON} {input.src_geojson} -a id -a population_sum -a proper | \
        {PYTHON} {input.src_population} {input.land_cover} > \
        {output}
        """


rule population_in_protected_areas:
    message: "Determine the population that lives in protected areas using {threads} threads."
    input:
        population = rules.population_in_europe.output,
        protected_areas = rules.protected_areas_in_europe.output,
        regions = "build/national/regions.geojson"
    output:
        "build/population-in-protected-areas.tif",
    threads: config["snakemake"]["max-threads"]
    shadow: "full"
    shell:
        """
        rio warp {input.population} -o warped_pop_europe.tif \
        --like {input.protected_areas} --threads {threads} --resampling bilinear
        rio calc "(* (== (read 1) 255) (read 2))" {input.protected_areas} warped_pop_europe.tif {output}
        rio mask {output} {output} --crop --geojson-mask {input.regions} --force-overwrite
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
    message:
        "Allocate eligible land to exclusive economic zones for scenario {wildcards.scenario} using {threads} threads."
    input:
        src = "src/regional_eligibility.py",
        regions = rules.eez_in_europe.output,
        eligibility = rules.eligible_land.output
    output:
        "build/{scenario}/eez-eligibility.csv"
    threads: config["snakemake"]["max-threads"]
    shell:
        PYTHON + " {input.src} offshore {input.regions} {input.eligibility} {output} {threads}"


rule regional_land_eligibility:
    message:
        "Allocate eligible land to regions for scenario {wildcards.scenario} of layer {wildcards.layer} "
        "using {threads} threads."
    input:
        src = "src/regional_eligibility.py",
        regions = rules.regions.output,
        eligibility = rules.eligible_land.output
    output:
        "build/{layer}/{scenario}/land-eligibility.csv"
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
    message: "Allocate eez eligibilities to regions for scenario {wildcards.scenario} of layer {wildcards.layer}."
    input:
        "src/allocate_eez.py",
        rules.eez_eligibility.output,
        rules.shared_coast.output
    output:
        "build/{layer}/{scenario}/offshore-eligibility.csv"
    shell:
        PYTHON_SCRIPT


rule regional_eligibility_rooftop_pv:
    message:
        "Determine rooftop pv potential in each region for scenario {wildcards.scenario} of layer {wildcards.layer}."
    input:
        "src/rooftop.py",
        rules.settlements.output.buildings,
        rules.eligible_land.output,
        rules.regions.output,
        rules.regional_land_eligibility.output
    output:
        "build/{layer}/{scenario}/land-eligibility-with-rooftop-pv.csv"
    shell:
        PYTHON_SCRIPT + " {CONFIG_FILE}"


rule regional_eligibility:
    message: "Merge land and offshore eligibility for layer {wildcards.layer} and scenario {wildcards.scenario}."
    input:
        land = rules.regional_eligibility_rooftop_pv.output,
        offshore = rules.regional_offshore_eligibility.output
    output:
        "build/{layer}/{scenario}/regional-eligibility.csv"
    run:
        import pandas as pd

        all = pd.concat(
            [pd.read_csv(path).set_index("id") for path in [input.land[0], input.offshore[0]]],
            axis=1
        )
        all.index.name = "id"
        all.to_csv(output[0], header=True)


rule rooftop_area_per_capita:
    message: "Determine the rooftop area per capita."
    input:
        population = "build/national/population.csv",
        eligibility = "build/national/{scenario}/land-eligibility-with-rooftop-pv.csv"
    output:
        "build/national/{scenario}/rooftop-area-per-capita.csv"
    run:
        import pandas as pd
        population = pd.read_csv(input.population, index_col=0)["population_sum"]
        eligibility_m2 = pd.read_csv(input.eligibility, index_col=0)["eligibility_rooftop_pv_km2"] * 1e6

        per_capita = eligibility_m2 / population
        per_capita.name = "rooftop_pv_m2_per_capita"
        per_capita.to_csv(output[0], float_format="%.2f")


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


rule regional_capacity_factors:
    message: "Determine capacity factors for regions of layer {wildcards.layer}."
    input:
        regions = rules.regions.output,
        national_capacity_factors = rules.renewable_capacity_factors.output
    output:
        "build/{layer}/capacity-factors.csv"
    run:
        import geopandas as gpd
        import pandas as pd

        regions = gpd.read_file(input.regions[0]).set_index("id")
        national_cps = pd.read_csv(input.national_capacity_factors[0], index_col=0)
        national_cps = national_cps.reindex(regions.set_index("country_code").index)
        national_cps.index = regions.index
        national_cps.to_csv(output[0], header=True)


rule necessary_land:
    message:
        "Determine fraction of land necessary to supply demand per region for scenario {wildcards.scenario} "
        "of layer {wildcards.layer}."
    input:
        "src/necessary_land.py",
        rules.population.output,
        rules.demand.output,
        rules.regional_eligibility.output,
        rules.regional_capacity_factors.output
    output:
        "build/{layer}/{scenario}/necessary-land.csv"
    shell:
        PYTHON_SCRIPT + " {CONFIG_FILE}"


rule necessary_land_plots:
    message: "Plot fraction of land necessary for scenario {wildcards.scenario}."
    input:
        src = "src/vis/necessary_land.py",
        national_regions = "build/national/regions.geojson",
        subnational_regions = "build/subnational/regions.geojson",
        municipal_regions = "build/municipal/regions.geojson",
        national_necessary_land = "build/national/{scenario}/necessary-land.csv",
        subnational_necessary_land = "build/subnational/{scenario}/necessary-land.csv",
        municipal_necessary_land = "build/municipal/{scenario}/necessary-land.csv",
        national_land_cover = "build/national/land-cover.csv",
        subnational_land_cover = "build/subnational/land-cover.csv",
        municipal_land_cover = "build/municipal/land-cover.csv",
        national_protected_areas = "build/national/protected-areas.csv",
        subnational_protected_areas = "build/subnational/protected-areas.csv",
        municipal_protected_areas = "build/municipal/protected-areas.csv",
        national_population = "build/national/population.csv",
        subnational_population = "build/subnational/population.csv",
        municipal_population = "build/municipal/population.csv",
        national_demand = "build/national/demand.csv",
        subnational_demand = "build/subnational/demand.csv",
        municipal_demand = "build/municipal/demand.csv",
        worldwide_countries = rules.country_shapes.output
    output:
        "build/{scenario}/necessary-land-boxplots.png",
        "build/{scenario}/necessary-land-map.png",
        "build/{scenario}/necessary-land-correlations.png"
    shell:
        PYTHON + " {input.src} "
                 "{input.national_regions},{input.national_necessary_land},{input.national_population},{input.national_land_cover},{input.national_protected_areas},{input.national_demand} "
                 "{input.subnational_regions},{input.subnational_necessary_land},{input.subnational_population},{input.subnational_land_cover},{input.subnational_protected_areas},{input.subnational_demand} "
                 "{input.municipal_regions},{input.municipal_necessary_land},{input.municipal_population},{input.municipal_land_cover},{input.municipal_protected_areas},{input.municipal_demand} "
                 "{input.national_regions} "
                 "{input.worldwide_countries} "
                 "{output}"


rule potential_plot:
    message: "Plot potentials of renewable power for scenario {wildcards.scenario}."
    input:
        "src/vis/potentials.py",
        "build/national/regions.geojson",
        "build/national/demand.csv",
        "build/national/{scenario}/land-eligibility-with-rooftop-pv.csv",
        "build/national/{scenario}/offshore-eligibility.csv",
        rules.renewable_capacity_factors.output
    output:
        "build/{scenario}/potentials.png"
    shell:
        PYTHON_SCRIPT + " {CONFIG_FILE}"


rule solution_matrix_plot:
    message: "Plot the solution matrix showing pathways to reach 100% sufficent power supply."
    input:
        "src/vis/solution.py",
        "build/municipal/demand.csv",
        "build/municipal/capacity-factors.csv",
        "build/municipal/population.csv",
        "build/municipal/full-protection/regional-eligibility.csv",
        "build/municipal/zero-protection/regional-eligibility.csv",
    output:
        "build/solution-matrix.png"
    shell:
        PYTHON_SCRIPT + " {CONFIG_FILE}"


rule kassel_plot:
    message: "Plot the map of land necessary for Germany and point to Kassel for scenario {wildcards.scenario}."
    input:
        "src/vis/kassel.py",
        "build/municipal/regions.geojson",
        "build/municipal/{scenario}/necessary-land.csv",
        "build/national/regions.geojson"
    output:
        "build/{scenario}/kassel-map.png"
    shell:
        PYTHON_SCRIPT


rule report:
    message: "Compile report."
    input:
        "report/literature.bib",
        "report/main.md",
        "report/pandoc-metadata.yml",
        expand("build/{scenario}/necessary-land-map.png", scenario=config["scenarios"].keys()),
        expand("build/{scenario}/potentials.png", scenario=config["scenarios"].keys()),
        rules.solution_matrix_plot.output
    output:
        "build/report.pdf"
    shell:
        """
        cd ./report
        pandoc --filter pantable --filter pandoc-fignos --filter pandoc-tablenos \
        --filter pandoc-citeproc main.md pandoc-metadata.yml -t latex -o ../build/report.pdf
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
