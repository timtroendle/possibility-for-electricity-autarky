# Introduction

* motivation: why is this important? EU targets European market and Europeanisation of the power grid, therefore pushing against an alternative option for the European power grid: local autarky. In here we analyse whether this is a sensible thing to do or not. We quantify a necessary condition for local autarky: sufficient local renewable potential to satisfy the local demand.

* The renewable potential in Europe has been quantified in previous research results: determination of technical/social/ecological/economic potential of renewables on different levels: all Europe, single nations, single regions, but never for all Europe on high resolution.

* somewhere here explain different types of potentials

# Method

The degree of local electricity autarky in a region in Europe is shaped by political decisions: despite the liberalised energy market, support schemes and concessions can foster or hinder local generation and storage. Strong collaboration and trading between regions -- the alternative to autarky -- requires the deployment and maintenance of sufficient transfer capacities, which remains a public responsibility. We therefore analyse regions in Europe with their own administration on four levels: European, national, regional, and municipal. For each administrative unit on each administrative level we quantify the renewable potentials and the current electricity demand. We then reject autarky based on renewable electricity for those units for which the annual demand exceeds the annual potential.

To identify administrative units including their geographic shape on all levels we use data from NUTS 2013 [@eurostat:2015] and the global administrative areas database (GADM) [@GADM:2018]. The scope of our analysis is EU-28 excluding Malta for which no data was available, plus Switzerland, Norway, and the Balkan countries Albania, Bosnia and Herzegovina, Macedonia, Montenegro, and Serbia. Together, they form the European level; in isolation they form the national level. Country shapes for EU-28 countries and Switzerland and Norway are defined by NUTS 2013, and for the balkan countries by GADM. The regional level is defined by the first-level administrative divisions, e.g. cantones in Switzerland, régions in France, or oblasti in Bulgaria, of which GADM identifies 570 in the study area. Lastly, 124404 communes in the 34 countries form the municipal level. These communes are defined for most countries by the Local Administrative Unit 2 (LAU2) layer of NUTS 2013, and for Albania, Bosnia and Herzegovina, and Montenegro we took their definitions from GADM. Lastly, we estimate the size of maritime areas over which regions have sovereignty by allocating Exclusive Economic Zones (EEZ) to regions on all levels. We divide and allocate to all regions which share a coast with the EEZ. The share is proportional to the length of the shared coast. We use EEZ shape data from @Claus:2018.

## Renewable potential

To quantify the renewable potential in each administrative unit, we first estimate the amount of land eligible for generation of renewable electricity and then the magnitude of electrical energy that can be generated annually on the eligible land.

### Open field land eligibility

To decide which fractions of the land of an administrative unit can be used for open field PV, or on- and offshore wind farms, we divide Europe in a grid of 10 arcseconds resolution, whose cell size varies with the longitude but never exceeds 0.09 km^2^. For each cell we derive the current land cover and use [@EuropeanSpaceAgency:2010], the average slope of the terrain [@Reuter:2007; @Danielson:2011] or its maximum water depths [@Amante:2009], and whether it belongs to an area which is environmentally protected [@UNEP-WCMC:2017]. We prohibit energy generation next to settlements by amending the coarse land cover data with more detailed data on settlements with a cell size of 6.25m^2^ [@Ferri:2017]. Using this dataset we classify each 10 arcseconds cell as built-up area when more than 1% of its land are buildings or urban parks and prohibit energy generation on it. To quantify the technical potential, we use the following rules: We allow wind farms to be built on farmland, forests, open vegetation and bare land with slope below 20°. We furthermore allow open field PV to be built on farmland, vegetation and bare land with slope below 3°. Lastly, we allow offshore wind farms to be built in water depths of less than 50m. For environmentally and socially restricted potentials, we limit the land eligibility for renewable electricity further, for example by prohibiting the use of environmentally protected land or the use of farmland for open field PV as it may lead to land use conflicts.

### Roofs for PV

The potential of roof-mounted PV not only depends on the amount of roof areas available, but also on the orientation and the tilt of those roofs. We mix an analytical approach with a statistical one to derive the potential. First, we analytically derive the rooftop areas in each unit. We then use a data set of Swiss roofs to correct the area estimation and to amend it with tilt and orientation statistically.

We use the European Settlement Map (ESM) [@Ferri:2017] to identify the amount of rooftop area in each unit. The map is based on satellite images of 2.5m resolution and employs auxiliary data e.g. on population or national data on infrastructure to automatically classify each cell as building, street, urban green, etc. For each of our 10 arcseconds cells we sum up the space that is classified as buildings. We are considering only those cells that had been classified as built-up areas before and which are hence not used for other renewable generation.

We then amend this first estimation with data from sonnendach.ch for Switzerland [@SwissFederalOfficeofEnergy:2018]. We use this dataset in two ways: First we improve the area estimation based on the European Settlement Map. This estimation is less precise due to the coarse methodology compared to sonnendach.ch, underestimates the area due to a lack of tilt, and overestimates the area as it ignores unavailable parts of the roof, e.g. those covered with windows or chimneys. For the roofs included in the sonnendach.ch dataset, the European Settlement Map identifies 768km^2^ roof areas, where sonnendach.ch finds only 630km^2^. After applying the expert estimation of available areas [@SwissFederalOfficeofEnergy:2016], this is reduced to 441km^2^ (TODO update!). The ESM data overestimates the actual potential hence by 74%. We assume this overestimation is representative for all Europe and apply this factor to all areas identified by the European Settlement Map.

The second use we make out of the Swiss data is to identify the tilt and orientation of the roof areas. For that, we cluster all roofs in 17 categories: flat roofs, and roofs with south-, west-, north-, and east-wards orientation with 4 groups of tilt each. We then quantify the relative area share of each category, see Table @tbl:roof-statistics. We again assume the distribution of these attributes of the Swiss housing stock is representative for Europe and apply it to all regions.

```table
---
caption: 'Area share of Swiss roof categories in the sonnendach.ch data set. {#tbl:roof-statistics}'
alignment: CCC
include: ../build/swiss/roof-statistics-publish.csv
markdown: True
---
```

### Renewable electricity yield

Based on the previous steps we can quantify the amount of land in each administrative unit that is eligible for generation of renewable electricity. To estimate the annual generation for wind power, we first assume a capacity density of 8 MW/km^2^ and 15 MW/km^2^ for onshore and offshore wind respectively [@EuropeanEnvironmentAgency:2009] which allows us to derive the installable capacity for each unit. We then use historically observed capacity factors per NUTS2 region (respectively per country on the Western Balkan) from renewables.ninja [@Staffell:2016] to determine the annual electricity yield from installable capacity.

For open field PV and flat roof-mounted PV, we assume a capacity density of ?? MWp/km^2^, southward facing and with tilt optimisation as defined by [@Jacobson:2018]. For PV of tilted roofs, we assume a capacity density of ?? MWp/km^2^ and we use the statistical model from Table @tbl:roof-statistics to derive 16 different deployment situations. We then use renewables.ninja [@Staffell:2016; @Pfenninger:2016] to simulate the renewable electricity yield of each deployment situation in each administrative unit of the regional level. In Switzerland for example, this leads to 442 simulations, based on 17 deployment situations in 26 cantons.

The aggregated yield of onshore wind, offshore wind, open field PV and roof-mounted PV represents the technical renewable electricity potential for each administrative unit.

## Current electricity demand

We relate the renewable electricity potential to the local electricity demand of today. As a base, we are using the load data from 2017 for each country [@OpenPowerSystemData:2018] originally published by ENTSO-e. For subnational levels, we upsample the data by the use of a dataset on demand of electricity intensive industries and on population in Europe.

We derive the dataset of electricity intensive industries from the European Emission Trading Scheme (ETS). Using ETS as a base means we are neglecting industries in Switzerland and the Western Balkan countries which do not take part in the scheme. We consider those steel, aluminium, and chloralkali factories, that are responsible for more than 0.5% of the respective ETS activity. Based on the ETS address registry and manual research, we identify the exact location of those factories.

As there is no comprehensive and/or consistent data set for industry production, we make two important assumptions to determine the production, and hence the electricity demand, of each installation. First, we assume that the product output of each plant is homogenous, corresponding to “steel”, “aluminium”, etc.: we do thus not differentiate between different types of steel or different aluminium products. Hence, each product comes with a generic electricity intensity factor (MWh/t output) which we derive from [@Ecorys:2009; @Paulus:2011; @Eurofer:2015; @Klobasa:2007; @EAA:2012; @Eurochlor:2014]. Second, we assume that the production of each facility is directly proportional to its emissions: a factory emitting 10% of the Activity’s CO~2~ emissions (after all installations contributing 0.5% or less have been removed) is assumed to produce 10% of the output of all facilities in the filtered list under each Activity. As base for the yearly European production, we take industry organisation data [@Eurofer:2015; @EAA:2012; @Cembuerau:2015; @Eurochlor:2014; @Paulus:2011] for the most recent year available. For chloralkali plants, we assume the lowest electricity intensity in the range given by @Klobasa:2007, given the efficiency improvements (-8% intensity since 2001) over the last decade [@Eurochlor:2014].

We use the dataset of industries to localise electricity intensive industrial demand to administrative units. We assume the remaining electricity demand of non electricity intensive industries, commerce, and households is spatially distributed over the country proportional to the population. We use the Global Human Settlement Population Grid which maps population in 2015 with a resolution of 250m [@JRC:2015] in Europe and globally. It is based on national censuses and population registers. With that, we define the local, annual electricity demand in each administrative unit of each administrative level.

# Results

## Technical potential

What's the potential on the European level? Total potential [TWh/a],235463.32
Normed potential [-],73.52
Roof mounted PV potential [TWh/a],7000.07
Open field PV potential [TWh/a],151276.25
Onshore wind potential [TWh/a],54642.86
Offshore wind potential [TWh/a],37417.57
Roof mounted PV potential [-],2.19
Open field PV potential [-],47.24
Onshore wind potential [-],17.06
Offshore wind potential [-],11.68

Then, on the national level:

id	normed_potential
CH	3.99
BE	10.43
LU	10.91
SI	14.91
AT	21.73

Subnational:

id	normed_potential
BEL.1_1	0.54
CHE.5_1	0.74
NOR.12_1	0.96
AUT.9_1	1.05
DEU.3_1	1.24
MKD.10_1	1.42
CHE.8_1	1.46
MKD.9_1	1.59
ESP.7_1	1.62
MKD.12_1	1.73
CHE.26_1	1.76
CZE.11_1	1.81
CHE.4_1	1.81
ROU.10_1	1.82
HUN.5_1	1.97
MKD.71_1	2.08


Municipal:

2% of the municipalities and 8% of Europe's population affected, of which 98% live in administrative units with high population density (93% DEGURBA cities / 7% towns / 0% rural); 4% live in industrial areas (with share > 50%), 1% lives in mountaineous areas (with median steepness > 20).

![Ranges of demand to technical potential ratio.](../build/technical-potential/normed-potentials-boxplots.png){#fig:normed-potentials-boxplots-technical .class}

## Social-ecological potential

In here, we prohibit the use of all protected land, PV on farmland, and 10% of all other technical potential be used, including offshore wind. We allow the use of all eligible roof areas.

European level

Total potential [TWh/a]	15691.47
Normed potential [-]	4.90
Roof mounted PV potential [TWh/a]	7000.07
Open field PV potential [TWh/a]	11801.71
Onshore wind potential [TWh/a]	3984.70
Offshore wind potential [TWh/a]	2452.48
Roof mounted PV potential [-]	2.19
Open field PV potential [-]	3.69
Onshore wind potential [-]	1.24
Offshore wind potential [-]	0.77

National level:

id	normed_potential
CH	1.69
BE	1.70
LU	1.93
AT	2.45
DE	2.81

Subnational level:

id	normed_potential
NOR.12_1	0.2500
BEL.1_1	0.53
ESP.7_1	0.57
AUT.9_1	0.72
CHE.5_1	0.73
CZE.11_1	0.850
CHE.8_1	0.93
FRA.8_1	1.03
MKD.71_1	1.070
DEU.3_1	1.09
IRL.6_1	1.09
MKD.9_1	1.16
NOR.1_1	1.23

Municipal level:

![Ranges of demand to social-ecological potential ratio.](../build/full-protection/normed-potentials-boxplots.png){#fig:normed-potentials-boxplots-social-ecological .class}

![Regions with sufficient yearly aggregated renewable power (green) and with insufficient power (red).](../build/full-protection/normed-potentials-map.png){#fig:normed-potentials-map-social-ecological .class}

14% of Europe's population affected, of which 84% live in urban administrative units. Now, more rural population is affected.
3% of the municipalities and 14% of Europe's population affected, of which 90% live in administrative units with high population density (86% DEGURBA cities / 12% towns / 2% rural); 5% live in industrial areas (with share > 50%), 2% lives in mountaineous areas (with median steepness > 20).

## Assessing the drivers

Leaving out environmental protection only helps 0.6% of Europe's population.

How low can we go with the 10% to have a large impact?

![Number of municipalities whose land demand for becoming autarkic is greater than a certain fraction.](../build/necessary-land.png){#fig:nnecessary-land .class}

![Total land demand (25/50%/75% quantile) on the national (blue), subnational (orange), and municipal (green) layer, when only a certain fraction of the demand can be supplied by rooftop PV.](../build/necessary-land-all-layers.png){#fig:nnecessary-land-all-layers .class}

# Conclusion

TODO Whats important here is the difference between European and municipal level! The actual numbers are very uncertain, but the relation is not. So I should rather show the differences it makes in land use.

TODO somewhere here discuss future trends that might become important: rising electricity demand from heat and mobility (important), urbanisation (important, but not huge), other technologies

TODO somewhere here discuss technical restrictions: distribution and transmission grid, intermittency of renewable infeed

TODO somewhere here discuss economic restrictions: LCOE e.g. from slope, access to roads, magnitude of resources (north facing rooftop pv anyone?)

TODO somewhere here discuss short comings of this approach: [@Holtinger:2016] e.g. reports that distance to settlements in Austria and Germany have a large impact; ignoreing suitable zones;

the whole thing is mainly a problem of densely populated regions. rooftop pv is of major importance. as long as enough rooftop pv can be build, land demand is low for most municipalities. should less rooftop pv be useable, e.g. due to technical issues discussed above, many municipalities will need to use much higher shares of their land.

# Bibliography
