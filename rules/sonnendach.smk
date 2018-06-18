"""These rules analyse statistics of the Swiss Sonnendach dataset.

These rules are not part of the main workflow and can be executed separately given
that you have the Sonnendach dataset available (www.sonnendach.ch). At the time of
this writing, the dataset is available only on request.

Run it like so:

    snakemake -s rules/sonnendach.smk

Plot the rulegraph like so:

    snakemake -s rules/sonnendach.smk --rulegraph | dot -Tpdf > dag.pdf

The statistics that result from this analysis have been manually added to the
main workflow.
"""
RAW_SONNENDACH_DATA = "data/sonnendach/SOLKAT_R1-R9_20180418.gdb/"
LAYER_NAME = "SOLKAT_CH_DACH"
DATA_AVAILABLE = 255
RASTER_RESOLUTION_IN_M = 100
CONFIG_FILE = "config/default.yaml"

configfile: CONFIG_FILE
include: "./data-preprocessing.smk"

rule all:
    input: "build/swiss/overestimation-settlement-data.txt"


rule rasterise_sonnendach:
    message: "Rasterise the sonnendach data to quantify its spatial extend."
    input:
        RAW_SONNENDACH_DATA
    output:
        "build/swiss/sonnendach-availability.tif"
    shell:
        """
        gdal_rasterize -at -burn {DATA_AVAILABLE} -of GTiff -init 0 -tr {RASTER_RESOLUTION_IN_M} {RASTER_RESOLUTION_IN_M} \
        -ot Int16 -l {LAYER_NAME} {input} {output}
        """


rule swiss_rooftops_from_settlement_data:
    message: "Warp and reproject settlement data to sonnendach extend and coordinates."
    input:
        rooftops = rules.rooftop_area.output,
        sonnendach = rules.rasterise_sonnendach.output
    output:
        "build/swiss/swiss-rooftops.tif"
    shell:
        "rio warp {input.rooftops} -o {output} --like {input.sonnendach} --resampling average"


rule total_size_swiss_rooftop_area_according_to_settlement_data:
    message: "Sum the size of roofs from the settlement data on the spatial extend of the sonnendach data."
    input:
        rooftops = rules.swiss_rooftops.output,
        sonnendach = rules.rasterise_sonnendach.output
    output:
        "build/swiss/swiss-rooftop-area-according-to-settlement-data-km2.txt"
    run:
        import rasterio

        with rasterio.open(input.rooftops[0], "r") as src:
            rooftops = src.read(1)
        with rasterio.open(input.sonnendach[0], "r") as src:
            sonnendach = src.read(1)
        rooftops[sonnendach != DATA_AVAILABLE] = 0
        rooftops[rooftops <= 0.01] = 0 # we ignore those in the analysis
        rooftop_area_km2 = (rooftops * RASTER_RESOLUTION_IN_M**2 / 1e6).sum()
        with open(output[0], "w") as f_out:
            f_out.write(f"{rooftop_area_km2}")


rule size_swiss_rooftops_according_to_sonnendach_data:
    message: "Select the size of rooftops from Sonnendach data."
    input: RAW_SONNENDACH_DATA
    output: "build/swiss/rooftop-areas-according-to-sonnendach-data.csv"
    shell:
        "ogr2ogr -select DF_UID,FLAECHE -f csv {output} {input} {LAYER_NAME}"


rule total_size_swiss_rooftops_according_to_sonnendach_data:
    message: "Sum the size of rooftops from Sonnendach data."
    input: rules.size_swiss_rooftops_according_to_sonnendach_data.output
    output: "build/swiss/total-rooftop-area-according-to-sonnendach-data-km2.txt"
    run:
        import pandas as pd

        sonnendach = pd.read_csv(input[0])
        total_size_km2 = sonnendach["FLAECHE"].sum() / 1e6
        with open(output[0], "w") as f_out:
            f_out.write(f"{total_size_km2}")


rule overestimation_settlement_data:
    message: "Determine the overestimation given in the settlement data."
    input:
        sonnendach = rules.total_size_swiss_rooftops_according_to_sonnendach_data.output,
        settlement = rules.total_size_swiss_rooftop_area_according_to_settlement_data.output
    output:
        "build/swiss/overestimation-settlement-data.txt"
    run:
        with open(input.sonnendach[0], "r") as f_in:
            sonnendach = float(f_in.read())
        with open(input.settlement[0], "r") as f_in:
            settlement = float(f_in.read())
        overestimation = settlement / sonnendach
        with open(output[0], "w") as f_out:
            f_out.write(f"{overestimation:.3f}")
