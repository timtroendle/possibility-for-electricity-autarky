"""This is a Snakemake file defining rules to retrieve raw data from online sources."""
import pycountry
from src.conversion import transform_bounds

PYTHON = "PYTHONPATH=./ python"
PYTHON_SCRIPT = "PYTHONPATH=./ python {input} {output}"
PYTHON_SCRIPT_WITH_CONFIG = PYTHON_SCRIPT + " {CONFIG_FILE}"

URL_LOAD = "https://data.open-power-system-data.org/time_series/2018-03-13/time_series_60min_stacked.csv"
URL_NUTS = "http://ec.europa.eu/eurostat/cache/GISCO/geodatafiles/NUTS_2013_01M_SH.zip"
URL_LAU = "http://ec.europa.eu/eurostat/cache/GISCO/geodatafiles/COMM-01M-2013-SH.zip"
URL_DEGURBA = "http://ec.europa.eu/eurostat/cache/GISCO/geodatafiles/DGURBA_2014_SH.zip"
URL_LAND_COVER = "http://due.esrin.esa.int/files/Globcover2009_V2.3_Global_.zip"
URL_PROTECTED_AREAS = "https://www.protectedplanet.net/downloads/WDPA_Jan2018?type=shapefile"
URL_CGIAR_TILE = "http://droppr.org/srtm/v4.1/6_5x5_TIFs/"
URL_GMTED_TILE = "https://edcintl.cr.usgs.gov/downloads/sciweb1/shared/topo/downloads/GMTED/Global_tiles_GMTED/075darcsec/mea/"
URL_GADM = "http://biogeo.ucdavis.edu/data/gadm2.8/gpkg"
URL_GADM = "https://biogeo.ucdavis.edu/data/gadm3.6/gpkg/"
URL_BATHYMETRIC = "https://www.ngdc.noaa.gov/mgg/global/relief/ETOPO1/data/bedrock/grid_registered/georeferenced_tiff/ETOPO1_Bed_g_geotiff.zip"
URL_WIND_CP = "https://www.renewables.ninja/static/downloads/ninja_europe_wind_v1.1.zip"
URL_PV_CP = "https://www.renewables.ninja/static/downloads/ninja_europe_pv_v1.1.zip"
URL_COUNTRY_SHAPES = "https://www.naturalearthdata.com/http//www.naturalearthdata.com/download/10m/cultural/ne_10m_admin_0_countries.zip"
URL_POP = "http://cidportal.jrc.ec.europa.eu/ftp/jrc-opendata/GHSL/GHS_POP_GPW4_GLOBE_R2015A/GHS_POP_GPW42015_GLOBE_R2015A_54009_250/V1-0/GHS_POP_GPW42015_GLOBE_R2015A_54009_250_v1_0.zip"


RAW_SETTLEMENT_DATA = "data/esm-100m-2017/ESM_class{esm_class}_100m.tif"
RAW_EEZ_DATA = "data/World_EEZ_v10_20180221/eez_v10.shp"
RAW_INDUSTRY_DATA = "data/electricity-intensive-industry/energy-intensive-industries.xlsx"

RESOLUTION_STUDY = (1 / 3600) * 10 # 10 arcseconds
RESOLUTION_SLOPE = (1 / 3600) * 3 # 3 arcseconds

SRTM_X_MIN = 34 # x coordinate of CGIAR tile raster
SRTM_X_MAX = 44
SRTM_Y_MIN = 1 # y coordinate of CGIAR tile raster
SRTM_Y_MAX = 8
GMTED_Y = ["50N", "70N"]
GMTED_X = ["030W", "000E", "030E"]


rule raw_load:
    message: "Download raw load."
    output:
        protected("data/automatic/raw-load-data.csv")
    shell:
        "curl -sLo {output} '{URL_LOAD}'"


rule electricity_demand_national:
    message: "Determine yearly demand per country."
    input:
        "src/process_load.py",
        rules.raw_load.output
    output:
        temp("build/electricity-demand-national.csv")
    shell:
        PYTHON_SCRIPT_WITH_CONFIG


rule raw_gadm_administrative_borders_zipped:
    message: "Download administrative borders for {wildcards.country_code} as zip."
    output: protected("data/automatic/raw-gadm/{country_code}.zip")
    shell: "curl -sLo {output} '{URL_GADM}/gadm36_{wildcards.country_code}_gpkg.zip'"


rule raw_gadm_administrative_borders:
    message: "Unzip administrative borders of {wildcards.country_code} as zip."
    input: "data/automatic/raw-gadm/{country_code}.zip"
    output: temp("data/automatic/raw-gadm/gadm36_{country_code}.gpkg")
    shell: "unzip -o {input} -d data/automatic/raw-gadm"


rule administrative_borders_gadm:
    message: "Merge administrative borders of all countries up to layer {params.max_layer_depth}."
    input:
        "src/gadm.py",
        ["data/automatic/raw-gadm/gadm36_{}.gpkg".format(country_code)
            for country_code in [pycountry.countries.lookup(country).alpha_3
                                 for country in config['scope']['countries']]
         ]
    params: max_layer_depth = 3
    output: "build/administrative-borders-gadm.gpkg"
    shell:
        PYTHON + " {input} {params.max_layer_depth} {output} {CONFIG_FILE}"


rule raw_nuts_units_zipped:
    message: "Download units as zip."
    output:
        protected("data/automatic/raw-nuts-units.zip")
    shell:
        "curl -sLo {output} '{URL_NUTS}'"


rule administrative_borders_nuts:
    message: "Normalise NUTS administrative borders."
    input:
        src = "src/nuts.py",
        zip = rules.raw_nuts_units_zipped.output
    output:
        "build/administrative-borders-nuts.gpkg"
    shadow: "full"
    shell:
        """
        unzip {input.zip} -d ./build
        {PYTHON} {input.src} merge ./build/NUTS_2013_01M_SH/data/NUTS_RG_01M_2013.shp \
        ./build/NUTS_2013_01M_SH/data/NUTS_AT_2013.dbf ./build/raw-nuts.gpkg
        {PYTHON} {input.src} normalise ./build/raw-nuts.gpkg {output} {CONFIG_FILE}
        """


rule raw_lau_units_zipped:
    message: "Download LAU units as zip."
    output:
        protected("data/automatic/raw-lau-units.zip")
    shell:
        "curl -sLo {output} '{URL_LAU}'"


rule administrative_borders_lau:
    message: "Normalise LAU administrative borders."
    input:
        src = "src/lau.py",
        zip = rules.raw_lau_units_zipped.output
    output:
        "build/administrative-borders-lau.gpkg"
    shadow: "full"
    shell:
        """
        unzip {input.zip} -d ./build
        {PYTHON} {input.src} merge ./build/COMM_01M_2013_SH/data/COMM_RG_01M_2013.shp \
        ./build/COMM_01M_2013_SH/data/COMM_AT_2013.dbf ./build/raw-lau.gpkg
        {PYTHON} {input.src} identify ./build/raw-lau.gpkg ./build/raw-lau-identified.gpkg
        {PYTHON} {input.src} normalise ./build/raw-lau-identified.gpkg {output} {CONFIG_FILE}
        """


rule raw_urbanisation_zipped:
    message: "Download DEGURBA units as zip."
    output:
        protected("data/automatic/raw-degurba-units.zip")
    shell:
        "curl -sLo {output} '{URL_DEGURBA}'"


rule lau2_urbanisation_degree:
    message: "Urbanisation degrees on LAU2 level."
    input:
        src = "src/lau.py",
        lau2 = rules.raw_lau_units_zipped.output,
        degurba = rules.raw_urbanisation_zipped.output
    output:
        "build/administrative-borders-lau-urbanisation.csv"
    shadow: "full"
    shell:
        """
        unzip {input.lau2} -d ./build
        unzip {input.degurba} -d ./build
        {PYTHON} {input.src} merge ./build/COMM_01M_2013_SH/data/COMM_RG_01M_2013.shp \
        ./build/COMM_01M_2013_SH/data/COMM_AT_2013.dbf ./build/raw-lau.gpkg
        {PYTHON} {input.src} degurba ./build/raw-lau.gpkg ./build/DGURBA_2014_SH/data/DGURBA_RG_01M_2014.shp {output}
        """


rule raw_land_cover_zipped:
    message: "Download land cover data as zip."
    output: protected("data/automatic/raw-globcover2009.zip")
    shell: "curl -sLo {output} '{URL_LAND_COVER}'"


rule raw_land_cover:
    message: "Extract land cover data as zip."
    input: rules.raw_land_cover_zipped.output
    output: temp("build/GLOBCOVER_L4_200901_200912_V2.3.tif")
    shadow: "full"
    shell: "unzip {input} -d ./build/"


rule raw_protected_areas_zipped:
    message: "Download protected areas data as zip."
    output: protected("data/automatic/raw-wdpa.zip")
    shell: "curl -sLo {output} -H 'Referer: {URL_PROTECTED_AREAS}' {URL_PROTECTED_AREAS}"


rule raw_protected_areas:
    message: "Extract protected areas data as zip."
    input: rules.raw_protected_areas_zipped.output
    output:
        polygons = "build/raw-wdpa-jan2018/WDPA_Jan2018-shapefile-polygons.shp",
        points = "build/raw-wdpa-jan2018/WDPA_Jan2018-shapefile-points.shp"
    shell: "unzip {input} -d build/raw-wdpa-jan2018"


rule raw_srtm_elevation_tile_zipped:
    message: "Download SRTM elevation data tile (x={wildcards.x}, y={wildcards.y}) from CGIAR."
    output:
        protected("data/automatic/raw-srtm/srtm_{x}_{y}.zip")
    shell:
        """
        curl -sLo {output} '{URL_CGIAR_TILE}/srtm_{wildcards.x}_{wildcards.y}.zip'
        """


rule raw_srtm_elevation_tile:
    message: "Unzip SRTM elevation data tile (x={wildcards.x}, y={wildcards.y})."
    input:
        "data/automatic/raw-srtm/srtm_{x}_{y}.zip"
    output:
        temp("build/srtm_{x}_{y}.tif")
    shadow: "full"
    shell:
        "unzip {input} -d build"


rule raw_srtm_elevation_data:
    message: "Merge all SRTM elevation data tiles."
    input:
        ["build/srtm_{x:02d}_{y:02d}.tif".format(x=x, y=y)
         for x in range(SRTM_X_MIN, SRTM_X_MAX + 1)
         for y in range(SRTM_Y_MIN, SRTM_Y_MAX + 1)
         if not (x is 34 and y in [3, 4, 5, 6])] # these tiles do not exist
    output:
        temp("build/raw-srtm-elevation-data.tif")
    shell:
        "rio merge {input} {output} --force-overwrite"


rule raw_gmted_elevation_tile:
    message: "Download GMTED elevation data tile."
    output:
        protected("data/automatic/raw-gmted/raw-gmted-{y}-{x}.tif")
    run:
        url = "{base_url}/{x_inverse}/{y}{x}_20101117_gmted_mea075.tif".format(**{
            "base_url": URL_GMTED_TILE,
            "x": wildcards.x,
            "y": wildcards.y,
            "x_inverse": wildcards.x[-1] + wildcards.x[:-1]
        })
        shell("curl -sLo {output} '{url}'".format(**{"url": url, "output": output}))


rule raw_gmted_elevation_data:
    message: "Merge all GMTED elevation data tiles."
    input:
        ["data/automatic/raw-gmted/raw-gmted-{y}-{x}.tif".format(x=x, y=y)
         for x in GMTED_X
         for y in GMTED_Y
         ]
    output:
        temp("build/raw-gmted-elevation-data.tif")
    shell:
        "rio merge {input} {output} --force-overwrite"


rule raw_bathymetry_zipped:
    message: "Download bathymetric data as zip."
    output: protected("data/automatic/raw-bathymetric.zip")
    shell: "curl -sLo {output} '{URL_BATHYMETRIC}'"


rule raw_bathymetry:
    message: "Extract bathymetric data from zip."
    input: rules.raw_bathymetry_zipped.output
    output: temp("build/ETOPO1_Bed_g_geotiff.tif")
    shell: "unzip {input} -d ./build/"


rule raw_wind_capacity_factors_zipped:
    message: "Download national wind capacity factors as zip."
    output: protected("data/automatic/raw-wind-capacity-factors.zip")
    shell: "curl -sLo {output} '{URL_WIND_CP}'"


rule raw_pv_capacity_factors_zipped:
    message: "Download national pv capacity factors as zip."
    output: protected("data/automatic/raw-pv-capacity-factors.zip")
    shell: "curl -sLo {output} '{URL_PV_CP}'"


rule raw_wind_capacity_factors:
    message: "Extract national wind capacity factors from zip."
    input: rules.raw_wind_capacity_factors_zipped.output
    shadow: "full"
    output: temp("build/ninja_wind_europe_v1.1_current_on-offshore.csv")
    shell: "unzip {input} -d ./build"


rule raw_pv_capacity_factors:
    message: "Extract national pv capacity factors from zip."
    input: rules.raw_pv_capacity_factors_zipped.output
    shadow: "full"
    output: temp("build/ninja_pv_europe_v1.1_sarah.csv")
    shell: "unzip {input} -d ./build"


rule elevation_in_europe:
    message: "Merge SRTM and GMTED elevation data and warp/clip to Europe using {threads} threads."
    input:
        gmted = rules.raw_gmted_elevation_data.output,
        srtm = rules.raw_srtm_elevation_data.output
    output:
        "build/elevation-europe.tif"
    params:
        srtm_bounds = "{x_min} {y_min} {x_max} 60".format(**config["scope"]["bounds"]),
        gmted_bounds = "{x_min} 59.5 {x_max} {y_max}".format(**config["scope"]["bounds"])
    threads: config["snakemake"]["max-threads"]
    shell:
        """
        rio clip --bounds {params.srtm_bounds} {input.srtm} -o build/tmp-srtm.tif
        rio clip --bounds {params.gmted_bounds} {input.gmted} -o build/tmp-gmted.tif
        rio warp build/tmp-gmted.tif -o build/tmp-gmted2.tif -r {RESOLUTION_SLOPE} \
        --resampling nearest --threads {threads}
        rio merge build/tmp-srtm.tif build/tmp-gmted2.tif {output}
        rm build/tmp-gmted.tif
        rm build/tmp-gmted2.tif
        rm build/tmp-srtm.tif
        """


rule land_cover_in_europe:
    message: "Clip land cover data to Europe."
    input: rules.raw_land_cover.output
    output: "build/land-cover-europe.tif"
    params: bounds = "{x_min} {y_min} {x_max} {y_max}".format(**config["scope"]["bounds"])
    shell: "rio clip {input} {output} --bounds {params.bounds}"


rule slope_in_europe:
    message: "Calculate slope and warp to resolution of study using {threads} threads."
    input:
        elevation = rules.elevation_in_europe.output,
        land_cover = rules.land_cover_in_europe.output
    output:
        "build/slope-europe.tif"
    threads: config["snakemake"]["max-threads"]
    shell:
        """
        gdaldem slope -s 111120 -compute_edges {input.elevation} build/slope-temp.tif
        rio warp build/slope-temp.tif -o {output} --like {input.land_cover} \
        --resampling max --threads {threads}
        rm build/slope-temp.tif
        """


rule protected_areas_points_to_circles:
    message: "Estimate shape of protected areas available as points only."
    input:
        "src/estimate_protected_shapes.py",
        rules.raw_protected_areas.output.points
    output:
        temp("build/protected-areas-points-as-circles.geojson")
    shell:
        PYTHON_SCRIPT_WITH_CONFIG


rule protected_areas_in_europe:
    message: "Rasterise protected areas data and clip to Europe."
    input:
        polygons = rules.raw_protected_areas.output.polygons,
        points = rules.protected_areas_points_to_circles.output,
        land_cover = rules.land_cover_in_europe.output
    output:
        "build/protected-areas-europe.tif"
    benchmark:
        "build/rasterisation-benchmark.txt"
    shell:
        # fio cat below should use a bounding box to not forward polygons outside
        # the study area. This would increase the performance drastically. Doing so
        # is blocked by bug https://github.com/Toblerity/Fiona/issues/543
        #
        # The filter is in accordance to the way UNEP-WCMC calculates statistics:
        # https://www.protectedplanet.net/c/calculating-protected-area-coverage
        """
        fio cat --rs {input.points} {input.polygons} | \
        fio filter "f.properties.STATUS in ['Designated', 'Inscribed', 'Established'] and \
        f.properties.DESIG_ENG != 'UNESCO-MAB Biosphere Reserve'" | \
        fio collect --record-buffered | \
        rio rasterize --like {input.land_cover} \
        --default-value 255 --all_touched -f "GTiff" --co dtype=uint8 -o {output}
        """


rule settlements:
    message: "Warp settlement data to CRS of study using {threads} threads."
    input:
        class50 = RAW_SETTLEMENT_DATA.format(esm_class="50"),
        class40 = RAW_SETTLEMENT_DATA.format(esm_class="40"),
        class41 = RAW_SETTLEMENT_DATA.format(esm_class="41"),
        class45 = RAW_SETTLEMENT_DATA.format(esm_class="45"),
        class30 = RAW_SETTLEMENT_DATA.format(esm_class="30"),
        class35 = RAW_SETTLEMENT_DATA.format(esm_class="35"),
        reference = rules.land_cover_in_europe.output
    output:
        buildings = "build/esm-class50-buildings.tif",
        urban_greens = "build/esm-class404145-urban-greens.tif",
        built_up = "build/esm-class303550-built-up.tif"
    threads: config["snakemake"]["max-threads"]
    shadow: "full"
    shell:
        """
        rio warp {input.class50} -o {output.buildings} \
        --like {input.reference} --threads {threads} --resampling bilinear --co compress=LZW
        rio warp {input.class40} -o build/esm-class40.tif \
        --like {input.reference} --threads {threads} --resampling bilinear --co compress=LZW
        rio warp {input.class41} -o build/esm-class41.tif \
        --like {input.reference} --threads {threads} --resampling bilinear --co compress=LZW
        rio warp {input.class45} -o build/esm-class45.tif \
        --like {input.reference} --threads {threads} --resampling bilinear --co compress=LZW
        rio warp {input.class30} -o build/esm-class30.tif \
        --like {input.reference} --threads {threads} --resampling bilinear --co compress=LZW
        rio warp {input.class35} -o build/esm-class35.tif \
        --like {input.reference} --threads {threads} --resampling bilinear --co compress=LZW
        rio calc "(+ (+ (read 1) (read 2)) (read 3))" \
        build/esm-class40.tif build/esm-class41.tif build/esm-class45.tif -o {output.urban_greens}
        rio calc "(+ (+ (read 1) (read 2)) (read 3))" \
        {output.buildings} build/esm-class30.tif build/esm-class35.tif -o {output.built_up}
        """


rule bathymetry_in_europe:
    message: "Clip bathymetric data to study area and warp to study resolution."
    input:
        bathymetry = rules.raw_bathymetry.output,
        reference = rules.land_cover_in_europe.output
    output:
        "build/bathymetry-in-europe.tif"
    shell:
        """
        rio warp {input.bathymetry} -o {output} --like {input.reference} --resampling min
        """


rule eez_in_europe:
    message: "Clip exclusive economic zones to study area."
    input: RAW_EEZ_DATA
    output: "build/eez-in-europe.geojson"
    params:
        bounds="{x_min},{y_min},{x_max},{y_max}".format(**config["scope"]["bounds"]),
        countries=",".join(["'{}'".format(country) for country in config["scope"]["countries"]])
    shell:
        """
        fio cat --bbox {params.bounds} {input}\
        | fio filter "f.properties.Territory1 in [{params.countries}]"\
        | fio collect > {output}
        """


rule industry:
    message: "Preprocess data on electricity intensive industry."
    input:
        "src/industry.py",
        RAW_INDUSTRY_DATA
    output:
        "build/industrial-load.geojson"
    shell:
        PYTHON_SCRIPT


rule raw_country_shapes:
    message: "Download raw shapes of countries worldwide."
    output:
        protected("data/automatic/raw-country-shapes.zip")
    shell:
        "curl -sLo {output} '{URL_COUNTRY_SHAPES}'"


rule country_shapes:
    message: "Converting country shapes from shape file to GeoJSON."
    input: rules.raw_country_shapes.output
    output: "build/worldwide-countries.geojson"
    shadow: "full"
    shell:
        """
        unzip {input} -d ./build
        fio dump build/ne_10m_admin_0_countries.shp > {output}
        """


rule raw_population_zipped:
    message: "Download population data."
    output:
        protected("data/automatic/raw-population-data.zip")
    shell:
        "curl -sLo {output} '{URL_POP}'"


rule raw_population:
    message: "Extract population data as zip."
    input: rules.raw_population_zipped.output
    output: temp("build/GHS_POP_GPW42015_GLOBE_R2015A_54009_250_v1_0.tif")
    shadow: "full"
    shell:
        """
        unzip {input} -d ./build/
        mv build/GHS_POP_GPW42015_GLOBE_R2015A_54009_250_v1_0/GHS_POP_GPW42015_GLOBE_R2015A_54009_250_v1_0.tif {output}
        """


rule population_in_europe:
    message: "Clip population data to bounds of study."
    input:
        population = rules.raw_population.output,
    output:
        "build/population-europe.tif"
    params:
        bounds = "{} {} {} {}".format(*transform_bounds(
            **config["scope"]["bounds"],
            from_epsg=config["crs"],
            to_epsg="ESRI:54009"
        ))
    shell:
        """
        rio clip --bounds {params.bounds} --co compress=LZW {input.population} -o {output}
        """
