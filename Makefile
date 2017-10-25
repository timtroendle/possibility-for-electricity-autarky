PYTHON = PYTHONPATH=./ python
RAW_NUTS_SHP = build/NUTS_2013_01M_SH/data/NUTS_RG_01M_2013.shp
RAW_GRIDDED_POP_DATA = ./data/gpw-v4-population-count-2015/gpw-v4-population-count_2015.tif
RAW_LAND_COVER_DATA = ./build/Globcover2009_V2.3_Global_/GLOBCOVER_L4_200901_200912_V2.3.tif
RAW_PROTECTED_AREAS_DATA = build/WDPA_Oct2017/WDPA_Oct2017-shapefile-polygons.shp

DEMAND_URL = https://data.open-power-system-data.org/time_series/2017-07-09/time_series_60min_stacked.csv
NUTS_URL = http://ec.europa.eu/eurostat/cache/GISCO/geodatafiles/NUTS_2013_01M_SH.zip
LAND_COVER_URL = http://due.esrin.esa.int/files/Globcover2009_V2.3_Global_.zip
PROTECTED_AREAS_URL = https://www.protectedplanet.net/downloads/WDPA_Oct2017?type=shapefile

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

build/national-demand.csv: src/process_demand.py build/raw-data-demand.csv
	$(PYTHON) $^ $@

build/nuts-2013-pop.geojson: $(RAW_NUTS_SHP) $(RAW_GRIDDED_POP_DATA)
	fio cat $(RAW_NUTS_SHP) | rio zonalstats -r $(RAW_GRIDDED_POP_DATA) --prefix "population_" --stats sum > $@

build/nuts-distributions.png: src/visualise_nuts.py build/nuts-2013-with-population.geojson
	$(PYTHON) $^ $@

build/nuts-2013-pop-demand.geojson: src/spatial_demand.py build/national-demand.csv build/nuts-2013-pop.geojson
	$(PYTHON) $^ $@

build/nuts-2013-pop-demand-cover.geojson: src/available_land.py build/nuts-2013-pop-demand.geojson $(RAW_LAND_COVER_DATA)
	$(PYTHON) $^ $@

## paper : runs all computational steps and creates the final paper
.PHONY: paper
paper: | build build/paper.pdf

build/paper.pdf: report/literature.bib report/main.md report/pandoc-metadata.yml
	cd ./report && \
	pandoc --filter pantable --filter pandoc-fignos --filter pandoc-tablenos --filter pandoc-citeproc \
		main.md pandoc-metadata.yml -t latex -o ../build/paper.pdf
