# Introduction

This analysis assesses the sufficiency of eligible land for renewable power units in Europe. It does so by first determining the land that is eligible for renewable power generation through an analysis of geospatial data on a high spatial resolution. Second, it estimates the electrical energy that can be harvested on the eligible land. And third, it compares this amount to the local demand for electrical energy. The renewable power potential is called sufficient whenever it exceeds the demand, otherwise it is called insufficient. The analysis is performed on different geographical scales where on each scale each region is considered autarkic in terms of electrical energy.

This document first describes the method and data analysis steps in details and then presents and discusses results.

# Method

The method is an analysis of different data sources, mainly geospatial data and time series. In the following, I will describe first the input data that is used, and second the analysis steps in more detail.

## Input data

SRTM elevation data

:   Digital elevation data for almost the entire globe, originally collected by NASA. The resolution is 3 arcseconds, but poles including large parts of Scandinavia are missing. In here I am using a processed version provided by CGIAR in which artefacts and missing values have been treated [@Reuter:2007].

GMTED elevation data

:   The missing globes of the SRTM elevation data makes another data set necessary for the Northern part of Europe. I am using the GMTED elevation data, which has a resolution of 7.5 arcseconds [@Danielson:2011]. It is composed of different sources and due to the low resolution I will use it only for the parts missing in the SRTM data set.

GlobCover 2009 -- land cover data

:   GlobCover2009 is a land cover data set provided by the European Space Agency which determines land cover worldwide with a resolution of 10 arcseconds [@EuropeanSpaceAgency:2010].

World Database on Protected Areas

:   The world database on protected areas [@UNEP-WCMC:2017] maps areas that are protected by national law. It is provided as a vector database.

Gridded Population of the World v4

:   The gridded population of the world data base provides an estimate of the spatial distribution of the worlds population in 2020 with a resolution of 30 arcseconds [@CIESIN:2016; @Doxsey-Whitfield:2015]. It is based on national censuses and population registers.

NUTS

:   Eurostat's Nomenclature of territorial units for statistics provides the basis by which Europe is divided into regions in this analysis [@eurostat:2015].

GADM

:   The global administrative areas database [@GADM:2015] is used to amend NUTS data.

Electricity demand

:   ENTSO-e provides historical load time series for most countries in Europe with a resolution of 1 hour. In this analysis I will use the processed version provided by @OpenPowerSystemData:2017.


## Analysis steps

### Land cover data

The GlobCover2009 land cover data is provided in the coordinate reference system and resolution that is used in this study as well. It is thus clipped to match the study area only. In the following, the land cover data is used as a template for other raster data.

### Protected areas data

The protected areas database is provided in two files: a shapefile including polygons of protected areas for all areas where the shape is known, and a shapefile including the centroids of all other areas as points. The polygons are used as provided, but for the centroids their shape is estimated. This is done by simply drawing a circle with the correct size around the centroid. The provider of the database, UNEP-WCMC, suggests and uses the same estimation method. All polygons including the estimated ones are rasterised to prepare them for the next step. The resolution, shape, and coordinate reference system of the processed land cover data is used as a template.

### Slope data

The slope in Europe is calculated from digital elevation data. The main source is SRTM, but for the Northern part of Europe, GMTED is used as SRTM is not available here. After merging the two data sets and clipping them to the study area, the slope is calculated using `gdaldem slope`. The resulting slope raster data has the resolution of the SRTM data of 3 arcseconds. It is downsampled to 10 arcseconds by taking the maximum slope in the 10 arcsecond region; a conservative approach of resampling.

### Land Eligibility

Based on the land cover, protected areas, and slope data, the land eligibility for renewable power plants is determined. Currently, only roof mounted PV, PV farms, and wind farms are considered. The result is a raster data set classifying each pixel whether its land can be used for roof-mounted PV, PV and wind farms, wind farms only, or not at all for renewable power provision.

### Administrative areas

Administrative areas as considered in this study are based on NUTS and GADM data. I am not using NUTS only as NUTS levels represent statistical units, not administrative ones. I am considering three levels: national, subnational, and communal. Subnational divisions are taken from GADM data.

### Electricity demand distribution

The electricity demand of each autarkic region is determined using the national electricity demand data, the gridded population data, and the administrative areas data set. In a first step, the gridded population is mapped to the regions to determine the local population. After that, the national electricity demand is allocated to the regions proportional to the local population.

For France, Spain, and Portugal, the geographical perimeter of the load data is of importance in particular to understand whether their islands are included or not. ENTSO-e has enquired the national transmission grid operators in this regard [@entso-e:2016] and from the document the following can be derived on the geographical perimeter of the load data:

France

:   The hourly load data excludes all overseas territories and Corsica as well.

Spain

:   The hourly load data includes Spanish mainland only.

Portugal

:   The hourly load data excludes Azores and Madeira.

In conclusion, this means that Corsica and the Balearic Islands are missing in the load data and the data should hence be scaled up.

### Regions

Using the electricity demand distribution and the land eligibility raster data set, a final vector data base of all regions and their necessary attributes can be formed. For that, the eligible land categories are counted and associated to their regions.

### Necessary land

Finally the fraction of the eligible land that is necessary to supply the electricity demand can be assessed. For that I am using assumptions on the annual energy yield per squaremeter of PV and wind to determine the annual energy yield per region. This can then be compared to the electrical energy demand in the region to determine the fraction of eligible land necessary to supply the demand.

# Results

![Ranges of fraction of land necessary to fulfil demand in different countries.](../build/necessary-land-boxplots.png){#fig:necessary-land-boxplots .class}

![Regions with sufficient yearly aggregated renewable power (green) and with insufficient power (red).](../build/necessary-land-map.png){#fig:necessary-land-map .class}

# Bibliography
