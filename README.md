# Renewable Resource Potentials

Evaluation of resource potential sufficiency for energy autarkic regions.

This repository contains the entire scientific project, including code and report. The philosophy behind this repository is that no intermediary results are included, but all results are computed from raw data and code.

## Getting ready

### Installation

The following dependencies are needed to set up an environment in which the analysis can be run and the paper be build:

* [conda](https://conda.io/docs/index.html)
* `LaTeX` to [produce a PDF](http://pandoc.org/MANUAL.html#creating-a-pdf). Can be avoided by switching to [any other output format supported by pandoc](http://pandoc.org/index.html).

When these dependencies are installed, you can create a conda environment from within you can run the analysis:

    conda env create -f conda-environment.yml

Don't forget to activate the environment. To see what you can do now, run:

    snakemake --list

### Data to be retrieved manually

Whenever possible, data is downloaded automatically. As this is not always possible, you will need to retrieve the following data sets manually:

* [European Settlement Map 2012, Release 2017, 100m](https://land.copernicus.eu/pan-european/GHSL/european-settlement-map), to be placed at `./data/esm-100m-2017/`
* [World Exclusive Economic Zones v10](http://www.marineregions.org/downloads.php), to be placed in `./data/World_EEZ_v10_20180221`
* [Sonnendach.ch 2018-04-18](http://www.sonnendach.ch), to be placed in `./data/sonnendach/`
* [Federal Register of Buildings and Dwellings (RBD/GWR) 2018-07-01](https://www.bfs.admin.ch/bfs/en/home/registers/federal-register-buildings-dwellings.html), to be placed in `./data/gwr/`
* onshore wind capacity factors from renewable.ninja, to be placed in `./data/wind/`
* simulated pv capacity factors from renewable.ninja, to be placed in `./data/pv.nc`

## Run the analysis

    snakemake paper

This will run all analysis steps to reproduce results and eventually build the paper.

You can also run certain parts only by using other `snakemake` rules; to get a list of all rules run `snakemake --list`.

To generate a PDF of the dependency graph of all steps, run:

    snakemake --rulegraph | dot -Tpdf > dag.pdf

(needs `dot`: `conda install graphviz`).

## Run the tests

    snakemake test

## Repo structure

* `report`: contains all files necessary to build the paper; plots and result files are not in here but generated automatically
* `src`: contains the Python source code
* `tests`: contains the test code
* `config`: configurations used in the study
* `rules`: additional Snakemake rules and workflows
* `data`: place for raw data, whether retrieved manually and automatically
* `build`: will contain all results (does not exist initially)
