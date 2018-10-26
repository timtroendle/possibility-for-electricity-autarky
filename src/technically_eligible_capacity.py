"""Determines maximal capacities for renewables."""
import click
import rasterio

from src.technical_eligibility import Eligibility
from src.utils import Config


@click.command()
@click.argument("path_to_eligible_areas")
@click.argument("path_to_result")
@click.argument("config", type=Config())
def determine_capacities(path_to_eligible_areas, path_to_result, config):
    """Determines maximal capacities for renewables."""
    with rasterio.open(path_to_eligible_areas) as src:
        meta = src.meta
    with rasterio.open(path_to_result, 'w', **meta) as new_geotiff:
        for id, eligibility in enumerate(Eligibility, start=1):
            power_density_mw_per_km2 = _power_density_mw_per_km2(
                eligibility=eligibility,
                prefer_pv=True, # FIXME create both
                flat_roof_share=0.3, # FIXME take from stats model
                config=config
            )
            with rasterio.open(path_to_eligible_areas) as src:
                new_geotiff.write(src.read(id * power_density_mw_per_km2, id))


def _power_density_mw_per_km2(eligibility, prefer_pv, flat_roof_share, config):
    maximum_installable_power_density = config["parameters"]["maximum-installable-power-density"]
    rooftop_pv = (maximum_installable_power_density["pv-on-flat-areas"] * flat_roof_share +
                  maximum_installable_power_density["pv-on-tilted-roofs"] * (1 - flat_roof_share))
    onshore = maximum_installable_power_density["onshore-wind"]
    offshore = maximum_installable_power_density["offshore-wind"]
    if prefer_pv:
        wind_and_pv = maximum_installable_power_density["pv-on-flat-areas"]
    else:
        wind_and_pv = onshore
    return {
        Eligibility.NOT_ELIGIBLE: 0,
        Eligibility.ROOFTOP_PV: rooftop_pv,
        Eligibility.ONSHORE_WIND_AND_PV: wind_and_pv,
        Eligibility.ONSHORE_WIND: onshore,
        Eligibility.OFFSHORE_WIND: offshore
    }[eligibility]


if __name__ == "__main__":
    determine_capacities()
