# Rules to sync to and from Euler

EULER_URL = "euler.ethz.ch"
EULER_BASE_DIR = "~/Develop/possibility-for-electricity-autarky/"
EULER_BUILD_DIR = EULER_BASE_DIR + "build/"
LOCAL_EULER_RESULTS = "./build/euler/"


rule send:
    message: "Send changes to Euler"
    shell:
        "rsync -avzh --progress --delete -r . --exclude-from=.syncignore {EULER_URL}:{EULER_BASE_DIR}"


rule receive:
    message: "Receive build changes from Euler"
    shell:
        "rsync -avzh --progress --delete -r --exclude-from=.syncignore-build {EULER_URL}:{EULER_BUILD_DIR} {LOCAL_EULER_RESULTS}"
