"""These rules analyse the Swiss Sonnendach dataset.

There are two types of statistical information extracted from this dataset:

(1) Statistics on the types of roofs: flat / tilted, orientation, and tilt. This is used to simulate
    the yield of roof-mounted PV.
(2) Total estimation of available Swiss roofs and their PV potential.
"""

import sys; sys.path.append(os.getcwd()) # this is necessary to be able to import "src", not sure why
RAW_SONNENDACH_DATA = "data/sonnendach/SOLKAT_20180827.gdb/"
RAW_BUILDING_CATEGORIES = "data/gwr/Table_GEB-01.txt"
LAYER_NAME = "SOLKAT_CH_DACH"
DATA_AVAILABLE = 255
RASTER_RESOLUTION_IN_M = 100
MIN_ROOF_SIZE = 10 # @BFE:2016 "Berechnung Potential in Gemeinden"
MAX_FLAT_TILT = 10 # @BFE:2016 "Berechnung Potential in Gemeinden"
SINGLE_FAMILY_BUILDING = 1021 # GKAT @BFE:2016 "Berechnung Potential in Gemeinden"
MULTI_FAMILY_BUILDING = 1025 # GKAT @BFE:2016 "Berechnung Potential in Gemeinden"
FALLBACK_BUILDING_TYPE = 1010 # GKAT @BFE:2016 "Berechnung Potential in Gemeinden"
THEIR_PERFORMANCE_RATIO = 0.8 # @Klauser:2016 "Solarpotentialanalyse für Sonnendach.ch"
THEIR_EFFICIENCY = 0.17 # @Klauser:2016 "Solarpotentialanalyse für Sonnendach.ch"


rule all_sonnendach:
    input:
        "build/swiss/total-rooftop-area-according-to-sonnendach-data-km2.txt",
        "build/swiss/total-yield-according-to-sonnendach-data-twh.txt",
        "build/swiss/roof-statistics.csv",
        "build/swiss/roof-statistics-publish.csv"


rule building_categories:
    message: "Preprocess the building category data."
    input:
        RAW_BUILDING_CATEGORIES
    output:
        "build/swiss/building-categories.csv"
    run:
        import pandas as pd
        categories = pd.read_table(
            input[0],
            header=None,
            usecols=[0, 11],
            names=["EGID", "GKAT"],
            index_col=0
        )
        categories.to_csv(output[0], index=True, header=True)


rule sonnendach_rooftop_data:
    message: "Extract necessary data from sonnendach to create a statistical model."
    input: RAW_SONNENDACH_DATA
    output:
        "build/swiss/roofs-without-geometry.csv"
    conda: "../envs/default.yaml"
    shell:
        "ogr2ogr -dialect sqlite -f csv \
        -sql 'SELECT DF_UID, GWR_EGID, FLAECHE, AUSRICHTUNG, NEIGUNG, MSTRAHLUNG, GSTRAHLUNG FROM {LAYER_NAME}' \
        {output} {input}"


rule total_size_swiss_rooftops_according_to_sonnendach_data:
    message: "Sum the size of rooftops from Sonnendach data."
    input:
        sonnendach = rules.sonnendach_rooftop_data.output,
        categories = rules.building_categories.output
    output: "build/swiss/total-rooftop-area-according-to-sonnendach-data-km2.txt"
    run:
        import pandas as pd


        def theoretic_to_actual_area(row):
            # method and values from @BFE:2016 "Berechnung Potential in Gemeinden"
            if row.NEIGUNG <= 10:
                return row.FLAECHE * _theoretic_to_actual_area_flat_roofs_factor(row)
            else:
                return row.FLAECHE * 0.7


        def _theoretic_to_actual_area_flat_roofs_factor(row):
            if row.GKAT == SINGLE_FAMILY_BUILDING:
                return 0.7
            elif row.GKAT == MULTI_FAMILY_BUILDING:
                if row.FLAECHE < 1000:
                    return 0.6 * 0.7
                else:
                    return 0.6 * 0.8
            else:
                if row.FLAECHE < 1000:
                    return 0.7
                else:
                    return 0.8

        sonnendach = pd.read_csv(input.sonnendach[0])
        sonnendach = sonnendach.merge(
            pd.read_csv(input.categories[0], index_col=0),
            left_on="GWR_EGID",
            right_index=True,
            how="left"
        )
        sonnendach["GKAT"].fillna(value=FALLBACK_BUILDING_TYPE, inplace=True)
        sonnendach["GKAT"] = sonnendach["GKAT"].astype(pd.np.int16)
        sonnendach = sonnendach[sonnendach.FLAECHE >= MIN_ROOF_SIZE]
        total_size_km2 = sonnendach.apply(theoretic_to_actual_area, axis=1).sum() / 1e6
        with open(output[0], "w") as f_out:
            f_out.write(f"{total_size_km2}")


rule total_swiss_yield_according_to_sonnendach_data:
    message: "Sum the yield of all available rooftops from Sonnendach data."
    input:
        sonnendach = rules.sonnendach_rooftop_data.output,
        categories = rules.building_categories.output
    output: "build/swiss/total-yield-according-to-sonnendach-data-twh.txt"
    run:
        import pandas as pd


        def theoretic_to_actual_radiation(row):
            # method and values from @BFE:2016 "Berechnung Potential in Gemeinden"
            if row.NEIGUNG <= 10:
                return row.GSTRAHLUNG * _theoretic_to_actual_area_flat_roofs_factor(row)
            else:
                return row.GSTRAHLUNG * 0.7


        def _theoretic_to_actual_area_flat_roofs_factor(row):
            if row.GKAT == SINGLE_FAMILY_BUILDING:
                return 0.7
            elif row.GKAT == MULTI_FAMILY_BUILDING:
                if row.FLAECHE < 1000:
                    return 0.6 * 0.7
                else:
                    return 0.6 * 0.8
            else:
                if row.FLAECHE < 1000:
                    return 0.7
                else:
                    return 0.8

        sonnendach = pd.read_csv(input.sonnendach[0])
        sonnendach = sonnendach.merge(
            pd.read_csv(input.categories[0], index_col=0),
            left_on="GWR_EGID",
            right_index=True,
            how="left"
        )
        sonnendach["GKAT"].fillna(value=FALLBACK_BUILDING_TYPE, inplace=True)
        sonnendach["GKAT"] = sonnendach["GKAT"].astype(pd.np.int16)
        sonnendach.loc[sonnendach.FLAECHE < MIN_ROOF_SIZE, "GSTRAHLUNG"] = 0
        total_radiation_kwh = sonnendach.apply(theoretic_to_actual_radiation, axis=1).sum()
        total_yield_twh = total_radiation_kwh * THEIR_EFFICIENCY * THEIR_PERFORMANCE_RATIO / 1e9
        with open(output[0], "w") as f_out:
            f_out.write(f"{total_yield_twh}")


rule sonnendach_statistics:
    message: "Create statistics of roofs in Switzerland."
    input: rules.sonnendach_rooftop_data.output
    output:
        raw = "build/swiss/roof-statistics.csv",
        publish = "build/swiss/roof-statistics-publish.csv"
    run:
        import pandas as pd
        data = pd.read_csv(input[0], index_col=0)
        data.rename(columns={"AUSRICHTUNG": "orientation", "NEIGUNG": "tilt", "FLAECHE": "area"}, inplace=True)
        data = data[data.area > MIN_ROOF_SIZE]
        data["share of roof areas"] = data.area.transform(lambda x: x / x.sum())
        orientation_categories = pd.cut(
            data["orientation"],
            bins=[-180, -135, -45, 45, 135, 180],
            include_lowest=True,
            labels=["N", "E", "S", "W", "N2"]
        ).replace({"N2": "N"})
        orientation_categories[data.tilt <= MAX_FLAT_TILT] = "flat"
        tilt_categories = pd.Series(pd.np.nan, index=data.index)
        tilt_categories[orientation_categories == "flat"] = "0"
        for orientation_category in ["N", "S", "E", "W"]:
            mask = (orientation_categories == orientation_category)
            tilt_categories[mask] = pd.qcut(data.tilt[mask], q=4)
        assert not tilt_categories.isnull().any()

        roof_categories = data.groupby([orientation_categories, tilt_categories]).agg(
            {"share of roof areas": "sum", "tilt": "mean"}
        )
        roof_categories.loc["flat", "tilt"] = 0.0
        roof_categories = roof_categories.reset_index()[["orientation", "tilt", "share of roof areas"]]
        roof_categories.to_csv(output.raw, header=True, index=False)
        roof_categories.rename(
            columns={
                "orientation": "Orientation",
                "share of roof areas": "Share of roof areas [%]",
                "tilt": "Average tilt [%]"
            },
            inplace=True
        )
        roof_categories["Share of roof areas [%]"] = roof_categories["Share of roof areas [%]"] * 100
        roof_categories.to_csv(output.publish, header=True, index=False, float_format="%.1f")
