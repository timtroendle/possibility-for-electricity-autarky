"""Module to fix population data."""
import warnings

import click
import pandas as pd

from eligible_land import GlobCover

WATER_THRESHOLD = 0.9 # regions above this threshold are considered pure water bodies
POPULATION_THRESHOLD = 0.001 # share of population that can be removed

WATER = f"lc_{GlobCover.WATER_BODIES.value}"
NOT_WATER = [f"lc_{x.value}" for x in GlobCover if x is not GlobCover.WATER_BODIES]


@click.command()
@click.argument("path_to_land_cover_data")
def fix_population(path_to_land_cover_data):
    """Fixes population data.

    (1) Removes nans, which can occur when regions are too small to cover a population raster.
    (2) Removes population living in water bodies.

    Implemented as a filter which reads from stdin and writes to stdout.
    """
    population = pd.read_csv(click.get_text_stream('stdin'))
    population = _fillna(population)
    population = _remove_water_bodies(population, pd.read_csv(path_to_land_cover_data))
    population.to_csv(click.get_text_stream('stdout'), header=True)


def _fillna(population):
    population["population_sum"] = pd.to_numeric(population["population_sum"], errors="coerce")
    return population.fillna(0.0)


def _remove_water_bodies(population, land_cover):
    data = land_cover.merge(population, on="id").fillna(0.0)
    data["water"] = data[WATER]
    data["not_water"] = data[NOT_WATER].sum(axis=1)
    data["rel_water"] = data["water"] / (data["not_water"] + data["water"])
    invalid_mask = (data["proper"] == 0) & (data["rel_water"] > WATER_THRESHOLD)
    invalid_population = data.loc[invalid_mask, "population_sum"].sum()
    if invalid_population > 0:
        warnings.warn(f"Removing {invalid_population:.0f} people because they are in water bodies.")
    assert invalid_population < POPULATION_THRESHOLD * data["population_sum"].sum()
    data.loc[invalid_mask, "population_sum"] = 0.0
    return data.set_index("id")["population_sum"]


if __name__ == "__main__":
    fix_population()
