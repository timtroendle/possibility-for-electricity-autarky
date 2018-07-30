"""Quantify the constrained potentials for renewable power in regions.

Based on the unconstrained potentials and rules to constrain it.
"""
import click
import pandas as pd

from src.utils import Config
from src.eligible_land import Eligibility


@click.command()
@click.argument("path_to_unconstrained_potentials_prefer_pv")
@click.argument("path_to_unconstrained_potentials_prefer_wind")
@click.argument("path_to_result")
@click.argument("scenario")
@click.argument("config", type=Config())
def constrained_potentials(path_to_unconstrained_potentials_prefer_pv, path_to_unconstrained_potentials_prefer_wind,
                           path_to_result, scenario, config):
    unconstrained_prefer_pv = pd.read_csv(path_to_unconstrained_potentials_prefer_pv, index_col=0)
    unconstrained_prefer_wind = pd.read_csv(path_to_unconstrained_potentials_prefer_wind, index_col=0)

    constrained = _constrain_potential(unconstrained_prefer_pv, unconstrained_prefer_wind,
                                       config["scenarios"][scenario])
    constrained.to_csv(path_to_result, header=True)


def _constrain_potential(unconstrained_prefer_pv, unconstrained_prefer_wind, scenario_config):
    constrained_prefer_pv = pd.DataFrame(
        index=unconstrained_prefer_pv.index,
        data={eligibility.energy_column_name: _scaling_factor(eligibility, scenario_config, prefer_pv=True)
              for eligibility in Eligibility}
    ) * unconstrained_prefer_pv
    constrained_prefer_wind = pd.DataFrame(
        index=unconstrained_prefer_wind.index,
        data={eligibility.energy_column_name: _scaling_factor(eligibility, scenario_config, prefer_pv=False)
              for eligibility in Eligibility}
    ) * unconstrained_prefer_wind
    return constrained_prefer_pv.where(
        constrained_prefer_pv > constrained_prefer_wind,
        other=constrained_prefer_wind
    )


def _scaling_factor(eligibility, scenario_config, prefer_pv=True):
    # FIXME the handling of protected areas is conservative:
    # When protected forest cannot be used more due to the fact that forest in general cannot
    # be used, in the current implementation this "allowance" of using protected areas is lost.
    # In reality one might allow to use more of the other land in such a case.
    # Should I intend to make strong conclusions about protected areas, I will need to review
    # this approach (probably could be best solved with linear programming).
    share_protected_areas_used = scenario_config["share-protected-areas-used"]
    share_rooftops_used = scenario_config["share-rooftops-used"]
    share_other_land_used = scenario_config["share-other-land-used"]
    share_farmland_used = scenario_config["share-farmland-used"]
    share_forest_used_for_wind = scenario_config["share-forest-used-for-wind"]
    if prefer_pv:
        share_wind_pv_on_farmland = share_farmland_used if scenario_config["pv-on-farmland"] else 0
    else:
        share_wind_pv_on_farmland = share_farmland_used
    share_offshore_used = scenario_config["share-offshore-used"]
    return {
        Eligibility.NOT_ELIGIBLE: 0,
        Eligibility.ROOFTOP_PV: share_rooftops_used,
        Eligibility.ONSHORE_WIND_AND_PV_OTHER: share_other_land_used,
        Eligibility.ONSHORE_WIND_OTHER: share_other_land_used,
        Eligibility.ONSHORE_WIND_FARMLAND: share_farmland_used,
        Eligibility.ONSHORE_WIND_FOREST: share_forest_used_for_wind,
        Eligibility.ONSHORE_WIND_AND_PV_FARMLAND: share_wind_pv_on_farmland,
        Eligibility.OFFSHORE_WIND: share_offshore_used,
        Eligibility.ONSHORE_WIND_AND_PV_OTHER_PROTECTED: min(share_other_land_used, share_protected_areas_used),
        Eligibility.ONSHORE_WIND_OTHER_PROTECTED: min(share_other_land_used, share_protected_areas_used),
        Eligibility.ONSHORE_WIND_FARMLAND_PROTECTED: min(share_farmland_used, share_protected_areas_used),
        Eligibility.ONSHORE_WIND_FOREST_PROTECTED: min(share_forest_used_for_wind, share_protected_areas_used),
        Eligibility.ONSHORE_WIND_AND_PV_FARMLAND_PROTECTED: min(share_wind_pv_on_farmland, share_protected_areas_used),
        Eligibility.OFFSHORE_WIND_PROTECTED: min(share_offshore_used, share_protected_areas_used)
    }[eligibility]


if __name__ == "__main__":
    constrained_potentials()
