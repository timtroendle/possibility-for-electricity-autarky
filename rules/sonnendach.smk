"""Retrieve statistics of the sonnendach.ch dataset."""

URL_TO_STATISTICS = "https://zenodo.org/record/4091033/files/roof-statistics.csv?download=1"
URL_TO_TOTAL_SIZE = "https://zenodo.org/record/4091033/files/total-rooftop-area-km2.txt?download=1"
URL_TO_TOTAL_YIELD = "https://zenodo.org/record/4091033/files/total-yield-twh.txt?download=1"


rule total_size_swiss_rooftops_according_to_sonnendach_data:
    message: "Download the size of rooftops from Sonnendach data."
    output: "data/automatic/sonnendach/total-rooftop-area-km2.txt"
    shell:
        "curl -sLo {output} '{URL_TO_TOTAL_SIZE}'"


rule total_swiss_yield_according_to_sonnendach_data:
    message: "Download the yield of all available rooftops from Sonnendach data."
    output: "data/automatic/sonnendach/total-yield-twh.txt"
    shell:
        "curl -sLo {output} '{URL_TO_TOTAL_YIELD}'"


rule sonnendach_statistics:
    message: "Download statistics of roofs in Switzerland."
    output: "data/automatic/sonnendach/roof-statistics.csv",
    shell:
        "curl -sLo {output} '{URL_TO_STATISTICS}'"


rule sonnendach_statistics_publish:
    message: "Beautify sonnendach statistics for publication."
    input: rules.sonnendach_statistics.output
    output: "build/sonnendach/roof-statistics-publish.csv"
    run:
        import pandas as pd

        roof_categories = pd.read_csv(input[0])
        roof_categories.rename(
            columns={
                "orientation": "Orientation",
                "share_of_roof_areas": "Share of roof areas [%]",
                "average_tilt": "Average tilt [%]"
            },
            inplace=True
        )
        roof_categories["Share of roof areas [%]"] = roof_categories["Share of roof areas [%]"] * 100
        roof_categories.to_csv(output[0], header=True, index=False, float_format="%.1f")
