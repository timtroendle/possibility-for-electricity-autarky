"""Determines maximal capacities for renewables."""
import click
import numpy as np
import pandas as pd
import rasterio

from src.technical_eligibility import Eligibility
from src.utils import Config


@click.command()
@click.argument("path_to_eligibility_categories")
@click.argument("path_to_eligible_areas")
@click.argument("path_to_statistical_roof_model")
@click.argument("path_to_pv_prio_result")
@click.argument("path_to_wind_prio_result")
@click.argument("config", type=Config())
def determine_capacities(path_to_eligibility_categories, path_to_eligible_areas, path_to_statistical_roof_model,
                         path_to_pv_prio_result, path_to_wind_prio_result, config):
    """Determines maximal capacities for renewables."""
    with rasterio.open(path_to_eligible_areas) as src:
        meta = src.meta
        areas = src.read(1)
    with rasterio.open(path_to_eligibility_categories) as src:
        eligibility_categories = src.read(1)
    flat_roof_share = pd.read_csv(path_to_statistical_roof_model).set_index("orientation").loc[
        "flat", "share_of_roof_areas"
    ]
    capacities_pv_prio = _determine_capacities(areas, eligibility_categories, config, flat_roof_share, pv_prio=True)
    capacities_wind_prio = _determine_capacities(areas, eligibility_categories, config, flat_roof_share, pv_prio=False)
    _write_to_file(path_to_pv_prio_result, capacities_pv_prio, meta)
    _write_to_file(path_to_wind_prio_result, capacities_wind_prio, meta)


def _determine_capacities(areas, eligibility_categories, config, flat_roof_share, pv_prio):
    capacities = np.zeros_like(areas)
    for eligibility in Eligibility:
        mask = eligibility_categories == eligibility
        power_density_mw_per_km2 = _power_density_mw_per_km2(
            eligibility=eligibility,
            pv_prio=pv_prio,
            flat_roof_share=flat_roof_share,
            config=config
        )
        capacities[mask] = areas[mask] * power_density_mw_per_km2
    return capacities


def _power_density_mw_per_km2(eligibility, pv_prio, flat_roof_share, config):
    maximum_installable_power_density = config["parameters"]["maximum-installable-power-density"]
    rooftop_pv = (maximum_installable_power_density["pv-on-flat-areas"] * flat_roof_share +
                  maximum_installable_power_density["pv-on-tilted-roofs"] * (1 - flat_roof_share))
    onshore = maximum_installable_power_density["onshore-wind"]
    offshore = maximum_installable_power_density["offshore-wind"]
    if pv_prio:
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


def _write_to_file(path_to_file, capacities, meta):
    with rasterio.open(path_to_file, 'w', **meta) as new_geotiff:
        new_geotiff.write(capacities, 1)


if __name__ == "__main__":
    determine_capacities()
