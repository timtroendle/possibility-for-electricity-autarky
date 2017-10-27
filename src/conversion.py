"""Functions to convert units."""

# from http://spatialreference.org/ref/sr-org/22/
GALL_PETERS_PROJ4 = "+proj=cea +lon_0=0 +lat_ts=45 +x_0=0 +y_0=0 +ellps=WGS84 +units=m +no_defs "


def watt_to_watthours(watt, duration):
    """Converts from [k|M|G|T]Watt to [k|M|G|T]WattHour."""
    return watt * duration.total_seconds() / 3600


def area_in_squaremeters(geodataframe):
    """Calculates the area sizes of a geo dataframe in square meters.

    Following https://gis.stackexchange.com/a/20056/77760 I am choosing Gall-Peters to receive
    a most accurate determination of the size of polygons in the geo dataframe.

    Returns a pandas series of area sizes in squre meters.
    """
    return geodataframe.to_crs(GALL_PETERS_PROJ4).area
