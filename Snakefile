PYTHON = "PYTHONPATH=./ python"
PANDOC = "pandoc --filter pantable --filter pandoc-fignos --filter pandoc-tablenos --filter pandoc-citeproc"
PYTHON_SCRIPT = "PYTHONPATH=./ python {input} {output}"

CONFIG_FILE = "config/default.yaml"

configfile: CONFIG_FILE
include: "rules/data-preprocessing.smk"
include: "rules/sonnendach.smk"

RAW_PV_CAPACITY_FACTORS = "data/pv.nc"


rule all:
    message: "Run entire analysis and compile report."
    input:
        "build/paper.pdf",
        "build/paper.docx",
        "build/supplementary-material.docx"


rule category_of_technical_eligibility:
    message:
        "Determine upper bound surface eligibility for renewables based on land cover, slope, bathymetry, and settlements."
    input:
        "src/technical_eligibility.py",
        rules.land_cover_in_europe.output,
        rules.slope_in_europe.output,
        rules.bathymetry_in_europe.output,
        rules.settlements.output.buildings,
        rules.settlements.output.urban_greens
    output:
        "build/technically-eligible-land.tif"
    shell:
        PYTHON_SCRIPT + " {CONFIG_FILE}"


rule area_of_technical_eligibility:
    message:
        "Quantify the area that is technically eligible for renewables."
    input:
        "src/technically_eligible_area.py",
        rules.category_of_technical_eligibility.output,
        rules.settlements.output.buildings,
        rules.correction_factor_building_footprint_to_available_rooftop.output
    output:
        "build/technically-eligible-area-km2.tif"
    shell:
        PYTHON_SCRIPT


rule capacity_of_technical_eligibility:
    message:
        "Quantify the capacity that is technically eligible for renewables."
    input:
        "src/technically_eligible_capacity.py",
        rules.category_of_technical_eligibility.output,
        rules.area_of_technical_eligibility.output,
        rules.sonnendach_statistics.output.raw
    output:
        "build/technically-eligible-capacity-pv-prio-mw.tif",
        "build/technically-eligible-capacity-wind-prio-mw.tif",
    shell:
        PYTHON_SCRIPT + " {CONFIG_FILE}"


rule electricity_yield_of_technical_eligibility:
    message:
        "Quantify the max annual electricity yield that is technically eligible for renewables."
    input:
        "src/technically_eligible_electricity_yield.py",
        rules.category_of_technical_eligibility.output,
        rules.capacity_of_technical_eligibility.output,
    output:
        "build/technically-eligible-electricity-yield-pv-prio-twh.tif",
        "build/technically-eligible-electricity-yield-wind-prio-twh.tif",
    shell:
        PYTHON_SCRIPT


rule units:
    message: "Form units of layer {wildcards.layer} by remixing NUTS, LAU, and GADM."
    input:
        "src/units.py",
        rules.administrative_borders_nuts.output,
        rules.administrative_borders_lau.output,
        rules.administrative_borders_gadm.output
    output:
        "build/{layer}/units.geojson"
    shell:
        PYTHON_SCRIPT + " {wildcards.layer} {CONFIG_FILE}"


rule local_land_cover:
    message: "Land cover statistics per unit of layer {wildcards.layer}."
    input:
        units = rules.units.output,
        land_cover = rules.land_cover_in_europe.output,
        src = "src/geojson_to_csv.py"
    output:
        "build/{layer}/land-cover.csv"
    shell:
        """
        fio cat {input.units} | \
        rio zonalstats -r {input.land_cover} --prefix 'lc_' --categorical | \
        {PYTHON} {input.src} -a id -a lc_11 -a lc_14 -a lc_20 -a lc_30 -a lc_40 \
        -a lc_50 -a lc_60 -a lc_70 -a lc_90 -a lc_100 -a lc_110 -a lc_120 -a lc_130 \
        -a lc_140 -a lc_150 -a lc_160 -a lc_170 -a lc_180 -a lc_190 -a lc_200 \
        -a lc_210 -a lc_220 -a lc_230 > \
        {output}
        """


rule local_built_up_area:
    message: "Determine the built up area for administrative units in layer {wildcards.layer}."
    input:
        "src/built_up_area.py",
        rules.settlements.output.built_up,
        rules.units.output
    output:
        "build/{layer}/built-up-areas.csv"
    shell:
        PYTHON_SCRIPT


rule population:
    message: "Allocate population to units of layer {wildcards.layer}."
    input:
        units = rules.units.output,
        population = rules.population_in_europe.output,
        src_geojson = "src/geojson_to_csv.py",
        src_population = "src/population.py",
        land_cover = rules.local_land_cover.output
    output:
        "build/{layer}/population.csv"
    shell:
        """
        crs=$(rio info --crs {input.population})
        fio cat --dst_crs "$crs" {input.units} | \
        rio zonalstats -r {input.population} --prefix 'population_' --stats sum | \
        {PYTHON} {input.src_geojson} -a id -a population_sum -a proper | \
        {PYTHON} {input.src_population} {input.units} {input.land_cover} > \
        {output}
        """


rule demand:
    message: "Allocate electricity demand to units of layer {wildcards.layer}."
    input:
        "src/spatial_demand.py",
        rules.electricity_demand_national.output,
        rules.industry.output,
        rules.units.output,
        rules.population.output
    output:
        "build/{layer}/demand.csv"
    shell:
        PYTHON_SCRIPT


rule eez_eligibility:
    message:
        "Allocate eligible land to exclusive economic zones using {threads} threads."
    input:
        src = "src/eligibility_local.py",
        regions = rules.eez_in_europe.output,
        eligibility = rules.category_of_technical_eligibility.output
    output:
        "build/eez-eligibility.csv"
    threads: config["snakemake"]["max-threads"]
    shell:
        PYTHON + " {input.src} offshore {input.regions} {input.eligibility} {output} {threads}"


rule shared_coast:
    message: "Determine share of coast length between eez and units of layer {wildcards.layer} using {threads} threads."
    input:
        "src/shared_coast.py",
        rules.units.output,
        rules.eez_in_europe.output
    output:
        "build/{layer}/shared-coast.csv"
    threads: config["snakemake"]["max-threads"]
    shell:
        PYTHON_SCRIPT + " {threads}"


rule national_capacity_factors:
    message: "Merge national renewable capacity factors and replace missing."
    input:
        "src/capacity_factors_national.py",
        rules.raw_wind_capacity_factors.output,
        rules.raw_pv_capacity_factors.output
    output:
        "build/capacity-factors-national.csv"
    shell:
        PYTHON_SCRIPT + " {CONFIG_FILE}"


rule wind_capacity_factors:
    message: "Create wind capacity factors with highest spatial resolution."
    input:
        "src/capacity_factors_wind.py",
        rules.national_capacity_factors.output,
        "data/wind/",
        "build/national/units.geojson",
        rules.administrative_borders_nuts.output
    output:
        "build/capacity-factors-wind.geojson"
    shell:
        PYTHON_SCRIPT + " {CONFIG_FILE}"


rule raw_regional_pv_capacity_factors:
    message: "Process renewables.ninja capacity factors."
    input:
        RAW_PV_CAPACITY_FACTORS
    output:
        "build/capacity-factors-pv-raw.csv"
    run:
        import xarray as xr

        ds = xr.open_dataset(input[0])
        pv_cfs = ds.mean(dim="time_utc")
        pv_cfs.to_dataframe().to_csv(output[0], header=True, index=True)


rule pv_capacity_factors:
    message: "Derive PV capacity factors on regional level."
    input:
        "src/capacity_factors_pv.py",
        rules.raw_regional_pv_capacity_factors.output,
        "build/regional/units.geojson",
        rules.sonnendach_statistics.output.raw,
    output:
        "build/capacity-factors-pv.geojson"
    shell:
        PYTHON_SCRIPT


rule local_capacity_factors:
    message: "Determine capacity factors for units of layer {wildcards.layer} using {threads} threads."
    input:
        "src/capacity_factors_local.py",
        rules.units.output,
        rules.wind_capacity_factors.output,
        rules.pv_capacity_factors.output
    output:
        "build/{layer}/capacity-factors.csv"
    threads: config["snakemake"]["max-threads"]
    shell:
        PYTHON_SCRIPT + " {threads}"


rule potentials:
    message:
        "Determine the constrained potentials for layer {wildcards.layer} in scenario {wildcards.scenario}."
    input:
        "src/potentials.py",
        rules.units.output,
        rules.electricity_yield_of_technical_eligibility.output,
        rules.category_of_technical_eligibility.output,
        rules.land_cover_in_europe.output,
        rules.protected_areas_in_europe.output
    output:
        "build/{layer}/{scenario}/potentials.csv"
    shell:
        PYTHON_SCRIPT + " {wildcards.scenario} {CONFIG_FILE}"


rule normed_potentials:
    message:
        "Determine potentials relative to demand for layer {wildcards.layer} "
        "in scenario {wildcards.scenario}."
    input:
        "src/potentials_normed.py",
        rules.demand.output,
        rules.potentials.output
    output:
        "build/{layer}/{scenario}/normed-potentials.csv"
    shell:
        PYTHON_SCRIPT


rule footprint:
    message: "Determine the land footprint of the renewable potential for layer {wildcards.layer} "
             "in scenario {wildcards.scenario}."
    input:
        "src/footprint.py",
        rules.category_of_technical_eligibility.output,
        rules.area_of_technical_eligibility.output,
        rules.electricity_yield_of_technical_eligibility.output,
        rules.land_cover_in_europe.output,
        rules.protected_areas_in_europe.output,
        rules.units.output
    output:
        "build/{layer}/{scenario}/footprint.csv"
    shell:
        PYTHON_SCRIPT + " {wildcards.scenario} {CONFIG_FILE}"


rule necessary_land:
    message: "Determine the necessary potentials to become autarkic of layer {wildcards.layer} "
             "in scenario {wildcards.scenario} given rooftop PV share {wildcards.pvshare}%."
    input:
        "src/necessary_land.py",
        rules.demand.output,
        rules.potentials.output,
        rules.footprint.output,
        rules.local_built_up_area.output
    output:
        "build/{layer}/{scenario}/necessary-land-when-pv-{pvshare}%.csv"
    shell:
        PYTHON_SCRIPT + " {wildcards.pvshare}"


rule scenario_results:
    message: "Merge all results of scenario {wildcards.scenario} for layer {wildcards.layer}."
    input:
        units = rules.units.output,
        demand = rules.demand.output,
        population = rules.population.output,
        constrained_potentials = rules.potentials.output,
        normed_potentials = rules.normed_potentials.output
    output:
        "build/{layer}/{scenario}/merged-results.geojson"
    run:
        import pandas as pd
        import geopandas as gpd

        gpd.read_file(input.units[0]).merge(
            pd.concat(
                [pd.read_csv(path, index_col="id") for path in input[1:]],
                axis=1
            ),
            left_on="id",
            right_index=True
        ).to_file(output[0], driver="GeoJSON")


rule necessary_land_overview:
    message: "Create table showing the fraction of land needed to become autarkic in scenario {wildcards.scenario} "
             "for rooftop PV share {wildcards.pvshare}%."
    input:
        nec_land = expand("build/{layer}/{{scenario}}/necessary-land-when-pv-{{pvshare}}%.csv", layer=config["layers"].keys()),
        demand = expand("build/{layer}/demand.csv", layer=config["layers"].keys())
    output:
        "build/{scenario}/overview-necessary-land-when-pv-{pvshare}%.csv"
    run:
        import pandas as pd
        nec_lands = [pd.read_csv(path, index_col=0)["fraction_non_built_up_land_necessary"] for path in input.nec_land]
        nec_roofs = [pd.read_csv(path, index_col=0)["fraction_roofs_necessary"] for path in input.nec_land]
        roof_pv_gens = [pd.read_csv(path, index_col=0)["rooftop_pv_generation_twh_per_year"] for path in input.nec_land]
        demands = [pd.read_csv(path, index_col=0)["demand_twh_per_year"] for path in input.demand]
        roof_pv_shares = [roof_pv_gen / demand for roof_pv_gen, demand in zip(roof_pv_gens, demands)]
        data = pd.DataFrame(
            index=[name.capitalize() for name in config["layers"].keys()],
            data={
                "Average land use [%]": [nec_land.mean() * 100 for nec_land in nec_lands],
                "Average roof space use [%]": [nec_roof.mean() * 100 for nec_roof in nec_roofs],
                "Average roof-mounted PV share [%]:": [roof_pv_share.mean() * 100 for roof_pv_share in roof_pv_shares]
            }
        )
        data.index.name = "Level"
        data.to_csv(
            output[0],
            index=True,
            header=True,
            float_format="%.0f"
        )


rule normed_potential_boxplots:
    message: "Plot ranges of relative potential for scenario {wildcards.scenario}."
    input:
        "src/vis/potentials_normed_boxplot.py",
        "build/municipal/{scenario}/merged-results.geojson"
    output:
        "build/{scenario}/normed-potentials-boxplots.png"
    shell:
        PYTHON_SCRIPT


rule potentials_sufficiency_map:
    message: "Plot potential sufficiency maps for scenario {wildcards.scenario}."
    input:
        "src/vis/potentials_sufficiency_map.py",
        "build/european/{scenario}/merged-results.geojson",
        "build/national/{scenario}/merged-results.geojson",
        "build/regional/{scenario}/merged-results.geojson",
        "build/municipal/{scenario}/merged-results.geojson"
    output:
        "build/{scenario}/sufficient-potentials-map.png"
    shell:
        PYTHON_SCRIPT


rule necessary_land_plot_all_layers:
    message: "Plot the fraction of land needed to become autarkic in scenario {wildcards.scenario}."
    input:
        "src/vis/necessary_land_all_layers.py",
        expand("build/{layer}/{{scenario}}/necessary-land-when-pv-{pvshare}%.csv",
               layer=config["layers"].keys(),
               pvshare=[0, 20, 40, 60, 80, 100]),
        expand("build/{layer}/population.csv", layer=config["layers"].keys()),
    output:
        "build/{scenario}/necessary-land-all-layers.png"
    shell:
        PYTHON_SCRIPT


rule necessary_land_map:
    message: "Plot maps of land needed to become autarkic in scenario {wildcards.scenario} "
             "for rooftop PV share {wildcards.pvshare}%."
    input:
        "src/vis/necessary_land_map.py",
        expand("build/{layer}/units.geojson", layer=config["layers"].keys()),
        expand("build/{layer}/{{scenario}}/necessary-land-when-pv-{{pvshare}}%.csv", layer=config["layers"].keys()),
        expand("build/{layer}/population.csv", layer=config["layers"].keys())
    output:
        "build/{scenario}/necessary-land-map-when-pv-{pvshare}%.png"
    shell:
        PYTHON_SCRIPT


rule exclusion_layers_plot:
    message: "Visualise the exclusion layers for {wildcards.country_code}."
    input:
        "src/vis/exclusion_layers.py",
        "build/national/units.geojson",
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
        expand("build/{layer}/units.geojson", layer=config["layers"].keys())
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
        number_units = [len(gpd.read_file(path_to_file).index) for path_to_file in input]

        pd.DataFrame({
            "Level": [name.capitalize() for name in layer_names],
            "Number units": number_units,
            "Source of shape data": sources
        }).to_csv(output[0], index=False, header=True)


rule scenario_overview:
    message: "Overview over scenario on all levels."
    input:
        normed_potentials = expand("build/{layer}/{{scenario}}/normed-potentials.csv", layer=config["layers"].keys()),
        population = expand("build/{layer}/population.csv", layer=config["layers"].keys())
    output:
        "build/{scenario}/overview.csv"
    run:
        import pandas as pd

        def add_layer(df, path_to_file):
            layer_name = path_to_file.split("/")[1]
            df["layer"] = layer_name
            return df

        ALL_LAYERS = ["european", "national", "regional", "municipal"]

        normed_potential = pd.concat([pd.read_csv(path, index_col="id").pipe(lambda df: add_layer(df, path))
                                     for path in input.normed_potentials])
        population = pd.concat([pd.read_csv(path, index_col="id").pipe(lambda df: add_layer(df, path))
                               for path in input.population])

        affected = normed_potential.normed_potential < 1.0
        high_density = population.density_p_per_km2 > 1000
        overview = pd.DataFrame(
            index=[path_to_file.split("/")[1] for path_to_file in input.normed_potentials]
        )
        overview["units affected [%]"] = (normed_potential.loc[affected].groupby("layer").count() /
                                          normed_potential.groupby("layer").count() * 100).reindex(ALL_LAYERS).iloc[:, 0]
        overview["of which dense units [%]"] = (normed_potential.loc[affected & high_density].groupby("layer").count() /
                                                normed_potential.loc[affected].groupby("layer").count() * 100).reindex(ALL_LAYERS).iloc[:, 0]
        overview["people affected [%]"] = (population.loc[affected].groupby("layer").population_sum.sum() /
                                           population.groupby("layer").population_sum.sum() * 100).reindex(ALL_LAYERS)
        overview["of which from dense units [%]"] = (population.loc[affected & high_density].groupby("layer").population_sum.sum() /
                                                     population.loc[affected].groupby("layer").population_sum.sum() * 100).reindex(ALL_LAYERS)

        overview.fillna(0).transpose().to_csv(output[0], index=True, header=True, float_format="%.1f")


rule scenarios_overview:
    message: "Brief overview over results of all scenarios on the municipal level."
    input:
        expand("build/municipal/{scenario}/constrained-potentials.csv", scenario=config["scenarios"].keys()),
        "build/municipal/slope.csv",
        rules.lau2_urbanisation_degree.output,
        "build/municipal/population.csv",
        "build/municipal/demand.csv"
    output:
        "build/overview-scenarios.csv"
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
        "build/{layer}/units.geojson"
    output:
        "build/{layer}/sensitivities-urban-population.txt",
        "build/{layer}/sensitivities-rural-population.txt",
        "build/{layer}/sensitivities-number.txt"
    threads: config["snakemake"]["max-threads"]
    shell:
        PYTHON_SCRIPT + " {threads}"


rule paper:
    message: "Compile paper."
    input:
        "report/literature.bib",
        "report/paper.md",
        "report/pandoc-metadata.yml",
        "build/technical-potential/normed-potentials-boxplots.png",
        "build/technical-potential/sufficient-potentials-map.png",
        "build/technical-social-potential/sufficient-potentials-map.png",
        "build/technical-social-potential/normed-potentials-boxplots.png",
        "build/necessary-land/overview-necessary-land-when-pv-100%.csv",
        "build/necessary-land/overview-necessary-land-when-pv-40%.csv",
        "build/necessary-land/necessary-land-map-when-pv-40%.png",
        "build/necessary-land/necessary-land-all-layers.png",
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
        rules.sonnendach_statistics.output.publish,
        expand(
            "build/exclusion-layers-{country_code}.png",
            country_code=[pycountry.countries.lookup(country).alpha_3
                          for country in config["scope"]["countries"]]
        )
    output:
        "build/supplementary-material.docx"
    shell:
        """
        cd ./report
        {PANDOC} supplementary.md -t docx -o ../build/supplementary-material.docx --table-of-contents
        """


rule clean: # removes all generated results
    shell:
        """
        rm -r ./build/*
        echo "Data downloaded to data/ has not been cleaned."
        """


rule test:
    input:
        "build/paper.pdf" # proxy for: all has to exist before running the tests
    shell:
        "py.test"
