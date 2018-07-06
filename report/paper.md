# Introduction

* motivation: why is this important? EU targets European market and Europeanisation of the power grid, therefore pushing against an alternative option for the European power grid: local autarky. In here we analyse whether this is a sensible thing to do or not. We quantify a necessary condition for local autarky: sufficient local renewable potential to satisfy the local demand.

* The renewable potential in Europe has been quantified in previous research results: determination of technical/social/ecological/economic potential of renewables on different levels: all Europe, single nations, single regions, but never for all Europe on high resolution.

* somewhere here explain different types of potentials

# Method

We assume autarky is a political decision and henceforth analyse autarky on administrative layers: all Europe, nations, regions, and municipalities. For each administrative unit on each administrative layer we quantify the renewable potentials and the current electricity demand. We will then reject autarky based on renewable electricity for those units for which the demand exceeds the potential. Data is NUTS / GADM + EEZ. (also discuss how to allocate EEZ to units)

## Renewable potential

First we determine the amount of eligible land per administrative unit, then we estimate the magnitude of electrical energy that can be generate on the available land.

### Open field land eligibility

* we divide Europe in a grid with 3 arcseconds (< 300m x 300m) resolution

* for each pixel we determine slope, environmental protection and land cover

* we allow wind on farms, forests, vegetation and bare land with slope < 20

* we allow pv on farms, vegetation and bare land with slope < 3

* we allow offshore wind in water depths of less than 50m.

* for the technical potential, we assume all land can be used, including the environmentally protected; for environmentally and socially restricted potential we limit the land use for renewables

### Rooftop PV eligibility

We mix a statistical approach with an analytical. First, we analytically derive the rooftop areas in each unit. We then use a detailed Swiss data set to correct the area estimation and to amend it with roof attributes necessary to derive pv potential like tilt and orientation of the roof.

First, we are using the European Settlement Map to identify the amount of rooftop area in each unit. We are considering only those pixels that had been classified as not eligible for other renewable generation before.

The European Settlement Map determines the fraction of rooftop areas in those areas which we rescale to match the sonnendach.ch data for Switzerland (assuming roof statistics are approximately equally distributed over Europe) and in this way we know the amount of rooftop area in each unit. Furthermore, we use the Swiss dataset to derive statistics about the distribution of roof attributes, assuming the Swiss housing stock is representative in Europe. TODO add table of statistical model.

### Renewable electricity yield

For wind, we assume a capacity density of onshore-wind: 8 [MW/km^2] and offshore-wind: 15 [MW/km^2] which allows us to derive the installable capacity of each administrative unit. We then use historically observed capacity factors from renewable.ninja per NUTS2 region to map from installable capacity to annual electricity yield.

For open field PV and roof-mounted PV, we assume a capacity density of ?? [MWp/km^2], southward facing and with tilt optimisation as defined by [@Jacobson:2018]. For PV of tilted roofs, we assume a capacity density of ?? [MWp/km^2] and we use the statistical model above to derive 16 different deployment situations. We then use renewable.ninja to simulate the renewable electricity yield.


## Current electricity demand

The electricity demand of each autarkic region is determined using the national electricity demand data, industrial demand data, the gridded population data, and the administrative areas data set. In a first step, the gridded population is mapped to the regions to determine the local population. After that, industrial demand is allocated to the regions in which they are located. Finally, the national non-industrial electricity demand is allocated to the regions proportional to the local population.

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

# Conclusion

TODO somewhere here discuss future trends that might become important: rising electricity demand from heat and mobility (important), urbanisation (important, but not huge), other technologies

TODO somewhere here discuss technical restrictions: distribution and transmission grid, intermittency of renewable infeed

the whole thing is mainly a problem of densely populated regions. rooftop pv is of major importance. as long as enough rooftop pv can be build, land demand is low for most municipalities. should less rooftop pv be useable, e.g. due to technical issues discussed above, many municipalities will need to use much higher shares of their land.

# Bibliography
