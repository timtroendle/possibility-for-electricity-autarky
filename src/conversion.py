"""Functions to convert units."""
import pycountry

# from https://epsg.io/3035
EPSG_3035_PROJ4 = "+proj=laea +lat_0=52 +lon_0=10 +x_0=4321000 +y_0=3210000 +ellps=GRS80 +units=m +no_defs "


def watt_to_watthours(watt, duration):
    """Converts from [k|M|G|T]Watt to [k|M|G|T]WattHour."""
    return watt * duration.total_seconds() / 3600


def area_in_squaremeters(geodataframe):
    """Calculates the area sizes of a geo dataframe in square meters.

    Following https://gis.stackexchange.com/a/20056/77760 I am choosing equal-area projections
    to receive a most accurate determination of the size of polygons in the geo dataframe.
    Instead of Gall-Peters, as suggested in the answer, I am using EPSG_3035 which is
    particularly usefull for Europe.

    Returns a pandas series of area sizes in square meters.
    """
    return geodataframe.to_crs(EPSG_3035_PROJ4).area


def eu_country_code_to_iso3(eu_country_code):
    """Converts EU country code to ISO 3166 alpha 3.

    The European Union uses its own country codes, which often but not always match ISO 3166.
    """
    assert len(eu_country_code) == 2, "EU country codes are of length 2, yours is '{}'.".format(eu_country_code)
    if eu_country_code.lower() == "el":
        iso2 = "gr"
    elif eu_country_code.lower() == "uk":
        iso2 = "gb"
    else:
        iso2 = eu_country_code
    return pycountry.countries.lookup(iso2).alpha_3
