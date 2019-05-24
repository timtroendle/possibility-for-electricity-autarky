"""Determine the fration of non-built-up land area needed to become autarkic."""
import click
import pandas as pd
import geopandas as gpd

from src.potentials import Potential


@click.command()
@click.argument("path_to_demand")
@click.argument("path_to_potential")
@click.argument("path_to_footprint")
@click.argument("path_to_built_up_area")
@click.argument("path_to_units")
@click.argument("path_to_output")
@click.argument("share_from_pv", type=click.INT)
def necessary_land(path_to_demand, path_to_potential, path_to_footprint, path_to_built_up_area,
                   path_to_units, path_to_output, share_from_pv=100):
    """Determine the fraction of non-built-up land area needed to become autarkic.

    Can vary the share of demand satisfied by rooftop PV.

    Ignores offshore as it distorts total area sizes.
    """
    assert share_from_pv <= 100
    assert share_from_pv >= 0
    share_from_pv = share_from_pv / 100
    demand = pd.read_csv(path_to_demand, index_col=0)["demand_twh_per_year"]
    potentials = pd.read_csv(path_to_potential, index_col=0)
    footprint = pd.read_csv(path_to_footprint, index_col=0)
    built_up_area = pd.read_csv(path_to_built_up_area, index_col=0)
    country_codes = gpd.read_file(path_to_units).set_index("id")["country_code"]

    rooftop_pv = potentials[str(Potential.ROOFTOP_PV)].where(
        potentials[str(Potential.ROOFTOP_PV)] < share_from_pv * demand,
        share_from_pv * demand
    )
    demand_after_rooftops = demand - rooftop_pv
    assert (demand_after_rooftops >= 0).all()

    open_field_potential = potentials[str(Potential.ONSHORE_WIND)] + potentials[str(Potential.OPEN_FIELD_PV)]
    open_field_footprint = footprint[Potential.ONSHORE_WIND.area_name] + footprint[Potential.OPEN_FIELD_PV.area_name]
    fraction_non_built_up_land = fraction_land_where_potential_exists(
        open_field_potential=open_field_potential,
        open_field_footprint=open_field_footprint,
        built_up_area=built_up_area,
        demand_after_rooftops=demand_after_rooftops
    )
    fraction_non_built_up_land.where(
        fraction_non_built_up_land.notna(),
        fraction_land_where_no_potential_exists(
            open_field_potential=open_field_potential,
            open_field_footprint=open_field_footprint,
            built_up_area=built_up_area,
            demand_after_rooftops=demand_after_rooftops,
            country_codes=country_codes
        ),
        inplace=True
    )
    # corner cases
    fraction_non_built_up_land[fraction_non_built_up_land > 1] = 1

    pd.DataFrame(
        index=fraction_non_built_up_land.index,
        data={
            "fraction_non_built_up_land_necessary": fraction_non_built_up_land,
            "fraction_roofs_necessary": rooftop_pv / potentials[str(Potential.ROOFTOP_PV)],
            "rooftop_pv_generation_twh_per_year": rooftop_pv
        }
    ).to_csv(
        path_to_output,
        index=True,
        header=True
    )


def fraction_land_where_potential_exists(open_field_potential, open_field_footprint,
                                         built_up_area, demand_after_rooftops):
    share_of_open_field_potential_necessary = demand_after_rooftops / open_field_potential
    necessary_land = open_field_footprint * share_of_open_field_potential_necessary
    return necessary_land / built_up_area["non_built_up_km2"]


def fraction_land_where_no_potential_exists(open_field_potential, open_field_footprint, built_up_area,
                                            demand_after_rooftops, country_codes):
    factor = open_field_footprint.groupby(country_codes).sum() / open_field_potential.groupby(country_codes).sum()
    factor.name = "km2_per_twh_nationally"
    assert (factor > 10).all()
    assert (factor < 70).all()
    factor = pd.DataFrame(country_codes).join(factor.rename("factor"), on="country_code")["factor"]
    necessary_land = demand_after_rooftops * factor
    return necessary_land / built_up_area["non_built_up_km2"]


if __name__ == "__main__":
    necessary_land()
