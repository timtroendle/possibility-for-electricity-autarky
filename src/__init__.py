from pathlib import Path

PATH_TO_VERSION_FILE = Path(__file__).parent / '..' / 'VERSION'

__version__ = PATH_TO_VERSION_FILE.open().readlines()[0].strip()
