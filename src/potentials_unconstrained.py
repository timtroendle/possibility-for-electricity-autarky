"""Quantify the unconstrained potential of renewable power in regions."""
from datetime import timedelta
import math

import click
import pandas as pd

from src.utils import Config
from src.eligible_land import Eligibility
from src.conversion import watt_to_watthours


@click.command()
@click.argument("path_to_eligibilities")
@click.argument("path_to_capacity_factors")
@click.argument("path_to_statistical_roof_model")
@click.argument("path_to_result_prefer_pv")
@click.argument("path_to_result_prefer_wind")
@click.argument("config", type=Config())
def potentials(path_to_eligibilities, path_to_capacity_factors, path_to_statistical_roof_model,
               path_to_result_prefer_pv, path_to_result_prefer_wind, config):
    eligibilities = pd.read_csv(path_to_eligibilities, index_col=0)
    capacity_factors = pd.read_csv(path_to_capacity_factors, index_col=0)
    roof_statistics = pd.read_csv(path_to_statistical_roof_model)
    flat_roof_share = roof_statistics.set_index("orientation").loc[
        "flat", "share of roof areas"
    ]
    share_of_flat_installed_power = _share_of_flat_installed_power(roof_statistics, config)

    for prefer_pv, path_to_result in [(True, path_to_result_prefer_pv), (False, path_to_result_prefer_wind)]:
        max_capacities_tw = _max_capacity_tw(eligibilities, config, prefer_pv, flat_roof_share)
        max_generation_twh_per_year = _generation_per_year(max_capacities_tw, capacity_factors,
                                                           share_of_flat_installed_power, prefer_pv)
        max_generation_twh_per_year.to_csv(path_to_result, header=True)


def _max_capacity_tw(eligibilities, config, prefer_pv, flat_roof_share):
    return pd.DataFrame({
        eligibility.area_column_name: (eligibilities[eligibility.area_column_name] *
                                       _power_density_mw_per_km2(eligibility, prefer_pv, flat_roof_share, config) /
                                       1e6)
        for eligibility in Eligibility
    })


def _generation_per_year(capacities, capacity_factors, share_of_flat_installed_power, prefer_pv):
    yield_assuming_full_power = watt_to_watthours(
        watt=capacities,
        duration=timedelta(days=365)
    )
    return pd.DataFrame({
        eligibility.energy_column_name: (yield_assuming_full_power[eligibility.area_column_name] *
                                         _capacity_factor(eligibility, prefer_pv, capacity_factors,
                                                          share_of_flat_installed_power))
        for eligibility in Eligibility
    })


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


def _capacity_factor(eligibility, prefer_pv, capacity_factors, share_of_flat_installed_power):
    rooftop_pv = (capacity_factors.loc[:, "flat_pv_capacity_factor"] * share_of_flat_installed_power +
                  capacity_factors.loc[:, "tilted_pv_capacity_factor"] * (1 - share_of_flat_installed_power))
    onshore = capacity_factors.loc[:, "onshore_capacity_factor"]
    offshore = capacity_factors.loc[:, "offshore_capacity_factor"]
    if prefer_pv:
        wind_and_pv = capacity_factors.loc[:, "flat_pv_capacity_factor"]
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


def _share_of_flat_installed_power(roof_statistics, config):
    # The roof statistics tell us the share of flat area to all area. What is the share of
    # installed power of flat area to installed power on all area?
    shares = roof_statistics.groupby("orientation")["share of roof areas"].sum()
    assert math.isclose(shares.sum(), 1)
    power_shares = shares.copy()
    maximum_installable_power_density = config["parameters"]["maximum-installable-power-density"]
    flat_capacity_correction = (maximum_installable_power_density["pv-on-flat-areas"] /
                                maximum_installable_power_density["pv-on-tilted-roofs"])
    assert flat_capacity_correction > 0
    assert flat_capacity_correction < 1
    power_shares["flat"] = power_shares["flat"] * flat_capacity_correction
    power_shares = power_shares / power_shares.sum()
    assert math.isclose(power_shares.sum(), 1)
    assert power_shares["flat"] < shares["flat"]
    return power_shares["flat"]


if __name__ == "__main__":
    potentials()
