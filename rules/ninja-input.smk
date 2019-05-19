"""Workflow to create simulation input for renewables.ninja.

We create a raster grid on top of a map of Europe in order of running one (wind)
or several (different roof configurations for pv) simulations per raster point.
"""
PYTHON = "PYTHONPATH=./ python"
PYTHON_SCRIPT = "PYTHONPATH=./ python {input} {output}"

CONFIG_FILE = "config/default.yaml"
configfile: CONFIG_FILE

include: "../Snakefile"
include: "sonnendach.smk"


rule ninja_simulation_input:
    message: "Create input files for renewable.ninja simulations."
    input:
        "build/capacityfactors/ninja-input-pv.csv",
        "build/capacityfactors/ninja-input-wind-onshore.csv",
        "build/capacityfactors/ninja-input-wind-offshore.csv"


rule pv_simulation_points:
    message: "Create locations and parameters of pv simulations for renewables.ninja."
    input:
        "src/capacityfactors/ninja_input_pv.py",
        "build/continental/units.geojson",
        rules.sonnendach_statistics.output.raw
    output:
        points = "build/capacityfactors/ninja-input-pv.csv",
    conda: "../envs/default.yaml"
    shell: PYTHON_SCRIPT + " {CONFIG_FILE}"


rule wind_simulation_points:
    message: "Create locations and parameters of wind simulations for renewables.ninja."
    input:
        "src/capacityfactors/ninja_input_wind.py",
        "build/continental/units.geojson",
        "build/eez-in-europe.geojson"
    output:
        points_onshore = "build/capacityfactors/ninja-input-wind-onshore.csv",
        points_offhore = "build/capacityfactors/ninja-input-wind-offshore.csv",
    conda: "../envs/default.yaml"
    shell: PYTHON_SCRIPT + " {CONFIG_FILE}"
