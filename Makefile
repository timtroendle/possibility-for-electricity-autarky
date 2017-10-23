PYTHON = PYTHONPATH=./ python
RAW_DEMAND_DATA = https://data.open-power-system-data.org/time_series/2017-07-09/time_series_60min_stacked.csv
RAW_NUTS_SHP = build/NUTS_2013_01M_SH/data/NUTS_RG_01M_2013.shp
RAW_GRIDDED_POP_DATA = ./data/gpw-v4-population-count-2015/gpw-v4-population-count_2015.tif

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
	curl -Lo $@ '$(RAW_DEMAND_DATA)'

build/raw-nuts-2013-01M-SH.zip:
	curl -Lo $@ 'http://ec.europa.eu/eurostat/cache/GISCO/geodatafiles/NUTS_2013_01M_SH.zip'

$(RAW_NUTS_SHP): build/raw-nuts-2013-01M-SH.zip
	unzip $^ -d ./build && \
	touch $@ # otherwise the rule would be executed again next time

build/national-demand.csv: src/process_demand.py build/raw-data-demand.csv
	$(PYTHON) $^ $@

build/nuts-2013-with-population.geojson: $(RAW_NUTS_SHP) $(RAW_GRIDDED_POP_DATA)
	fio cat $(RAW_NUTS_SHP) | rio zonalstats -r $(RAW_GRIDDED_POP_DATA) --prefix "population_" --stats sum > $@

build/nuts-2013-demand.geojson: src/spatial_demand.py build/national-demand.csv build/nuts-2013-with-population.geojson
	$(PYTHON) $^ $@

## paper : runs all computational steps and creates the final paper
.PHONY: paper
paper: | build build/paper.pdf

build/paper.pdf: report/literature.bib report/main.md report/pandoc-metadata.yml
	cd ./report && \
	pandoc --filter pantable --filter pandoc-fignos --filter pandoc-tablenos --filter pandoc-citeproc \
		main.md pandoc-metadata.yml -t latex -o ../build/paper.pdf
