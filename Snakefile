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


rule clean:
    shell:
        "rm -rf ./build/*"


rule test:
    shell:
        "py.test"
