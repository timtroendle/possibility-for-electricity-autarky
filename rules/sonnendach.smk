"""These rules analyse statistics of the Swiss Sonnendach dataset."""

import sys; sys.path.append(os.getcwd()) # this is necessary to be able to import "src", not sure why
RAW_SONNENDACH_DATA = "data/sonnendach/SOLKAT_R1-R9_20180418.gdb/"
RAW_BUILDING_CATEGORIES = "data/gwr/Table_GEB-01.txt"
LAYER_NAME = "SOLKAT_CH_DACH"
DATA_AVAILABLE = 255
RASTER_RESOLUTION_IN_M = 100
MIN_ROOF_SIZE = 10 # @BFE:2016 "Berechnung Potential in Gemeinden"
MAX_FLAT_TILT = 10 # @BFE:2016 "Berechnung Potential in Gemeinden"
SINGLE_FAMILY_BUILDING = 1021 # GKAT @BFE:2016 "Berechnung Potential in Gemeinden"
MULTI_FAMILY_BUILDING = 1025 # GKAT @BFE:2016 "Berechnung Potential in Gemeinden"
FALLBACK_BUILDING_TYPE = 1010 # GKAT @BFE:2016 "Berechnung Potential in Gemeinden"
CONFIG_FILE = "config/default.yaml"

configfile: CONFIG_FILE


rule all_sonnendach:
    input:
        "build/swiss/pv-simulation-parameters.csv"


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
    shell:
        "ogr2ogr -dialect sqlite -f csv \
        -sql 'SELECT DF_UID, GWR_EGID, FLAECHE, AUSRICHTUNG, NEIGUNG, MSTRAHLUNG, GSTRAHLUNG FROM {LAYER_NAME}' \
        {output} {input}"


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
        rooftops = rules.settlements.output.buildings,
        sonnendach = rules.rasterise_sonnendach.output
    output:
        "build/swiss/swiss-rooftops.tif"
    shell:
        "rio warp {input.rooftops} -o {output} --like {input.sonnendach} --resampling average"


rule total_size_swiss_rooftop_area_according_to_settlement_data:
    message: "Sum the size of roofs from the settlement data on the spatial extend of the sonnendach data."
    input:
        rooftops = rules.swiss_rooftops_from_settlement_data.output,
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


rule ratio_esm_estimation_available:
    message: "Determine the share of roof areas from settlement data actually available."
    input:
        sonnendach = rules.total_size_swiss_rooftops_according_to_sonnendach_data.output,
        settlement = rules.total_size_swiss_rooftop_area_according_to_settlement_data.output
    output:
        "build/swiss/ratio-esm-available.txt"
    run:
        with open(input.sonnendach[0], "r") as f_in:
            sonnendach = float(f_in.read())
        with open(input.settlement[0], "r") as f_in:
            settlement = float(f_in.read())
        ratio = sonnendach / settlement
        with open(output[0], "w") as f_out:
            f_out.write(f"{ratio:.3f}")


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
                "share of roof areas": "share of roof areas [%]",
                "tilt": "average tilt [%]"
            },
            inplace=True
        )
        roof_categories["share of roof areas [%]"] = roof_categories["share of roof areas [%]"] * 100
        roof_categories.to_csv(output.publish, header=True, index=False, float_format="%.1f")


rule pv_simulation_parameters:
    message: "Create input parameters for simulation of photovoltaics."
    input:
        roof_categories = rules.sonnendach_statistics.output,
        regions = "build/subnational/regions.geojson"
    output:
        "build/swiss/pv-simulation-parameters.csv"
    run:
        import pandas as pd
        import geopandas as gpd

        def orientation_to_azimuth(orientation):
            if orientation == "S":
                return 180
            elif orientation == "W":
                return -90
            elif orientation == "N":
                return 0
            elif orientation == "E":
                return 90
            elif orientation == "flat":
                return 180
            else:
                raise ValueError()

        def optimal_tilt(latitude):
            # based on @Jacobson:2018
            optimal_tilt = 1.3793 + latitude * (1.2011 + latitude * (-0.014404 + latitude * 0.000080509))
            assert 90 > optimal_tilt >= 0
            return optimal_tilt

        roof_categories = pd.read_csv(input.roof_categories[0])
        regions = gpd.read_file(input.regions).set_index("id")
        lat_long = pd.DataFrame(
            index=regions.index,
            data={
                "lat": regions.centroid.map(lambda point: point.y),
                "long": regions.centroid.map(lambda point: point.x)
            }
        )

        index = pd.MultiIndex.from_product((regions.index, roof_categories.index), names=["id", "roof_cat_id"])
        data = pd.DataFrame(index=index).reset_index()
        data = data.merge(roof_categories, left_on="roof_cat_id", right_index=True).drop(columns=["share of roof areas"])
        data = data.merge(lat_long, left_on="id", right_index=True)
        data["azim"] = data["orientation"].map(orientation_to_azimuth)
        data["site_id"] = data.apply(
            lambda row: "{}_{}_{}".format(row.id, row.orientation, round(row.tilt)),
            axis=1
        )
        flat_mask = data["orientation"] == "flat"
        data.loc[flat_mask, "tilt"] = data.loc[flat_mask, "lat"].map(optimal_tilt)
        data[["site_id", "lat", "long", "tilt", "azim"]].sort_index().to_csv(output[0], header=True, index=False)
