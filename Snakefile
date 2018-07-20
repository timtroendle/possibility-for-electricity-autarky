PYTHON = "PYTHONPATH=./ python"
PANDOC = "pandoc --filter pantable --filter pandoc-fignos --filter pandoc-tablenos --filter pandoc-citeproc"
PYTHON_SCRIPT = "PYTHONPATH=./ python {input} {output}"

CONFIG_FILE = "config/default.yaml"

configfile: CONFIG_FILE
include: "rules/data-preprocessing.smk"
include: "rules/sonnendach.smk"


rule all:
    message: "Run entire analysis and compile report."
    input:
        "build/report.pdf",
        "build/paper.pdf",
        "build/scenario-overview.csv"


rule eligible_land:
    message:
        "Determine land eligibility for renewables based on land cover, slope, bathymetry, settlements, "
        "and protected areas."
    input:
        "src/eligible_land.py",
        rules.land_cover_in_europe.output,
        rules.protected_areas_in_europe.output,
        rules.slope_in_europe.output,
        rules.bathymetry_in_europe.output,
        rules.settlements.output
    output:
        "build/eligible-land.tif"
    shell:
        PYTHON_SCRIPT + " {CONFIG_FILE}"


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


rule regional_slope:
    message: "Slope statistics per region of layer {wildcards.layer}."
    input:
        regions = rules.regions.output,
        slope = rules.slope_in_europe.output,
        src = "src/geojson_to_csv.py"
    output:
        "build/{layer}/slope.csv"
    shell:
        """
        fio cat {input.regions} | \
        rio zonalstats -r {input.slope} --stats "min max median percentile_25 percentile_75" | \
        {PYTHON} {input.src} -a id -a _min -a _max -a _median -a _percentile_25 -a _percentile_75 |
        sed -e 's/None/NaN/g' > \
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
        {PYTHON} {input.src_population} {input.regions} {input.land_cover} > \
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
        "Allocate eligible land to exclusive economic zones using {threads} threads."
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
    message:
        "Allocate eligible land to regions of layer {wildcards.layer} using {threads} threads."
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


rule regional_eligibility_rooftop_pv:
    message:
        "Determine rooftop pv potential in each region of layer {wildcards.layer}."
    input:
        "src/rooftop.py",
        rules.settlements.output.buildings,
        rules.eligible_land.output,
        rules.regions.output,
        rules.regional_land_eligibility.output,
        rules.ratio_esm_estimation_available.output
    output:
        "build/{layer}/land-eligibility-with-rooftop-pv.csv"
    shell:
        PYTHON_SCRIPT + " {CONFIG_FILE}"


rule regional_eligibility:
    message: "Merge land and offshore eligibility for layer {wildcards.layer}."
    input:
        land = rules.regional_eligibility_rooftop_pv.output,
        offshore = rules.regional_offshore_eligibility.output
    output:
        "build/{layer}/regional-eligibility.csv"
    run:
        import pandas as pd

        all = pd.concat(
            [pd.read_csv(path).set_index("id") for path in [input.land[0], input.offshore[0]]],
            axis=1,
            sort=True
        )
        all.index.name = "id"
        all.to_csv(output[0], header=True)


rule rooftop_area_per_capita:
    message: "Determine the rooftop area per capita."
    input:
        population = "build/national/population.csv",
        eligibility = "build/national/land-eligibility-with-rooftop-pv.csv"
    output:
        "build/national/rooftop-area-per-capita.csv"
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


rule unconstrained_potentials:
    message:
        "Determine the unconstrained renewable potentials for all eligibility types of layer {wildcards.layer}."
    input:
        "src/potentials_unconstrained.py",
        rules.regional_eligibility.output,
        rules.regional_capacity_factors.output,
        rules.sonnendach_statistics.output.raw
    output:
        prefer_pv = "build/{layer}/unconstrained-potentials-prefer-pv.csv",
        prefer_wind = "build/{layer}/unconstrained-potentials-prefer-wind.csv"
    shell:
        PYTHON_SCRIPT + " {CONFIG_FILE}"


rule constrained_potentials:
    message:
        "Determine constrained potentials for layer {wildcards.layer} in scenario {wildcards.scenario}."
    input:
        "src/potentials_constrained.py",
        rules.unconstrained_potentials.output
    output:
        "build/{layer}/{scenario}/constrained-potentials.csv"
    shell:
        PYTHON_SCRIPT + " {wildcards.scenario} {CONFIG_FILE}"


rule normed_potentials:
    message:
        "Determine potentials relative to demand for layer {wildcards.layer} "
        "in scenario {wildcards.scenario}."
    input:
        "src/potentials_normed.py",
        rules.demand.output,
        rules.constrained_potentials.output
    output:
        "build/{layer}/{scenario}/normed-potentials.csv"
    shell:
        PYTHON_SCRIPT


rule technology_potentials:
    message: "Potentials per technology for layer {wildcards.layer} and scenario {wildcards.scenario}."
    input:
        "src/potentials_technology.py",
        rules.unconstrained_potentials.output,
    output:
        "build/{layer}/{scenario}/technology-potentials.csv"
    shell:
        PYTHON_SCRIPT + " {wildcards.scenario} {CONFIG_FILE}"


rule european_potentials:
    message: "Summarise potentials on European level for scenario {wildcards.scenario}."
    input:
        constrained_potentials = "build/national/{scenario}/constrained-potentials.csv",
        technology_potentials = "build/national/{scenario}/technology-potentials.csv",
        demand = "build/national/demand.csv"
    output:
        "build/{scenario}/european-potentials.csv"
    params: scenario = "{scenario}"
    run:
        import pandas as pd
        demand = pd.read_csv(input.demand, index_col=0)["demand_twh_per_year"]
        constrained_potentials = pd.read_csv(input.constrained_potentials, index_col=0).reindex(demand.index)
        technology_potentials = pd.read_csv(input.technology_potentials, index_col=0).reindex(demand.index)
        pd.Series({
            "Total [TWh/a]": constrained_potentials.sum().sum(),
            "Normed [%]": constrained_potentials.sum().sum() / demand.sum() * 100,
            "Roof mounted PV [TWh/a]": technology_potentials["rooftop-pv"].sum(),
            "Open field PV [TWh/a]": technology_potentials["pv-farm"].sum(),
            "Onshore wind [TWh/a]": technology_potentials["onshore wind"].sum(),
            "Offshore wind [TWh/a]": technology_potentials["offshore wind"].sum(),
            "Roof mounted PV [%]": technology_potentials["rooftop-pv"].sum() / demand.sum() * 100,
            "Open field PV [%]": technology_potentials["pv-farm"].sum() / demand.sum() * 100,
            "Onshore wind [%]": technology_potentials["onshore wind"].sum() / demand.sum() * 100,
            "Offshore wind [%]": technology_potentials["offshore wind"].sum() / demand.sum() * 100,
        }, name=params.scenario).to_csv(output[0], index=True, header=True, float_format="%.0f")


rule european_potentials_aggregation:
    message: "Aggregate the European potentials to create table for paper."
    input: expand("build/{scenario}/european-potentials.csv", scenario=config["paper"]["europe-level-results"]),
    output: "build/european-potentials.csv"
    run:
        import pandas as pd
        summaries = [pd.read_csv(summary_path, index_col=0) for summary_path in input]
        pd.concat(summaries, axis=1).to_csv(output[0], header=True, index=True)


rule normed_potential_plots:
    message: "Plot fraction of land necessary for scenario {wildcards.scenario}."
    input:
        src = "src/vis/potentials_normed.py",
        national_regions = "build/national/regions.geojson",
        subnational_regions = "build/subnational/regions.geojson",
        municipal_regions = "build/municipal/regions.geojson",
        national_normed_potential = "build/national/{scenario}/normed-potentials.csv",
        subnational_normed_potential = "build/subnational/{scenario}/normed-potentials.csv",
        municipal_normed_potential = "build/municipal/{scenario}/normed-potentials.csv",
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
        "build/{scenario}/normed-potentials-boxplots.png",
        "build/{scenario}/normed-potentials-map.png",
        "build/{scenario}/normed-potentials-correlations.png"
    shell:
        PYTHON + " {input.src} "
                 "{input.national_regions},{input.national_normed_potential},{input.national_population},{input.national_land_cover},{input.national_protected_areas},{input.national_demand} "
                 "{input.subnational_regions},{input.subnational_normed_potential},{input.subnational_population},{input.subnational_land_cover},{input.subnational_protected_areas},{input.subnational_demand} "
                 "{input.municipal_regions},{input.municipal_normed_potential},{input.municipal_population},{input.municipal_land_cover},{input.municipal_protected_areas},{input.municipal_demand} "
                 "{input.national_regions} "
                 "{input.worldwide_countries} "
                 "{output}"


rule technology_potentials_plot:
    message: "Plot potentials of renewable power for scenario {wildcards.scenario}."
    input:
        "src/vis/potentials_technology.py",
        "build/national/demand.csv",
        "build/national/{scenario}/technology-potentials.csv",
    output:
        "build/{scenario}/technology-potentials.png"
    shell:
        PYTHON_SCRIPT


rule necessary_land_plot:
    message: "Plot the fraction of land needed to become autarkic."
    input:
        "src/vis/necessary_land.py",
        "build/municipal/unconstrained-potentials-prefer-pv.csv",
        "build/municipal/unconstrained-potentials-prefer-wind.csv",
        "build/municipal/demand.csv"
    output:
        "build/necessary-land.png"
    shell:
        PYTHON_SCRIPT


rule necessary_land_plot_all_layers:
    message: "Plot the fraction of land needed to become autarkic."
    input:
        "build/national/demand.csv",
        "build/subnational/demand.csv",
        "build/municipal/demand.csv",
        "build/national/unconstrained-potentials-prefer-pv.csv",
        "build/subnational/unconstrained-potentials-prefer-pv.csv",
        "build/municipal/unconstrained-potentials-prefer-pv.csv",
        "build/national/regional-eligibility.csv",
        "build/subnational/regional-eligibility.csv",
        "build/municipal/regional-eligibility.csv",
        src = "src/vis/necessary_land_all_layers.py",
    output:
        "build/necessary-land-all-layers.png"
    shell:
        PYTHON + " {input.src} {output}"


rule solution_matrix_plot:
    message: "Plot the solution matrix showing pathways to reach 100% sufficent power supply."
    input:
        "src/vis/solution.py",
        "build/municipal/demand.csv",
        "build/municipal/population.csv",
        "build/municipal/social-ecological-potential/constrained-potentials.csv",
        "build/municipal/zero-protection/constrained-potentials.csv",
    output:
        "build/solution-matrix.png"
    shell:
        PYTHON_SCRIPT


rule exclusion_layers_plot:
    message: "Visualise the exclusion layers for {wildcards.country_code}."
    input:
        "src/vis/exclusion_layers.py",
        "build/national/regions.geojson",
        rules.land_cover_in_europe.output,
        rules.slope_in_europe.output,
        rules.protected_areas_in_europe.output,
        rules.settlements.output.buildings,
    output:
        "build/exclusion-layers-{country_code}.png"
    shell:
        PYTHON_SCRIPT + " {wildcards.country_code}"


rule layer_overview:
    message: "Overview table of administrative layers."
    input:
        expand("build/{layer}/regions.geojson", layer=config["layers"].keys())
    output:
        "build/overview-administrative-levels.csv"
    run:
        import pandas as pd
        import geopandas as gpd

        def format_source(source_name):
            source = source_name[:-1].upper()
            if source in ["NUTS", "LAU"]:
                source = source + " [@eurostat:2015]"
            elif source == "GADM":
                source = source + " [@GADM:2018]"
            return source

        layer_names = [path_to_file.split("/")[1] for path_to_file in input]
        sources = [[format_source(source) for source in set(config["layers"][layer_name].values())]
                   for layer_name in layer_names]
        sources = [", ".join(set(sources_per_layer)) for sources_per_layer in sources]
        number_regions = [len(gpd.read_file(path_to_file).index) for path_to_file in input]

        layer_names = ["European"] + layer_names
        number_regions = ["1"] + number_regions
        sources = [sources[0]] + sources

        pd.DataFrame({
            "level": layer_names,
            "number regions": number_regions,
            "source of shape data": sources
        }).to_csv(output[0], index=False, header=True)


rule scenario_overview:
    message: "Brief overview over results of all scenarios on the municipal level."
    input:
        expand("build/municipal/{scenario}/constrained-potentials.csv", scenario=config["scenarios"].keys()),
        "build/municipal/slope.csv",
        rules.lau2_urbanisation_degree.output,
        "build/municipal/population.csv",
        "build/municipal/demand.csv"
    output:
        "build/scenario-overview.csv"
    run:
        import pandas as pd

        demand = pd.read_csv(input[-1], index_col=0)["demand_twh_per_year"]
        industrial = pd.read_csv(input[-1], index_col=0)["industrial_demand_fraction"] > 0.5
        population = pd.read_csv(input[-2], index_col=0)["population_sum"].reindex(demand.index)
        high_density = pd.read_csv(input[-2], index_col=0)["density_p_per_km2"].reindex(demand.index) > 1000
        potentials = [pd.read_csv(path, index_col=0).sum(axis=1).reindex(demand.index) for path in input[:-4]]
        urbanisation = pd.read_csv(input[-3], index_col=0)["urbanisation_class"].reindex(demand.index)
        steep = pd.read_csv(input[-4], index_col=0).reindex(demand.index)._median > 20
        urban = urbanisation == 1
        town = urbanisation == 2
        rural = urbanisation == 3
        classified = urban | town | rural
        scenario_names = [path.split("/")[2] for path in input[:-4]]
        overview = pd.DataFrame(
            index=scenario_names,
            columns=[
                "unit share with insufficient supply",
                "population share with insufficient supply",
                "of which urban",
                "of which town",
                "of which rural",
                "of which densely populated",
                "of which in industrial area",
                "of which in steep area",
                "high density pop affected",
                "low density pop affected",
            ]
        )
        overview["unit share with insufficient supply"] = [
            population[pot < demand].count() / population.count() for pot in potentials
        ]
        overview["population share with insufficient supply"] = [
            population[pot < demand].sum() / population.sum() for pot in potentials
        ]
        overview["of which urban"] = [
            population[(pot < demand) & urban].sum() / population[(pot < demand) & classified].sum() for pot in potentials
        ]
        overview["of which town"] = [
            population[(pot < demand) & town].sum() / population[(pot < demand) & classified].sum() for pot in potentials
        ]
        overview["of which rural"] = [
            population[(pot < demand) & rural].sum() / population[(pot < demand) & classified].sum() for pot in potentials
        ]
        overview["of which densely populated"] = [
            population[(pot < demand) & high_density].sum() / population[pot < demand].sum() for pot in potentials
        ]
        overview["of which in industrial area"] = [
            population[(pot < demand) & industrial].sum() / population[pot < demand].sum() for pot in potentials
        ]
        overview["of which in steep area"] = [
            population[(pot < demand) & steep].sum() / population[pot < demand].sum() for pot in potentials
        ]
        overview["high density pop affected"] = [
            population[(pot < demand) & high_density].sum() / population[high_density].sum() for pot in potentials
        ]
        overview["low density pop affected"] = [
            population[(pot < demand) & ~high_density].sum() / population[~high_density].sum() for pot in potentials
        ]
        overview.to_csv(output[0], header=True, float_format="%.4f")


rule sensitivities:
    message: "Perform sensitivity analysis on layer {wildcards.layer} using {threads} threads."
    input:
        "src/sensitivity.py",
        "build/{layer}/unconstrained-potentials-prefer-pv.csv",
        "build/{layer}/unconstrained-potentials-prefer-wind.csv",
        "build/{layer}/demand.csv",
        "build/{layer}/population.csv",
        "build/{layer}/regions.geojson"
    output:
        "build/{layer}/sensitivities-urban-population.txt",
        "build/{layer}/sensitivities-rural-population.txt",
        "build/{layer}/sensitivities-number.txt"
    threads: config["snakemake"]["max-threads"]
    shell:
        PYTHON_SCRIPT + " {threads}"


rule report:
    message: "Compile report."
    input:
        "report/literature.bib",
        "report/main.md",
        "report/pandoc-metadata.yml",
        "build/social-ecological-potential/normed-potentials-map.png",
        "build/social-ecological-potential/potentials.png",
        rules.solution_matrix_plot.output
    output:
        "build/report.pdf"
    shell:
        """
        cd ./report
        pandoc --filter pantable --filter pandoc-fignos --filter pandoc-tablenos \
        --filter pandoc-citeproc main.md pandoc-metadata.yml -t latex -o ../build/report.pdf
        """


rule paper:
    message: "Compile paper."
    input:
        "report/literature.bib",
        "report/paper.md",
        "report/pandoc-metadata.yml",
        "build/technical-potential/normed-potentials-boxplots.png",
        "build/social-ecological-potential/normed-potentials-map.png",
        "build/european-potentials.csv",
        "build/necessary-land.png",
        "build/necessary-land-all-layers.png",
        rules.sonnendach_statistics.output.publish,
        "build/exclusion-layers-ROU.png",
        rules.layer_overview.output
    output:
        "build/paper.pdf"
    shell:
        """
        cd ./report
        {PANDOC} paper.md pandoc-metadata.yml -t latex -o ../build/paper.pdf
        """

rule paper_docx:
    message: "Compile paper to docx."
    input:
        paper = "report/paper.md",
        metadata = "report/pandoc-metadata.yml",
        all_other = rules.paper.output # to avoid repeating actual depdencies
    output: "build/paper.docx"
    shell:
        """
        cd ./report
        {PANDOC} ../report/paper.md ../report/pandoc-metadata.yml -t docx -o ../build/paper.docx
        """


rule supplementary_material:
    message: "Compile the supplementary material."
    input:
        "report/supplementary.md",
        expand(
            "build/exclusion-layers-{country_code}.png",
            country_code=[pycountry.countries.lookup(country).alpha_3
                          for country in config["scope"]["countries"]]
        )
    output:
        "build/supplementary-material.pdf"
    shell:
        """
        cd ./report
        {PANDOC} supplementary.md -t latex -o ../build/supplementary-material.pdf
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
