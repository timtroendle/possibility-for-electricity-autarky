from pathlib import Path

PATH_TO_VERSION_FILE = Path(__file__).parent / '..' / 'VERSION'

WEB_CACHE = "./build/webcache"
"""Cache for downloads from web."""

__version__ = PATH_TO_VERSION_FILE.open().readlines()[0].strip()
