from datetime import timedelta

import pytest

from src.conversion import watt_to_watthours


@pytest.mark.parametrize("watt,duration,expected_watthour", [
    (10, timedelta(minutes=60), 10),
    (6, timedelta(minutes=30), 3),
    (1 / 8760, timedelta(days=365), 1)
])
def test_watt_to_watthour_conversion(watt, duration, expected_watthour):
    assert watt_to_watthours(watt=watt, duration=duration) == expected_watthour
