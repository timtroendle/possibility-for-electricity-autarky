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
include: "rules/publish-data.smk"
include: "rules/sync.smk"

localrules: all, paper, supplementary_material, clean

wildcard_constraints:
    layer = "({layer_list})".format(layer_list="|".join((f"({layer})" for layer in config["layers"]))),
    scenario = "({scenario_list})".format(scenario_list="|".join((f"({scenario})" for scenario in config["scenarios"])))

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
        "build/supplementary-material.docx",
        "build/logs/test-report.html",
        "build/technical-potential/normed-potentials-boxplots.tif",
        "build/technical-potential/sufficient-potentials-map.tif",
        "build/technical-social-potential/sufficient-potentials-map.tif",
        "build/technical-social-potential/normed-potentials-boxplots.tif",
        "build/necessary-land/necessary-land-map-when-pv-40%.tif",
        "build/necessary-land/necessary-land-all-layers.tif",
        "build/exclusion-layers-ROU.tif",


PAPER_DEPENDENCIES = [
    "report/paper.md",
    "report/literature.bib",
    "report/pandoc-metadata.yml",
    "report/energy-strategy-reviews.csl",
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
]


rule paper:
    message: "Compile paper."
    input: PAPER_DEPENDENCIES
    output:
        "build/paper.docx"
    shadow: "minimal"
    conda: "envs/report.yaml"
    shell:
        """
        cp report/* .
        {PANDOC} paper.md pandoc-metadata.yml -t docx -o {output}
        """


rule supplementary_material:
    message: "Compile the supplementary material."
    input:
        "report/supplementary.md",
        "report/literature.bib",
        "report/energy-strategy-reviews.csl",
        "report/data-sources.csv",
        rules.sonnendach_statistics.output.publish,
        expand(
            "build/exclusion-layers-{country_code}.png",
            country_code=[pycountry.countries.lookup(country).alpha_3
                          for country in config["scope"]["countries"]]
        ),
        "build/national/technical-potential/potentials-polished.csv",
        "build/national/technical-social-potential/potentials-polished.csv"
    output:
        "build/supplementary-material.docx"
    shadow: "minimal"
    conda: "envs/report.yaml"
    shell:
        """
        cp ./report/* .
        {PANDOC} supplementary.md -t docx -o {output} --table-of-contents
        """


rule clean: # removes all generated results
    shell:
        """
        rm -r ./build/*
        echo "Data downloaded to data/ has not been cleaned."
        """


rule test:
    input:
        PAPER_DEPENDENCIES, # proxy for: all has to exist before running the tests
        rules.total_swiss_yield_according_to_sonnendach_data.output
    output: "build/logs/test-report.html"
    conda: "envs/default.yaml"
    shell:
        "py.test --html={output} --self-contained-html"
