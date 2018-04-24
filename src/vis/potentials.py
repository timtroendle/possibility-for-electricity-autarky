"""Visualise the theoretic potential of all renewable power technologies."""
from datetime import timedelta

import click
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import seaborn as sns

from src.utils import Config
from src.eligible_land import Eligibility
from src.conversion import watt_to_watthours


@click.command()
@click.argument("path_to_regions")
@click.argument("path_to_cps")
@click.argument("path_to_plot")
@click.argument("config", type=Config())
def potentials(path_to_regions, path_to_cps, path_to_plot, config):
    """Visualise the theoretic potential of all renewable power technologies."""
    sns.set_context('paper')
    regions = gpd.read_file(path_to_regions)
    cps = pd.read_csv(path_to_cps, index_col=0)

    data = pd.Series(
        index=pd.MultiIndex.from_product([
            regions.country_code.unique(),
            ["rooftop-pv", "pv-farm", "onshore wind", "offshore wind"]
        ], names=["country_code", "tech"]),
        name="normed yield"
    )
    for country in regions.country_code.unique():
        potentials = _potentials(regions[regions.country_code == country], config, cps.loc[country])
        for tech in ["rooftop-pv", "pv-farm", "onshore wind", "offshore wind"]:
            data.loc[country, tech] = potentials[tech]

    fig = plt.figure(figsize=(8, 6))
    ax = fig.add_subplot(111)
    ax.set_yscale("log")
    sns.stripplot(
        data=data.reset_index(),
        y="normed yield",
        x="tech",
        jitter=True,
        ax=ax
    )
    ax.axhline(1, color="r", linewidth=0.75, label="national demand")
    ax.set_ylabel("yield relative to national demand [-]")
    fig.savefig(path_to_plot, dpi=300)


def _potentials(regions, config, cps):
    def __normed_yield(technology, eligibility, cp):
        return _normed_yield(config, technology, regions[eligibility.property_name].sum(), cp, demand_twh_per_year)

    demand_twh_per_year = regions["demand_twh_per_year"].sum()
    return {
        "rooftop-pv": __normed_yield(
            "rooftop-pv",
            Eligibility.ROOFTOP_PV,
            cps.loc["pv_capacity_factor"]
        ),
        "pv-farm": __normed_yield(
            "pv-farm",
            Eligibility.ONSHORE_WIND_OR_PV_FARM,
            cps.loc["pv_capacity_factor"]
        ),
        "onshore wind": (
            __normed_yield(
                "onshore-wind",
                Eligibility.ONSHORE_WIND_FARM,
                cps.loc["onshore_capacity_factor"]
            ) + __normed_yield(
                "onshore-wind",
                Eligibility.ONSHORE_WIND_OR_PV_FARM,
                cps.loc["onshore_capacity_factor"]
            )
        ),
        "offshore wind": __normed_yield(
            "offshore-wind",
            Eligibility.OFFSHORE_WIND_FARM,
            cps.loc["offshore_capacity_factor"]
        )
    }


def _normed_yield(config, technology, area_km2, cp, demand_twh_per_year):
    return _yield_twh_per_year(config, technology, area_km2, cp) / demand_twh_per_year


def _yield_twh_per_year(config, technology, area_km2, cp):
    specific_energy_yield_w_per_m2 = config["parameters"]["maximum-installable-power-density"][technology] * cp
    specific_energy_yield_w_per_km2 = specific_energy_yield_w_per_m2 * 1e6
    specific_energy_yield_twh_per_year_per_km2 = watt_to_watthours(
        specific_energy_yield_w_per_km2 / 1e12,
        timedelta(days=365)
    )
    return specific_energy_yield_twh_per_year_per_km2 * area_km2


if __name__ == "__main__":
    potentials()
