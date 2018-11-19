"""Test whether potential estimations between layers are similar."""
import os
from pathlib import Path

import pytest
import pandas as pd

from src.potentials import Potential

TOLERANCE = 0.005 # 0.5%

BUILD_DIR = Path(os.path.abspath(__file__)).parent.parent / "build"
PATH_TO_EUROPEAN_POTENTIALS = BUILD_DIR / "european" / "technical-potential" / "potentials.csv"
PATH_TO_NATIONAL_POTENTIALS = BUILD_DIR / "national" / "technical-potential" / "potentials.csv"
PATH_TO_REGIONAL_POTENTIALS = BUILD_DIR / "regional" / "technical-potential" / "potentials.csv"
PATH_TO_MUNICIPAL_POTENTIALS = BUILD_DIR / "municipal" / "technical-potential" / "potentials.csv"


@pytest.mark.skipif(not PATH_TO_EUROPEAN_POTENTIALS.exists(), reason="European potentials not available.")
@pytest.mark.skipif(not PATH_TO_NATIONAL_POTENTIALS.exists(), reason="National potentials not available.")
@pytest.mark.parametrize(
    "potential", Potential
)
def test_european_to_national(potential):
    european = pd.read_csv(PATH_TO_EUROPEAN_POTENTIALS, index_col=0).sum()
    national = pd.read_csv(PATH_TO_NATIONAL_POTENTIALS, index_col=0).sum()

    assert european[str(potential)] == pytest.approx(national[str(potential)], TOLERANCE)


@pytest.mark.skipif(not PATH_TO_EUROPEAN_POTENTIALS.exists(), reason="European potentials not available.")
@pytest.mark.skipif(not PATH_TO_REGIONAL_POTENTIALS.exists(), reason="Regional potentials not available.")
@pytest.mark.parametrize(
    "potential", Potential
)
def test_european_to_regional(potential):
    european = pd.read_csv(PATH_TO_EUROPEAN_POTENTIALS, index_col=0).sum()
    regional = pd.read_csv(PATH_TO_REGIONAL_POTENTIALS, index_col=0).sum()

    assert european[str(potential)] == pytest.approx(regional[str(potential)], TOLERANCE)


@pytest.mark.skipif(not PATH_TO_EUROPEAN_POTENTIALS.exists(), reason="European potentials not available.")
@pytest.mark.skipif(not PATH_TO_MUNICIPAL_POTENTIALS.exists(), reason="Municipal potentials not available.")
@pytest.mark.parametrize(
    "potential", Potential
)
def test_european_to_municipal(potential):
    european = pd.read_csv(PATH_TO_EUROPEAN_POTENTIALS, index_col=0).sum()
    municipal = pd.read_csv(PATH_TO_MUNICIPAL_POTENTIALS, index_col=0).sum()

    assert european[str(potential)] == pytest.approx(municipal[str(potential)], TOLERANCE)
