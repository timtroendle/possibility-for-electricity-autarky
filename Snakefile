PYTHON = "PYTHONPATH=./ python"
PANDOC = "pandoc --filter pantable --filter pandoc-fignos --filter pandoc-tablenos --filter pandoc-citeproc"
PYTHON_SCRIPT = "PYTHONPATH=./ python {input} {output}"
PYTHON_SCRIPT_WITH_CONFIG = PYTHON_SCRIPT + " {CONFIG_FILE}"

CONFIG_FILE = "config/default.yaml"

configfile: CONFIG_FILE
include: "rules/data-preprocessing.smk"
include: "rules/sonnendach.smk"
include: "rules/capacityfactors.smk"
include: "rules/potential.smk"
include: "rules/analysis.smk"
include: "rules/sync.smk"

localrules: all, paper, supplementary_material, clean


onstart:
    shell("mkdir -p build/logs")
onsuccess:
    if "email" in config.keys():
        shell("echo "" | mail -s 'possibility-for-electricity-autarky succeeded' {config[email]}")
onerror:
    if "email" in config.keys():
        shell("echo "" | mail -s 'possibility-for-electricity-autarky crashed' {config[email]}")


rule all:
    message: "Run entire analysis and compile report."
    input:
        "build/paper.docx",
        "build/supplementary-material.docx"


rule sensitivities:
    message: "Perform sensitivity analysis on layer {wildcards.layer} using {threads} threads."
    input:
        "src/sensitivity.py",
        "build/{layer}/unconstrained-potentials-prefer-pv.csv",
        "build/{layer}/unconstrained-potentials-prefer-wind.csv",
        "build/{layer}/demand.csv",
        "build/{layer}/population.csv",
        "build/{layer}/units.geojson"
    output:
        "build/{layer}/sensitivities-urban-population.txt",
        "build/{layer}/sensitivities-rural-population.txt",
        "build/{layer}/sensitivities-number.txt"
    threads: config["snakemake"]["max-threads"]
    shell:
        PYTHON_SCRIPT + " {threads}"


rule paper:
    message: "Compile paper."
    input:
        "report/literature.bib",
        "report/paper.md",
        "report/pandoc-metadata.yml",
        "build/technical-potential/normed-potentials-boxplots.png",
        "build/technical-potential/sufficient-potentials-map.png",
        "build/technical-social-potential/sufficient-potentials-map.png",
        "build/technical-social-potential/normed-potentials-boxplots.png",
        "build/necessary-land/overview-necessary-land-when-pv-100%.csv",
        "build/necessary-land/overview-necessary-land-when-pv-40%.csv",
        "build/necessary-land/necessary-land-map-when-pv-40%.png",
        "build/necessary-land/necessary-land-all-layers.png",
        "build/exclusion-layers-ROU.png",
        rules.layer_overview.output
    output:
        "build/paper.docx"
    shell:
        """
        cd ./report
        {PANDOC} paper.md pandoc-metadata.yml -t docx -o ../build/paper.docx
        """


rule supplementary_material:
    message: "Compile the supplementary material."
    input:
        "report/supplementary.md",
        rules.sonnendach_statistics.output.publish,
        expand(
            "build/exclusion-layers-{country_code}.png",
            country_code=[pycountry.countries.lookup(country).alpha_3
                          for country in config["scope"]["countries"]]
        )
    output:
        "build/supplementary-material.docx"
    shell:
        """
        cd ./report
        {PANDOC} supplementary.md -t docx -o ../build/supplementary-material.docx --table-of-contents
        """


rule clean: # removes all generated results
    shell:
        """
        rm -r ./build/*
        echo "Data downloaded to data/ has not been cleaned."
        """


rule test:
    input:
        "build/paper.pdf", # proxy for: all has to exist before running the tests
        rules.total_swiss_yield_according_to_sonnendach_data.output
    shell:
        "py.test"
