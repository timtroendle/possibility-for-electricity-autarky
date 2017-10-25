import pytest

from src.available_land import aggregate_stats


@pytest.fixture
def rasterstats():
    """Statistics as returned by rasterstats."""
    return [
        {11: 3, 14: 6, 230: 10},
        {14: 7, 230: 14}
    ]


def test_watt_to_watthour_conversion(rasterstats):
    expected_result = {
        "WATER": [0, 0],
        "NO_WATER": [9, 7],
        "NO_DATA": [10, 14]
    }
    assert aggregate_stats(rasterstats) == expected_result
