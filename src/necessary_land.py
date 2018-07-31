"""Determine the fration of non-built-up land area needed to become autarkic."""
import click
import pandas as pd

from src.potentials_constrained import _constrain_potential, _scaling_factor
from src.eligibility import Eligibility

ZERO_DEMAND = 0.000001

SCENARIO_CONFIG = {
    "share-protected-areas-used": 1,
    "pv-on-farmland": False,
    "share-farmland-used": 1,
    "share-forest-used-for-wind": 1,
    "share-other-land-used": 1,
    "share-offshore-used": 0,
    "share-rooftops-used": 1
}


@click.command()
@click.argument("path_to_demand")
@click.argument("path_to_eligibility")
@click.argument("path_to_unconstrained_potentials_prefer_pv")
@click.argument("path_to_unconstrained_potentials_prefer_wind")
@click.argument("path_to_built_up_share")
@click.argument("path_to_output")
@click.argument("share_from_pv", type=click.INT)
def necessary_land(path_to_demand, path_to_eligibility, path_to_unconstrained_potentials_prefer_pv,
                   path_to_unconstrained_potentials_prefer_wind, path_to_built_up_share,
                   path_to_output, share_from_pv=100):
    """Determine the fration of non-built-up land area needed to become autarkic.

    Can vary the share of demand satisfied by rooftop PV.

    Ignores offshore as it distorts total area sizes.
    """
    assert share_from_pv <= 100
    assert share_from_pv >= 0
    share_from_pv = share_from_pv / 100
    demand = pd.read_csv(path_to_demand, index_col=0)["demand_twh_per_year"]
    unconstrained_potentials_prefer_pv = pd.read_csv(path_to_unconstrained_potentials_prefer_pv, index_col=0)
    unconstrained_potentials_prefer_wind = pd.read_csv(path_to_unconstrained_potentials_prefer_wind, index_col=0)
    eligibility = pd.read_csv(path_to_eligibility, index_col=0)
    built_up_share = pd.read_csv(path_to_built_up_share, index_col=0)["bu_mean"]

    constrained_potential = _constrain_potential(unconstrained_potentials_prefer_pv,
                                                 unconstrained_potentials_prefer_wind, SCENARIO_CONFIG)
    constrained_eligibility = _constrain_eligibility(eligibility, SCENARIO_CONFIG)
    pv = constrained_potential.eligibility_rooftop_pv_twh_per_year.where(
        constrained_potential.eligibility_rooftop_pv_twh_per_year < share_from_pv * demand,
        share_from_pv * demand
    )
    demand_after_rooftops = demand - pv
    assert (demand_after_rooftops >= 0).all()
    constrained_potential_without_rooftops = constrained_potential.copy()
    del constrained_potential_without_rooftops["eligibility_rooftop_pv_twh_per_year"]
    constrained_potential_without_rooftops = constrained_potential_without_rooftops.sum(axis=1)
    factor_available_land = (demand_after_rooftops / constrained_potential_without_rooftops)
    del constrained_eligibility["eligibility_offshore_wind_km2"]
    del constrained_eligibility["eligibility_offshore_wind_protected_km2"]
    del constrained_eligibility["eligibility_rooftop_pv_km2"]
    necessary_land = constrained_eligibility.sum(axis=1) * factor_available_land
    del eligibility["eligibility_offshore_wind_km2"]
    del eligibility["eligibility_offshore_wind_protected_km2"]
    assert (built_up_share.max() <= 1).all()
    assert (built_up_share.min() >= 0).all()
    non_built_up_land = (1 - built_up_share) * eligibility.sum(axis=1)
    fraction_non_built_land = necessary_land / non_built_up_land
    # corner cases
    fraction_non_built_land[constrained_potential_without_rooftops == 0] = 1 # otherwise will be nan
    fraction_non_built_land[demand_after_rooftops < ZERO_DEMAND] = 0 # otherwise will be nan

    fraction_non_built_land[fraction_non_built_land > 1] = 1
    fraction_non_built_land.rename("fraction non-built-up land necessary").to_csv(
        path_to_output,
        index=True,
        header=True
    )


def _constrain_eligibility(eligibilities, scenario_config):
    constrained_prefer_pv = pd.DataFrame(
        index=eligibilities.index,
        data={eligibility.area_column_name: _scaling_factor(eligibility, scenario_config, prefer_pv=True)
              for eligibility in Eligibility}
    ) * eligibilities
    constrained_prefer_wind = pd.DataFrame(
        index=eligibilities.index,
        data={eligibility.area_column_name: _scaling_factor(eligibility, scenario_config, prefer_pv=False)
              for eligibility in Eligibility}
    ) * eligibilities
    return constrained_prefer_pv.where(
        constrained_prefer_pv > constrained_prefer_wind,
        other=constrained_prefer_wind
    )


if __name__ == "__main__":
    necessary_land()
