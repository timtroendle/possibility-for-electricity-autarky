"""These rules analyse the Swiss Sonnendach dataset.

There are two types of information extracted from this dataset:

(1) Statistics on the types of roofs: flat / tilted, orientation, and tilt. This is used to simulate
    the yield of roof-mounted PV.
(2) A correction (multiplication) factor that relates area of building foot prints as identified
    from ESM to area of rooftops usable for PV.
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


rule total_size_swiss_building_footprints_according_to_settlement_data:
    message: "Sum the size of building footprints from settlement data."
    input:
        building_footprints = rules.settlements.output.buildings,
        eligibility = "build/eligible-land.tif",
        countries = rules.administrative_borders_nuts.output[0]
    output:
        "build/swiss/building-footprints-according-to-settlement-data-km2.txt"
    run:
        import rasterio
        import fiona
        from rasterstats import zonal_stats
        import pandas as pd
        import geopandas as gpd

        from src.eligibility import Eligibility
        from src.conversion import area_in_squaremeters

        with rasterio.open(input.eligibility, "r") as f_eligibility:
            eligibility = f_eligibility.read(1)
        with rasterio.open(input.building_footprints, "r") as f_building_share:
            building_share = f_building_share.read(1)
            affine = f_building_share.affine
        building_share[eligibility != Eligibility.ROOFTOP_PV] = 0

        with fiona.open(input.countries, "r", layer="nuts0") as src:
            zs = zonal_stats(
                vectors=src,
                raster=building_share,
                affine=affine,
                stats="mean",
                nodata=-999
            )
            building_share = pd.Series(
                index=[feat["properties"]["id"] for feat in src],
                data=[stat["mean"] for stat in zs]
            )
        building_footprint_km2 = area_in_squaremeters(gpd.read_file(input.countries).set_index("id")).div(1e6) * building_share
        swiss_building_footprint = building_footprint_km2.loc["CH"]
        with open(output[0], "w") as f_out:
            f_out.write(f"{swiss_building_footprint}")


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


rule correction_factor_building_footprint_to_available_rooftop:
    message: "Determine the factor that maps from building footprints to available rooftop area for CH."
    input:
        rooftops = rules.total_size_swiss_rooftops_according_to_sonnendach_data.output[0],
        building_footprints = rules.total_size_swiss_building_footprints_according_to_settlement_data.output[0]
    output:
        "build/swiss/ratio-esm-available.txt"
    run:
        with open(input.rooftops, "r") as f_in:
            rooftops = float(f_in.read())
        with open(input.building_footprints, "r") as f_in:
            building_footprints = float(f_in.read())
        ratio = rooftops / building_footprints
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
                "orientation": "Orientation",
                "share of roof areas": "Share of roof areas [%]",
                "tilt": "Average tilt [%]"
            },
            inplace=True
        )
        roof_categories["Share of roof areas [%]"] = roof_categories["Share of roof areas [%]"] * 100
        roof_categories.to_csv(output.publish, header=True, index=False, float_format="%.1f")


rule pv_simulation_parameters:
    message: "Create input parameters for simulation of photovoltaics."
    input:
        roof_categories = rules.sonnendach_statistics.output,
        units = "build/regional/units.geojson"
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
        units = gpd.read_file(input.units).set_index("id")
        lat_long = pd.DataFrame(
            index=units.index,
            data={
                "lat": units.centroid.map(lambda point: point.y),
                "long": units.centroid.map(lambda point: point.x)
            }
        )

        index = pd.MultiIndex.from_product((units.index, roof_categories.index), names=["id", "roof_cat_id"])
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
