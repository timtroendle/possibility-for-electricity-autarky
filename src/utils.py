"""Module containing utilities."""
from pathlib import Path

import click
import yaml

PATH_TO_CONFIGS = Path(__file__).parent / '..' / 'config'


class Config(click.ParamType):
    """A configuration parameter on the command line.

    Configurations will always be read from the config directory.
    """
    name = "configuration"

    def convert(self, value, param, ctx):
        name_of_file = Path(value).name
        path_to_file = PATH_TO_CONFIGS / name_of_file
        if not path_to_file.exists():
            raise ValueError("Config {} does not exist.".format(path_to_file))
        with path_to_file.open('r') as stream:
            try:
                return yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                raise IOError(exc)
