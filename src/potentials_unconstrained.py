"""Quantify the unconstrained potential of renewable power in regions."""
from datetime import timedelta

import click
import pandas as pd

from src.utils import Config
from src.eligible_land import Eligibility
from src.conversion import watt_to_watthours


@click.command()
@click.argument("path_to_eligibilities")
@click.argument("path_to_capacity_factors")
@click.argument("path_to_result_prefer_pv")
@click.argument("path_to_result_prefer_wind")
@click.argument("config", type=Config())
def potentials(path_to_eligibilities, path_to_capacity_factors, path_to_result_prefer_pv,
               path_to_result_prefer_wind, config):
    eligibilities = pd.read_csv(path_to_eligibilities, index_col=0)
    capacity_factors = pd.read_csv(path_to_capacity_factors, index_col=0)

    for prefer_pv, path_to_result in [(True, path_to_result_prefer_pv), (False, path_to_result_prefer_wind)]:
        max_capacities_tw = _max_capacity_tw(eligibilities, config, prefer_pv)
        max_generation_twh_per_year = _generation_per_year(max_capacities_tw, capacity_factors, prefer_pv)
        max_generation_twh_per_year.to_csv(path_to_result, header=True)


def _max_capacity_tw(eligibilities, config, prefer_pv):
    return pd.DataFrame({
        eligibility.area_column_name: (eligibilities[eligibility.area_column_name] *
                                       _power_density_watt_per_km2(eligibility, prefer_pv, config) /
                                       1e12)
        for eligibility in Eligibility
    })


def _generation_per_year(capacities, capacity_factors, prefer_pv):
    yield_assuming_full_power = watt_to_watthours(
        watt=capacities,
        duration=timedelta(days=365)
    )
    return pd.DataFrame({
        eligibility.energy_column_name: (yield_assuming_full_power[eligibility.area_column_name] *
                                         _capacity_factor(eligibility, prefer_pv, capacity_factors))
        for eligibility in Eligibility
    })


def _power_density_watt_per_km2(eligibility, prefer_pv, config):
    rooftop_pv = config["parameters"]["maximum-installable-power-density"]["rooftop-pv"] * 1e6
    onshore = config["parameters"]["maximum-installable-power-density"]["onshore-wind"] * 1e6
    offshore = config["parameters"]["maximum-installable-power-density"]["offshore-wind"] * 1e6
    if prefer_pv:
        wind_and_pv = wind_and_pv = config["parameters"]["maximum-installable-power-density"]["pv-farm"] * 1e6
    else:
        wind_and_pv = onshore
    return {
        Eligibility.NOT_ELIGIBLE: 0,
        Eligibility.ROOFTOP_PV: rooftop_pv,
        Eligibility.ONSHORE_WIND_AND_PV_OTHER: wind_and_pv,
        Eligibility.ONSHORE_WIND_OTHER: onshore,
        Eligibility.ONSHORE_WIND_FARMLAND: onshore,
        Eligibility.ONSHORE_WIND_FOREST: onshore,
        Eligibility.ONSHORE_WIND_AND_PV_FARMLAND: wind_and_pv,
        Eligibility.OFFSHORE_WIND: offshore,
        Eligibility.ONSHORE_WIND_AND_PV_OTHER_PROTECTED: wind_and_pv,
        Eligibility.ONSHORE_WIND_OTHER_PROTECTED: onshore,
        Eligibility.ONSHORE_WIND_FARMLAND_PROTECTED: onshore,
        Eligibility.ONSHORE_WIND_FOREST_PROTECTED: onshore,
        Eligibility.ONSHORE_WIND_AND_PV_FARMLAND_PROTECTED: wind_and_pv,
        Eligibility.OFFSHORE_WIND_PROTECTED: offshore
    }[eligibility]


def _capacity_factor(eligibility, prefer_pv, capacity_factors):
    rooftop_pv = capacity_factors.loc[:, "pv_capacity_factor"]
    onshore = capacity_factors.loc[:, "onshore_capacity_factor"]
    offshore = capacity_factors.loc[:, "offshore_capacity_factor"]
    if prefer_pv:
        wind_and_pv = capacity_factors.loc[:, "pv_capacity_factor"]
    else:
        wind_and_pv = onshore
    return {
        Eligibility.NOT_ELIGIBLE: 0,
        Eligibility.ROOFTOP_PV: rooftop_pv,
        Eligibility.ONSHORE_WIND_AND_PV_OTHER: wind_and_pv,
        Eligibility.ONSHORE_WIND_OTHER: onshore,
        Eligibility.ONSHORE_WIND_FARMLAND: onshore,
        Eligibility.ONSHORE_WIND_FOREST: onshore,
        Eligibility.ONSHORE_WIND_AND_PV_FARMLAND: wind_and_pv,
        Eligibility.OFFSHORE_WIND: offshore,
        Eligibility.ONSHORE_WIND_AND_PV_OTHER_PROTECTED: wind_and_pv,
        Eligibility.ONSHORE_WIND_OTHER_PROTECTED: onshore,
        Eligibility.ONSHORE_WIND_FARMLAND_PROTECTED: onshore,
        Eligibility.ONSHORE_WIND_FOREST_PROTECTED: onshore,
        Eligibility.ONSHORE_WIND_AND_PV_FARMLAND_PROTECTED: wind_and_pv,
        Eligibility.OFFSHORE_WIND_PROTECTED: offshore
    }[eligibility]


if __name__ == "__main__":
    potentials()
