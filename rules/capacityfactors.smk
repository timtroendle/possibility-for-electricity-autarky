"""Workflow to create spatially disaggregated capacity factors from renewables.ninja simulations.

This is based on simulations run based on input generated in the workflow `ninja-input.smk`. Beware
that renewables.ninja simulations are not in the loop, i.e. they are not run automatically but must
be run manually if they need to be altered.
"""
PYTHON = "PYTHONPATH=./ python"
PYTHON_SCRIPT = "PYTHONPATH=./ python {input} {output}"

CONFIG_FILE = "config/default.yaml"
configfile: CONFIG_FILE


rule capacityfactor_timeseries:
    message: "Create index capacity factor timeseries of {wildcards.technology}."
    input:
        "src/capacityfactors/timeseries.py",
        "data/capacityfactors/{technology}/outputs",
    output:
        "build/capacityfactors/{technology}-timeseries.nc"
    shell:
        PYTHON_SCRIPT


rule capacityfactor_id_map:
    message: "Create raster map of indices to time series for {wildcards.technology}."
    input:
        src = "src/capacityfactors/id_map.py",
        timeseries = rules.capacityfactor_timeseries.output,
        reference = "build/land-cover-europe.tif"
    output:
        "build/capacityfactors/{technology}-ids.tif"
    shadow: "full"
    params:
        resolution = config["parameters"]["ninja"]["resolution-grid"]
    shell:
        """
        {PYTHON} {input.src} {input.timeseries} build/{wildcards.technology}-ids-lowres.tif {params.resolution}
        rio warp build/{wildcards.technology}-ids-lowres.tif {output} --like {input.reference} \
        --resampling nearest
        """


rule time_average_capacityfactor_map:
    message: "Create raster map of average capacity factors for {wildcards.technology}."
    input:
        "src/capacityfactors/averages_map.py",
        rules.capacityfactor_id_map.output,
        rules.capacityfactor_timeseries.output
    output:
        "build/capacityfactors/{technology}-time-average.tif"
    shell:
        PYTHON_SCRIPT
