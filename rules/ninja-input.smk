"""Workflow to create simulation input for renewables.ninja.

We create a raster grid on top of a map of Europe in order of running one (wind)
or several (different roof configurations for pv) simulations per raster point.
"""
PYTHON = "PYTHONPATH=./ python"
PYTHON_SCRIPT = "PYTHONPATH=./ python {input} {output}"

CONFIG_FILE = "config/default.yaml"
RESOLUTION_KM2 = 200 # FIXME should be 50, corresponding to MERRA
configfile: CONFIG_FILE

include: "../Snakefile"
include: "sonnendach.smk"

rule all_ninja:
    message: "Create input files for renewable.ninja simulations."
    input:
        "build/ninja/pv.csv",
        "build/ninja/wind.csv"


rule pv:
    message: "Create pv simulation parameters for renewables.ninja."
    input:
        "src/ninja/pv.py",
        "build/european/units.geojson",
        rules.sonnendach_statistics.output.raw
    output: "build/ninja/pv.csv"
    shell: PYTHON_SCRIPT + " {RESOLUTION_KM2} {CONFIG_FILE}"


rule wind:
    message: "Create wind simulation parameters for renewables.ninja."
    input:
        "src/ninja/wind.py",
        "build/european/units.geojson",
        "build/eez-in-europe.geojson"
    output: "build/ninja/wind.csv"
    shell: PYTHON_SCRIPT + " {RESOLUTION_KM2} {CONFIG_FILE}"
