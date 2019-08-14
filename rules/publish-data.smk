"""Rules to prepare publication of result data."""

localrules: prepare_everything_for_publication, copy

LAYERS = config["layers"].keys()
SCENARIOS = ["technical-potential", "technical-social-potential"]
PV_SHARES = config["paper"]["pv-shares"]

rule prepare_everything_for_publication:
    message: "Prepare all files for publication."
    input:
        expand("build/publish/{layer}/units.csv", layer=LAYERS),
        expand("build/publish/{layer}/population.csv", layer=LAYERS),
        expand("build/publish/{layer}/demand.csv", layer=LAYERS),
        expand("build/publish/{layer}/shared-coast.csv", layer=LAYERS),
        expand("build/publish/{layer}/{scenario}/areas.csv", layer=LAYERS, scenario=SCENARIOS),
        expand("build/publish/{layer}/{scenario}/capacities.csv", layer=LAYERS, scenario=SCENARIOS),
        expand("build/publish/{layer}/{scenario}/potentials.csv", layer=LAYERS, scenario=SCENARIOS),
        expand("build/publish/{layer}/{scenario}/normed-potentials.csv", layer=LAYERS, scenario=SCENARIOS),
        expand(
            "build/publish/{layer}/necessary-land/necessary-land-when-pv-{pvshare}%.csv",
            layer=LAYERS,
            pvshare=PV_SHARES
        )


rule copy:
    message: "Copy file {input[0]} in preparation for publication."
    input: "build/{path_to_file}/{filename}.{suffix}"
    output: "build/publish/{path_to_file}/{filename}.{suffix}"
    shell: "cp {input} {output}"


rule units_without_geometry:
    message: "Remove shapes from units." # We are not allowed to redistribute those.
    input: rules.units.output[0]
    output: "build/publish/{layer}/units.csv"
    run:
        import pandas as pd
        import geopandas as gpd

        units = gpd.read_file(input[0]).set_index("id")
        units = pd.DataFrame(units)
        del units["geometry"]
        units.to_csv(output[0], index=True, header=True)
