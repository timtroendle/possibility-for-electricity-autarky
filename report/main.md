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

ETOPO1 Global Relief Model

:   Offshore wind power can be build in shallow and medium-deep water. To determine the depth of the water I am using the ETOPO1 Global Relief Model [@Amante:2009], which has a resolution of 1 arcminute.

GlobCover 2009 -- land cover data

:   GlobCover2009 is a land cover data set provided by the European Space Agency which determines land cover worldwide with a resolution of 10 arcseconds [@EuropeanSpaceAgency:2010].

European Settlement Map 2012, Release 2017

:   European Settlement Map is a spatial raster data set that maps settlements in Europe. It is provided by JRC in a resolution of 2.5m [@Ferri:2017]. In here, I am using the statistical summary provided at 100m resolution to identify buildings.

World Database on Protected Areas

:   The world database on protected areas [@UNEP-WCMC:2017] maps areas that are protected by national law. It is provided as a vector database.

Gridded Population of the World v4

:   The gridded population of the world data base provides an estimate of the spatial distribution of the worlds population in 2020 with a resolution of 30 arcseconds [@CIESIN:2016; @Doxsey-Whitfield:2015]. It is based on national censuses and population registers.

NUTS

:   Eurostat's Nomenclature of territorial units for statistics provides the basis by which Europe is divided into regions in this analysis [@eurostat:2015].

GADM

:   The global administrative areas database [@GADM:2018] is used to amend NUTS data.

Exclusive Economic Zones

:   The exclusive economic zones determine sovereignty of nations over maritime areas [@Claus:2018].

Electricity demand

:   ENTSO-e provides historical load time series for most countries in Europe with a resolution of 1 hour. In this analysis I will use the processed version provided by @OpenPowerSystemData:2018.

Capacity factors PV and wind

:   National capacity factors for PV and wind for each hour of the year for the years between 1985-2015 and 1980-2016 are taken from renewable.ninja [@Pfenninger:2016; @Staffell:2016].

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

### Electricity intensive industries

We constructed the data set for energy intensive industries primarily based on the European Emission Trading Scheme (ETS) data for emissions in 2014 as well as the ETS address registry. This means that we only consider factories in the European Union, Norway and Liechtenstein, but not Switzerland, the Western Balkan countries  and Iceland . The electricity intensive industries considered are steel, aluminium, cement, and chloralkali , WHAT ABOUT GLASS; CERAMICS; PAPER (SOURCES).

For all industries, we took the facilities registered under the respective Main Activity Code to be the production facilities for the goods in question. In some cases, the ETS data base is ambiguous: for example, some combustion facilities (for electricity and/or heat, listed under Activity 20) apparently belong to a factory, as indicated by the inclusion of “aluminium” or “steel” in the name of the combustion facility. As there is no way to create a consistent set of factories based on such a manual search (it cannot be ruled out that other Activity 20 entries are connected to a factory, but without being named “steel”, “aluminium”, etc, or having that name in the local language), we consider only the factories listed in the ETS in the unambiguous categories for the respective good.

----------------------------------------------------------------------------------------------
type of industry                         source
----------------------------------  ---------------
Steel                               ETS main activity 5 (production of pig iron or steel
                                    (primary or secondary fusion), including continuous casting

                                    ETS main activity 24 (Production of pig iron or steel)

                                    ETS main activity 4 (Metal ore roasting or sintering)

Aluminium                           ETS main activity 26 (Primary aluminium

                                    ETS main activity 27 (Secondary aluminium)

Cement                              ETS main activity 29 (cement clinker)

Chloralkali                         Plant list from Eurochlor [@Eurochlor:2014]

----------------------------------------------------------------------------------------------

From the ETS data, we exclude all facilities with no reported emissions in 2013 and 2014; if data for is reported for only one year and the account is not reported as closed, the factory is included. We use the largest emissions for 2013 or 2014 as the emissions for the factory.The factories are then sorted according to emissions, and the installations responsible for 0.5% or less of the Activity’s total emissions are excluded. For chloralkali, we excluded all facilities with a capacity of 0.5% or less of the total European chlor production capacity. The remaining installations are then cross-checked with the ETS address registry and the addresses are converted to coordinates. For chloralkali, the cities were already included in the primary data. For aluminium, the ETS address registry does not hold the precise addresses: here, we searched for each installation manually. For all installations, the coordinates are those of the city of the postal address of the plant, and are thus only approximations. Two installations were excluded, as no address could be found (the secondary aluminium re-smelters „Gesamte Gießerei“ (ETS ID 14632-0007) and Alcoa Manufacturing (GB) Ltd“ (ETS ID UK-E-IN-12608). As only cement clinker production is included in the ETS, whereas cement grinding – which is the most electricity intensive step – is not, we here assume that the cement mills are co-located with the cement clinker production installations.


----------------------------------------------------------------------------------------------
type of industry      Electricity intensity (MWh/t)    European production   Average utilisation
------------------  --------------------------------  --------------------- ---------------------
Steel               0.25-0.65 [@Ecorys:2009]          170 Mt crude steel    75% [@Paulus:2011]
                    0.525 [@Paulus:2011] (electric    [@Eurofer:2015]
                    arc remelting)                    (2014)

Primary aluminium   15 [@Ecorys:2009;                 4.7 Mt [@EAA:2012]    98% [@Paulus:2011]
                    @Paulus:2011; @Klobasa:2007]      (2011)

Secondary aluminium 0.7 [@Ecorys:2009]                4.3 Mt [@EAA:2012]    98% [@Paulus:2011]
                                                      (2011)

Cement              0.105 (clinker) +                 157.2 Mt              100% (mills)
                    0.06 (cement grinding)            [@Cembuerau:2015]
                                                      (2013)

Chlor               3.3 (Hg Process)                  9454 kt Cl            76% [@Eurochlor:2014]
                    2.55 (Diaphragm)                  [@Eurochlor:2014]
                    2.64 (Membrane) [@Klobasa:2007]

----------------------------------------------------------------------------------------------

As there is no comprehensive and/or consistent data set for industry production, we make two important assumptions to determine the production, and hence the electricity demand, of each installation. First, we assume that the product output of each plant is homogenous, corresponding to “steel”, “aluminium”, etc.: we do thus not differentiate between different types of steel or different aluminium products. Hence, each product comes with a generic electricity intensity factor (MWh/t output). Second, we assume that the production of each facility is directly proportional to its emissions: a factory emitting 10% of the Activity’s CO2 emissions (after all installations contributing 0.5% or less have been removed) is assumed to produce 10% of the output of all facilities in the filtered list under each Activity. As base for the yearly European production, we take industry organisation data (SOURCES) for the most recent year available.

For chloralkali plants, we assume the lowest electricity intensity in the range given by Klobasa, given the efficiency improvements (-8% intensity since 2001) over the last decade [@Eurochlor:2014].

### Electricity demand distribution

The electricity demand of each autarkic region is determined using the national electricity demand data, industrial demand data, the gridded population data, and the administrative areas data set. In a first step, the gridded population is mapped to the regions to determine the local population. After that, industrial demand is allocated to the regions in which they are located. Finally, the national non-industrial electricity demand is allocated to the regions proportional to the local population.

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

Both offshore wind and rooftop pv need special treatments. That's first because the regions do not include maritime regions and hence ignore offshore wind potential. And second, because the land cover data set identifies urban areas, but its resolution is too coarse to identify rooftop areas. Large fraction of urban areas are not rooftop areas though, but parks, streets, or water areas. Without special treatment, using land cover data alone would hence lead to an overestimation of rooftop pv potential.

To handle offshore wind, I am using the Economic Exclusive Zones (EEZ) to determine how much offshore wind potential each region has. EEZ are national sovereignty, so there is no correct way to allocate shares of maritime regions to subnational regions. In here, I choose a simple approach: I allocate offshore wind potential to all regions that share a coast with the EEZ. The share is proportional to the length of the shared coast. This simple approach ignores spatial distribution within the EEZs. For example, if there are two regions sharing a coast with an EEZ and both coast lengths are the same, I will allocate 50% of the offshore wind potential to each region in any case. That is true even if one region has all its coast protected and the other not.

To handle rooftop pv, I am using the European Settlement Map to identify the share of rooftop areas in each region. Really what I am doing is identifying buildings as the map has no information on the type of the rooftop or more generally the suitability for pv. This step is hence still an upper bound for rooftop pv potential.

### Necessary land

Finally the fraction of the eligible land that is necessary to supply the electricity demand can be assessed. For that I am using two things:

* national capacity factors,
* and assumptions on maximal density of installable power per technology.

I am using the national capacity factors from renewables.ninja for all regions of a given country. Where national capacity factors for onshore wind are missing, I am using the ones from neighbouring countries. Where national capacity factors for offshore wind are missing, I am using the ones from onshore wind.

The assumptions on maximal density of installable power per technology are taken from the literature [@Gagnon:2016; @EuropeanEnvironmentAgency:2009] and determine which capacity of a certain technology can be installed per land area.

Using these factors together with the eligible land estimation of all steps before lets me determine the annual energy yield per region. This can then be compared to the electrical energy demand in the region to determine the fraction of eligible land necessary to supply the demand.

# Results

![Potential of renewable power technologies to fulfil national demand.](../build/potentials.png){#fig:potentials .class}

![Ranges of fraction of land necessary to fulfil demand in different countries.](../build/necessary-land-boxplots.png){#fig:necessary-land-boxplots .class}

![Regions with sufficient yearly aggregated renewable power (green) and with insufficient power (red).](../build/necessary-land-map.png){#fig:necessary-land-map .class}

# Bibliography
