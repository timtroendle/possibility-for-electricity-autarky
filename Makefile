PYTHON = PYTHONPATH=./ python
RAW_DEMAND_DATA = https://data.open-power-system-data.org/time_series/2017-07-09/time_series_60min_stacked.csv

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


build/national-demand.csv: src/process_demand.py build/raw-data-demand.csv
	$(PYTHON) $^ $@

## paper : runs all computational steps and creates the final paper
.PHONY: paper
paper: | build build/paper.pdf

build/paper.pdf: report/literature.bib report/main.md report/pandoc-metadata.yml
	cd ./report && \
	pandoc --filter pantable --filter pandoc-fignos --filter pandoc-tablenos --filter pandoc-citeproc \
		main.md pandoc-metadata.yml -t latex -o ../build/paper.pdf
