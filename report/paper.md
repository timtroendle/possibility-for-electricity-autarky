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

What's the potential on the European level? Then, on the national level (TODO rather show data than plot, the plot is ugly):

![Technical Potential of renewable power technologies to fulfil national demand.](../build/technical-potential/potentials.png){#fig:technical-potentials .class}

![Ranges of demand to technical potential ratio.](../build/technical-potential/necessary-land-boxplots.png){#fig:necessary-land-boxplots-technical .class}

8% of Europe's population affected, of which 95% live in urban administrative units.

## Social-ecological potential

In here, we prohibit the use of all protected land, PV on farmland, and 10% of all other technical potential be used, including offshore wind. We allow the use of all eligible roof areas.

![Ranges of demand to social-ecological potential ratio.](../build/full-protection/necessary-land-boxplots.png){#fig:necessary-land-boxplots-social-ecological .class}

![Regions with sufficient yearly aggregated renewable power (green) and with insufficient power (red).](../build/full-protection/necessary-land-map.png){#fig:necessary-land-map-social-ecological .class}

14% of Europe's population affected, of which 84% live in urban administrative units. Now, more rural population is affected.

## Assessing the drivers

Leaving out environmental protection only helps 0.6% of Europe's population.

How low can we go with the 10% to have a large impact?

# Conclusion

TODO somewhere here discuss future trends that might become important: rising electricity demand from heat and mobility (important), urbanisation (important, but not huge), other technologies

# Bibliography
