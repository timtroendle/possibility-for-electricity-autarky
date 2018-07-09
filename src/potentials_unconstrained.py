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
    roof_pv_capacity_factor_correction_factor = _orientation_and_tilt_correction_factor(roof_statistics, config)

    for prefer_pv, path_to_result in [(True, path_to_result_prefer_pv), (False, path_to_result_prefer_wind)]:
        max_capacities_tw = _max_capacity_tw(eligibilities, config, prefer_pv, flat_roof_share)
        max_generation_twh_per_year = _generation_per_year(max_capacities_tw, capacity_factors,
                                                           roof_pv_capacity_factor_correction_factor, prefer_pv)
        max_generation_twh_per_year.to_csv(path_to_result, header=True)


def _max_capacity_tw(eligibilities, config, prefer_pv, flat_roof_share):
    return pd.DataFrame({
        eligibility.area_column_name: (eligibilities[eligibility.area_column_name] *
                                       _power_density_mw_per_km2(eligibility, prefer_pv, flat_roof_share, config) /
                                       1e6)
        for eligibility in Eligibility
    })


def _generation_per_year(capacities, capacity_factors, roof_pv_capacity_factor_correction_factor, prefer_pv):
    yield_assuming_full_power = watt_to_watthours(
        watt=capacities,
        duration=timedelta(days=365)
    )
    return pd.DataFrame({
        eligibility.energy_column_name: (yield_assuming_full_power[eligibility.area_column_name] *
                                         _capacity_factor(eligibility, prefer_pv, capacity_factors,
                                                          roof_pv_capacity_factor_correction_factor))
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


def _capacity_factor(eligibility, prefer_pv, capacity_factors, roof_pv_capacity_factor_correction_factor):
    rooftop_pv = capacity_factors.loc[:, "pv_capacity_factor"] * roof_pv_capacity_factor_correction_factor
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


def _orientation_and_tilt_correction_factor(roof_statistics, config):
    # FIXME This should stem from the simulated data.
    # This factor assumes the capacity factor for PV is based on southwards facing PV plants.
    # It therefore returns a factor to be applied to the capacity factor that takes into
    # account that not all roofs are southwards facing. It takes the shares from the
    # statistical model and applies factors which are average reduction factors observed in
    # the renewables.ninja simulations. For example: on average in Europe, all northwards
    # facing roofs of all tilts have an energy output that is ~0.66 of the output of a south-
    # wards facing roof.
    shares = roof_statistics.groupby("orientation")["share of roof areas"].sum()
    assert math.isclose(shares.sum(), 1)
    # First, we need to correct the shares. The are valid area shares. But now we are dealing
    # with installable capacity, and there is less capacity available on flat roofs. Hence we
    # reduce the flat share accordingly and renormalise the shares.
    corrected_shares = shares.copy()
    maximum_installable_power_density = config["parameters"]["maximum-installable-power-density"]
    flat_capacity_correction = (maximum_installable_power_density["pv-on-flat-areas"] /
                                maximum_installable_power_density["pv-on-tilted-roofs"])
    assert flat_capacity_correction > 0
    assert flat_capacity_correction < 1
    corrected_shares["flat"] = corrected_shares["flat"] * flat_capacity_correction
    corrected_shares = corrected_shares / corrected_shares.sum()
    assert math.isclose(corrected_shares.sum(), 1)
    assert corrected_shares["flat"] < shares["flat"]
    cp_correction = pd.Series(index=corrected_shares.index) # FIXME these should come from simulations
    cp_correction["S"] = 1
    cp_correction["flat"] = 1 # flat roofs are facing south
    cp_correction["N"] = 0.66380420362320351
    cp_correction["E"] = 0.8080722273127737
    cp_correction["W"] = 0.8627391732891946
    correction_factor = (cp_correction * shares).sum()
    assert correction_factor > 0
    assert correction_factor < 1
    return correction_factor


if __name__ == "__main__":
    potentials()
