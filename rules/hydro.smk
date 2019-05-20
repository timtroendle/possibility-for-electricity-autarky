"""Rules to generate hydro electricity capacities and time series."""

configfile: "./config/default.yaml"
localrules: download_stations_database, stations_database

URL_STATIONS = "https://zenodo.org/record/2669146/files/energy-modelling-toolkit/hydro-power-database-3.zip?download=1"
IRENA_GENERATION = "data/irena-capacity-generation.xlsx"


rule download_stations_database:
    message: "Download database of hydro electricity stations."
    output:
        protected("data/automatic/raw-hydro-stations.zip")
    shell:
        "curl -sLo {output} '{URL_STATIONS}'"


rule stations_database:
    message: "Unzip stations database."
    input: rules.download_stations_database.output
    output: "build/data/jrc-hydro-power-plant-database.csv"
    shadow: "full"
    shell:
        """
        unzip {input} -d ./build/
        mv build/energy-modelling-toolkit-hydro-power-database-e857dd4/data/jrc-hydro-power-plant-database.csv {output}
        """


rule hydro_potential:
    message: "Define hydro generation on {wildcards.layer} layer."
    input:
        src = "src/hydro/units.py",
        units = rules.units.output[0],
        plants = rules.stations_database.output[0],
        national_generation = IRENA_GENERATION
    params:
        year = 2016 # FIXME rather take average from multiple years
    output: "build/{layer}/hydro-potential.csv"
    conda: "../envs/hydro.yaml"
    script: "../src/hydro/units.py"
