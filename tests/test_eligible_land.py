import pytest
import numpy as np
from numpy.testing import assert_array_equal

from src.eligible_land import Eligibility, determine_eligibility


@pytest.fixture
def land_cover():
    return np.array([[11, 110], [110, 210], [14, 14]])


@pytest.fixture
def protected_areas():
    return np.array([[0, 0], [1, 0], [0, 0]])


@pytest.fixture
def slope():
    return np.array([[2, 2], [2, 1], [3, 18]])


@pytest.fixture
def bathymetry():
    return np.array([[20, 20], [200, -45], [30, 18]])


def test_eligibility(land_cover, protected_areas, slope, bathymetry):
    expected_result = np.array([
        [Eligibility.ONSHORE_WIND_OR_PV_FARM, Eligibility.ONSHORE_WIND_FARM],
        [Eligibility.NOT_ELIGIBLE, Eligibility.OFFSHORE_WIND_FARM],
        [Eligibility.ONSHORE_WIND_OR_PV_FARM, Eligibility.ONSHORE_WIND_FARM]
    ])
    assert_array_equal(determine_eligibility(land_cover, protected_areas, slope, bathymetry), expected_result)
