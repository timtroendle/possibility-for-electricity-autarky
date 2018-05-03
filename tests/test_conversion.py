from datetime import timedelta
import math

import pytest

from src.conversion import watt_to_watthours, eu_country_code_to_iso3, coordinate_string_to_decimal


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


@pytest.mark.parametrize(
    "arcminutes,expected_easting,expected_northing",
    [("""48°18'N 14°17'E""", 14.283333, 48.300000),
     ("""54°35'20.0"N 1°11'15.0"W""", -1.187500, 54.588889)]
)
def test_coordinates_to_decimal(arcminutes, expected_easting, expected_northing):
    easting, northing = coordinate_string_to_decimal(arcminutes)
    assert math.isclose(easting, expected_easting, abs_tol=0.00001)
    assert math.isclose(northing, expected_northing, abs_tol=0.00001)


@pytest.mark.parametrize(
    "arcminutes,expected_easting,expected_northing",
    [("""48°18'N 14°17'O""", 14.283333, 48.300000),
     ("""48°18'N 14°17' O""", 14.283333, 48.300000),
     ("""48°18'N, 14°17' O""", 14.283333, 48.300000),
     ("""48.300000 N, 14.283333O""", 14.283333, 48.300000),
     ("""48°18′N 14°17′E""", 14.283333, 48.300000),
     ("""48°18′0.0″N 14°17′0.0″E""", 14.283333, 48.300000)]
)
def test_coordinates_to_decimal_edgecases(arcminutes, expected_easting, expected_northing):
    easting, northing = coordinate_string_to_decimal(arcminutes)
    assert math.isclose(easting, expected_easting, abs_tol=0.00001)
    assert math.isclose(northing, expected_northing, abs_tol=0.00001)
