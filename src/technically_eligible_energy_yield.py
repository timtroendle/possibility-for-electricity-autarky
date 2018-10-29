"""Determines maximal energy yield for renewables."""
from datetime import timedelta

import click
import numpy as np
import rasterio

from src.technical_eligibility import Eligibility
from src.conversion import watt_to_watthours


@click.command()
@click.argument("path_to_eligibility_categories")
@click.argument("path_to_capacities_pv_prio")
@click.argument("path_to_capacities_wind_prio")
@click.argument("path_to_pv_prio_result")
@click.argument("path_to_wind_prio_result")
def determine_energy_yield(path_to_eligibility_categories, path_to_capacities_pv_prio, path_to_capacities_wind_prio,
                           path_to_pv_prio_result, path_to_wind_prio_result):
    """Determines maximal energy yield for renewables."""
    with rasterio.open(path_to_capacities_pv_prio) as src:
        meta = src.meta
        capacity_pv_prio_mw = src.read(1)
    with rasterio.open(path_to_capacities_wind_prio) as src:
        capacity_wind_prio_mw = src.read(1)
    with rasterio.open(path_to_eligibility_categories) as src:
        eligibility_categories = src.read(1)
    rooftop_cf = watt_to_watthours(0.15, duration=timedelta(days=365)) # FIXME should be a map
    open_field_pv_cf = watt_to_watthours(0.2, duration=timedelta(days=365)) # FIXME should be a map
    wind_cf = watt_to_watthours(0.25, duration=timedelta(days=365)) # FIXME should be a map
    energy_yield_pv_prio = _determine_energy_yield(
        capacity_mw=capacity_pv_prio_mw,
        eligibility_category=eligibility_categories,
        rooftop_cf=rooftop_cf,
        open_field_pv_cf=open_field_pv_cf,
        wind_cf=wind_cf,
        pv_prio=True
    )
    energy_yield_wind_prio = _determine_energy_yield(
        capacity_mw=capacity_wind_prio_mw,
        eligibility_category=eligibility_categories,
        rooftop_cf=rooftop_cf,
        open_field_pv_cf=open_field_pv_cf,
        wind_cf=wind_cf,
        pv_prio=False
    )
    _write_to_file(path_to_pv_prio_result, energy_yield_pv_prio, meta)
    _write_to_file(path_to_wind_prio_result, energy_yield_wind_prio, meta)


def _determine_energy_yield(capacity_mw, eligibility_category, rooftop_cf, open_field_pv_cf, wind_cf, pv_prio):
    energy_yield_twh = np.zeros_like(capacity_mw)
    for eligibility in Eligibility:
        cf = _capacity_factor(eligibility, pv_prio, rooftop_cf, open_field_pv_cf, wind_cf)
        mask = eligibility_category == eligibility
        energy_yield_twh[mask] = (capacity_mw * cf)[mask] / 1e6
    return energy_yield_twh


def _capacity_factor(eligibility, pv_prio, rooftop_cf, open_field_pv_cf, wind_cf):
    return {
        Eligibility.NOT_ELIGIBLE: 0,
        Eligibility.ROOFTOP_PV: rooftop_cf,
        Eligibility.ONSHORE_WIND_AND_PV: open_field_pv_cf if pv_prio else wind_cf,
        Eligibility.ONSHORE_WIND: wind_cf,
        Eligibility.OFFSHORE_WIND: wind_cf
    }[eligibility]


def _write_to_file(path_to_file, energy_yield, meta):
    if "transform" in meta.keys():
        del meta["transform"] # this is to avoid a deprecation warning of rasterio < 1.0
    with rasterio.open(path_to_file, 'w', **meta) as new_geotiff:
        new_geotiff.write(energy_yield, 1)


if __name__ == "__main__":
    determine_energy_yield()
