"""Rules analysing the scenario results."""


wildcard_constraints:
        suffix = "((png)|(tif))" # can plot tif or png


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
        "build/municipal/{scenario}/merged-results.gpkg"
    output:
        "build/{scenario}/normed-potentials-boxplots.{suffix}"
    conda: "../envs/default.yaml"
    shell:
        PYTHON_SCRIPT


rule potentials_sufficiency_map:
    message: "Plot potential sufficiency maps for scenario {wildcards.scenario}."
    input:
        "src/vis/potentials_sufficiency_map.py",
        "build/continental/{scenario}/merged-results.gpkg",
        "build/national/{scenario}/merged-results.gpkg",
        "build/regional/{scenario}/merged-results.gpkg",
        "build/municipal/{scenario}/merged-results.gpkg"
    output:
        "build/{scenario}/sufficient-potentials-map.{suffix}"
    conda: "../envs/default.yaml"
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
        "build/{scenario}/necessary-land-all-layers.{suffix}"
    conda: "../envs/default.yaml"
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
        "build/{scenario}/necessary-land-map-when-pv-{pvshare}%.{suffix}"
    conda: "../envs/default.yaml"
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
        "build/exclusion-layers-{country_code}.{suffix}"
    conda: "../envs/default.yaml"
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

        ALL_LAYERS = ["continental", "national", "regional", "municipal"]

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
        potential = expand(
            "build/municipal/{scenario}/potentials.csv",
            scenario=config["paper"]["europe-level-results"]
        ),
        urbanisation = rules.lau2_urbanisation_degree.output[0],
        population = "build/municipal/population.csv",
        demand = "build/municipal/demand.csv"
    output:
        "build/municipal/overview-scenarios.csv"
    run:
        import pandas as pd

        demand = pd.read_csv(input.demand, index_col=0)["demand_twh_per_year"]
        industrial = pd.read_csv(input.demand, index_col=0)["industrial_demand_fraction"] > 0.5
        population = pd.read_csv(input.population, index_col=0)["population_sum"].reindex(demand.index)
        high_density = pd.read_csv(input.population, index_col=0)["density_p_per_km2"].reindex(demand.index) > 1000
        potentials = [pd.read_csv(path, index_col=0).sum(axis=1).reindex(demand.index) for path in input.potential]
        urbanisation = pd.read_csv(input.urbanisation, index_col=0)["urbanisation_class"].reindex(demand.index)
        urban = urbanisation == 1
        town = urbanisation == 2
        rural = urbanisation == 3
        classified = urban | town | rural
        scenario_names = [path.split("/")[2] for path in input.potential]
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
        overview["high density pop affected"] = [
            population[(pot < demand) & high_density].sum() / population[high_density].sum() for pot in potentials
        ]
        overview["low density pop affected"] = [
            population[(pot < demand) & ~high_density].sum() / population[~high_density].sum() for pot in potentials
        ]
        overview.to_csv(output[0], header=True, float_format="%.4f")
