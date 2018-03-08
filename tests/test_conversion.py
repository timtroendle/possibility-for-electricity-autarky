from datetime import timedelta

import pytest

from src.conversion import watt_to_watthours, eu_country_code_to_iso3


@pytest.mark.parametrize("watt,duration,expected_watthour", [
    (10, timedelta(minutes=60), 10),
    (6, timedelta(minutes=30), 3),
    (1 / 8760, timedelta(days=365), 1)
])
def test_watt_to_watthour_conversion(watt, duration, expected_watthour):
    assert watt_to_watthours(watt=watt, duration=duration) == expected_watthour


@pytest.mark.parametrize(
    "eu_country_code,iso3",
    [("DE", "DEU"),
     ("EL", "GRC"),
     ("UK", "GBR")]
)
def test_eu_country_code(eu_country_code, iso3):
    assert eu_country_code_to_iso3(eu_country_code) == iso3
