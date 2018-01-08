PYTHON_SCRIPT = "PYTHONPATH=./ python {input} {output}"
URL_LOAD = "https://data.open-power-system-data.org/time_series/2017-07-09/time_series_60min_stacked.csv"


rule paper:
    input:
        "build/necessary-land-boxplots.png",
        "build/necessary-land-map.png",
        "report/literature.bib",
        "report/main.md",
        "report/pandoc-metadata.yml"
    output:
        "build/paper.pdf"
    shell:
        "cd ./report && \
        pandoc --filter pantable --filter pandoc-fignos --filter pandoc-tablenos \
        --filter pandoc-citeproc main.md pandoc-metadata.yml -t latex -o ../build/paper.pdf"


rule download_raw_load:
    output:
        protected("build/raw-load-data.csv")
    shell:
        "curl -Lo {output} '{URL_LOAD}'"


rule process_load:
    input:
        "src/process_load.py",
        rules.download_raw_load.output
    output:
        "build/national-load.csv"
    shell:
        PYTHON_SCRIPT


rule clean: # removes all generated results
    shell:
        "rm -r ./build/*"


rule force_clean: # removes all builds including protected results
    shell:
        "rm -rf ./build/*"


rule test:
    shell:
        "py.test"
