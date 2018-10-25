import pytest
import numpy as np

from src.eligibility import Eligibility, _determine_eligibility, GlobCover, ProtectedArea


@pytest.fixture
def config():
    return {
        "parameters": {
            "max-slope": {
                "pv": 3,
                "wind": 20
            },
            "max-depth-offshore": -50,
            "max-building-share": 0.1,
            "max-urban-green-share": 0.1
        }
    }


@pytest.mark.parametrize(
    "land_cover,protected_areas,slope,bathymetry,building_share,urban_green_share,expected", [
        (GlobCover.RAINFED_CROPLANDS, ProtectedArea.NOT_PROTECTED, 0, 0, 0, 0,
         Eligibility.ONSHORE_WIND_AND_PV_FARMLAND),
        (GlobCover.RAINFED_CROPLANDS, ProtectedArea.NOT_PROTECTED, 4, 0, 0, 0, Eligibility.ONSHORE_WIND_FARMLAND),
        (GlobCover.RAINFED_CROPLANDS, ProtectedArea.NOT_PROTECTED, 21, 0, 0, 0, Eligibility.NOT_ELIGIBLE),
        (GlobCover.RAINFED_CROPLANDS, ProtectedArea.NOT_PROTECTED, 0, 0, 0.11, 0, Eligibility.ROOFTOP_PV),
        (GlobCover.RAINFED_CROPLANDS, ProtectedArea.NOT_PROTECTED, 0, 0, 0, 0.11, Eligibility.ROOFTOP_PV),
        (GlobCover.RAINFED_CROPLANDS, ProtectedArea.PROTECTED, 0, 0, 0, 0,
         Eligibility.ONSHORE_WIND_AND_PV_FARMLAND_PROTECTED),
        (GlobCover.MOSAIC_FOREST, ProtectedArea.NOT_PROTECTED, 0, 0, 0, 0, Eligibility.ONSHORE_WIND_FOREST),
        (GlobCover.MOSAIC_FOREST, ProtectedArea.NOT_PROTECTED, 21, 0, 0, 0, Eligibility.NOT_ELIGIBLE),
        (GlobCover.MOSAIC_FOREST, ProtectedArea.NOT_PROTECTED, 0, 0, 0.11, 0, Eligibility.ROOFTOP_PV),
        (GlobCover.MOSAIC_FOREST, ProtectedArea.NOT_PROTECTED, 0, 0, 0, 0.11, Eligibility.ROOFTOP_PV),
        (GlobCover.MOSAIC_FOREST, ProtectedArea.PROTECTED, 0, 0, 0, 0,
         Eligibility.ONSHORE_WIND_FOREST_PROTECTED),
        (GlobCover.MOSAIC_GRASSLAND, ProtectedArea.PROTECTED, 0, 0, 0, 0,
         Eligibility.ONSHORE_WIND_AND_PV_OTHER_PROTECTED),
        (GlobCover.MOSAIC_GRASSLAND, ProtectedArea.PROTECTED, 4, 0, 0, 0, Eligibility.ONSHORE_WIND_OTHER_PROTECTED),
        (GlobCover.WATER_BODIES, ProtectedArea.NOT_PROTECTED, 0, 0, 0, 0, Eligibility.OFFSHORE_WIND),
        (GlobCover.WATER_BODIES, ProtectedArea.NOT_PROTECTED, 0, -51, 0, 0, Eligibility.NOT_ELIGIBLE),
        (GlobCover.WATER_BODIES, ProtectedArea.PROTECTED, 0, 0, 0, 0, Eligibility.OFFSHORE_WIND_PROTECTED),
        (GlobCover.ARTIFICAL_SURFACES_AND_URBAN_AREAS, ProtectedArea.NOT_PROTECTED, 0, 0, 0, 0,
         Eligibility.NOT_ELIGIBLE)

    ]
)
def test_eligibility(land_cover, protected_areas, slope, bathymetry, building_share, urban_green_share,
                     expected, config):
    result = _determine_eligibility(
        land_cover=np.array([land_cover]),
        protected_areas=np.array([protected_areas]),
        slope=np.array([slope]),
        bathymetry=np.array([bathymetry]),
        building_share=np.array([building_share]),
        urban_green_share=np.array([urban_green_share]),
        config=config
    )
    assert Eligibility(result[0]) == expected
