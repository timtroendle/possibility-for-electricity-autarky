PYTHON = PYTHONPATH=./ python
RAW_NUTS_SHP = build/NUTS_2013_01M_SH/data/NUTS_RG_01M_2013.shp
RAW_ADMINISTRATIVE_BORDERS = build/administrative-borders.gpkg
RAW_GRIDDED_POP_DATA = ./data/gpw-v4-population-count-2015/gpw-v4-population-count_2015.tif
RAW_LAND_COVER_DATA = ./build/Globcover2009_V2.3_Global_/GLOBCOVER_L4_200901_200912_V2.3.tif
RAW_PROTECTED_AREAS_DATA = build/WDPA_Oct2017/WDPA_Oct2017-shapefile-polygons.shp
RAW_ELEVATION_DATA = build/raw-elevation-data.tif

DEMAND_URL = https://data.open-power-system-data.org/time_series/2017-07-09/time_series_60min_stacked.csv
NUTS_URL = http://ec.europa.eu/eurostat/cache/GISCO/geodatafiles/NUTS_2013_01M_SH.zip
LAND_COVER_URL = http://due.esrin.esa.int/files/Globcover2009_V2.3_Global_.zip
PROTECTED_AREAS_URL = https://www.protectedplanet.net/downloads/WDPA_Oct2017?type=shapefile

REF_EXTENT=-12 17 42 79
REF_EXTENT_COMMA=-12,17,42,79
REF_RESOLUTION=0.002777777777778 -0.002777777777778

.PHONY : help
help : Makefile
		@sed -n 's/^##//p' $<

build:
	mkdir ./build

## clean : removes all results that have been computed earlier
.PHONY: clean
clean:
	rm -rf ./build/*

## test  : runs the test suite
.PHONY: test
test:
	py.test

$(RAW_ADMINISTRATIVE_BORDERS): src/administrative_borders.py
	$(PYTHON) $^ $@

build/raw-data-demand.csv:
	curl -Lo $@ '$(DEMAND_URL)'

$(RAW_LAND_COVER_DATA):
	curl -Lo ./build/Globcover2009.zip '$(LAND_COVER_URL)'
	unzip ./build/Globcover2009.zip -d ./build/Globcover2009_V2.3_Global_
	touch $@ # otherwise the rule would be executed again next time

$(RAW_NUTS_SHP):
	curl -Lo ./build/nuts-2013-01M-SH.zip '$(NUTS_URL)'
	unzip ./build/nuts-2013-01M-SH.zip -d ./build
	touch $@ # otherwise the rule would be executed again next time

$(RAW_PROTECTED_AREAS_DATA):
	curl -Lo ./build/wdpa.zip -H 'Referer: $(PROTECTED_AREAS_URL)' $(PROTECTED_AREAS_URL)
	unzip build/wdpa.zip -d build/WDPA_Oct2017
	touch $@ # otherwise the rule would be executed again next time

$(RAW_ELEVATION_DATA): src/download_elevation_data.py
	$(PYTHON) $^ $@

build/slope-europe.tif: $(RAW_ELEVATION_DATA) build/land-cover-europe.tif
	gdaldem slope -s 111120 -compute_edges $(RAW_ELEVATION_DATA) build/slope-temp.tif
	rio warp build/slope-temp.tif -o $@ --like build/land-cover-europe.tif --resampling bilinear
	rm build/slope-temp.tif

build/land-cover-europe.tif: $(RAW_LAND_COVER_DATA)
	rio clip $^ $@ --bounds $(REF_EXTENT)

build/protected-areas-europe.tif: $(RAW_PROTECTED_AREAS_DATA) build/land-cover-europe.tif
	# TODO misses the 9% protected areas available as points only. How to incorporate those?
	fio cat --rs --bbox $(REF_EXTENT_COMMA) $< | \
	fio filter "f.properties.STATUS == 'Designated'" | \
	fio collect --record-buffered | \
	rio rasterize --like build/land-cover-europe.tif -o build/protected-areas-europe-temp.tif
	rio convert --dtype uint8 build/protected-areas-europe-temp.tif -o $@
	rm build/protected-areas-europe-temp.tif

build/available-land.tif: src/available_land.py build/land-cover-europe.tif build/protected-areas-europe.tif build/slope-europe.tif
	$(PYTHON) $^ $@

build/national-demand.csv: src/process_demand.py build/raw-data-demand.csv
	$(PYTHON) $^ $@

build/nuts-2013-pop.geojson: $(RAW_NUTS_SHP) $(RAW_GRIDDED_POP_DATA)
	fio cat $(RAW_NUTS_SHP) | rio zonalstats -r $(RAW_GRIDDED_POP_DATA) --prefix "population_" --stats sum > $@

build/nuts-distributions.png: src/vis/nuts.py build/nuts-2013-with-population.geojson
	$(PYTHON) $^ $@

build/nuts-2013-pop-demand.geojson: src/spatial_demand.py build/national-demand.csv build/nuts-2013-pop.geojson
	# TODO check whether demand time series incorporates oversea regions in FR, ES, PT
	$(PYTHON) $^ $@

build/nuts-2013-pop-demand-availability.geojson: build/nuts-2013-pop-demand.geojson build/available-land.tif
	fio cat build/nuts-2013-pop-demand.geojson | rio zonalstats -r build/available-land.tif --categorical --prefix availability > $@

build/nuts-2013-necessary-land.geojson: src/necessary_land.py build/nuts-2013-pop-demand-availability.geojson
	# TODO this approach leads to up to 866 m^2 roof area per citizen -- way too much
	$(PYTHON) $^ $@

build/capacity_factors.txt: src/capacity_factors.py build/raw-data-demand.csv
	$(PYTHON) $^ $@

build/necessary-land-boxplots.png build/necessary-land-map.png: src/vis/necessary_land.py build/nuts-2013-necessary-land.geojson
	$(PYTHON) $^ build/necessary-land-boxplots.png build/necessary-land-map.png

## paper : runs all computational steps and creates the final paper
.PHONY: paper
paper: | build build/paper.pdf

build/paper.pdf: build/necessary-land-boxplots.png build/necessary-land-map.png
build/paper.pdf: report/literature.bib report/main.md report/pandoc-metadata.yml
	cd ./report && \
	pandoc --filter pantable --filter pandoc-fignos --filter pandoc-tablenos --filter pandoc-citeproc \
		main.md pandoc-metadata.yml -t latex -o ../build/paper.pdf
