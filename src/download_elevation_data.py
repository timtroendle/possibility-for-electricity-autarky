"""Module to download elevation data from CGIAR."""
import zipfile
from pathlib import Path
import tempfile
import io
import subprocess

import click
import requests

X_MIN = 34 # x coordinate of CGIAR tile raster
X_MAX = 42
Y_MIN = 1
Y_MAX = 6
DATA_URL = "http://droppr.org/srtm/v4.1/6_5x5_TIFs/srtm_{x:02d}_{y:02d}.zip"
FILE_NAME = "srtm_{x:02d}_{y:02d}.tif"


@click.command()
@click.argument("path_to_result")
def download_elevation_data(path_to_result):
    """Download CGIAR tiles for Europe and merges them."""
    with tempfile.TemporaryDirectory(prefix='elevation-data') as tmpdir:
        print("Downloading files...")
        tiles = [_tile(x, y, tmpdir)
                 for x in range(X_MIN, X_MAX + 1)
                 for y in range(Y_MIN, Y_MAX + 1)
                 if not (x is 34 and y not in [1, 2])] # these tiles do not exist
        print("Merging files...")
        _merge(tiles, path_to_result)


def _tile(x, y, tmpdir):
    r = requests.get(DATA_URL.format(x=x, y=y))
    print("Downloading {}".format(r.url))
    z = zipfile.ZipFile(io.BytesIO(r.content))
    z.extractall(path=tmpdir)
    return (Path(tmpdir) / FILE_NAME.format(x=x, y=y)).absolute()


def _merge(tiles, path_to_output):
    cmd = (['rio', 'merge'] +
           [tile.as_posix() for tile in tiles] +
           [path_to_output, '--force-overwrite'])
    popen = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
    )
    for stdout_line in iter(popen.stdout.readline, ""):
        print(stdout_line, end="")
    popen.stdout.close()
    return_code = popen.wait()
    if return_code:
        raise subprocess.CalledProcessError(return_code, cmd)


if __name__ == '__main__':
    download_elevation_data()
