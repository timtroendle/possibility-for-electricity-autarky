"""Allocate eez eligibilities to administrative units."""
from textwrap import dedent

import click
import pandas as pd

from eligibility import Eligibility

OFFSHORE_ELIGIBILITIES = [Eligibility.OFFSHORE_WIND.area_column_name,
                          Eligibility.OFFSHORE_WIND_PROTECTED.area_column_name]
REL_TOLERANCE = 0.005 # 0.5 %
ABS_TOLERANCE = 5 # km^2


@click.command()
@click.argument("path_to_eez_eligibility")
@click.argument("path_to_shared_coasts")
@click.argument("path_to_output")
def allocate_eezs(path_to_eez_eligibility, path_to_shared_coasts, path_to_output):
    """Allocate eez eligibilities to administrative units.

    How much offshore eligibility of a certain eez goes to which unit?
    I simply allocate offshore eligibility to all units that share a coast with
    the eez. The allocation is proportional to the lenght of the shared coastself.
    """
    eez_eligibilities = pd.read_csv(path_to_eez_eligibility, index_col=0)[OFFSHORE_ELIGIBILITIES]
    eez_eligibilities.index = eez_eligibilities.index.map(str)
    shared_coasts = pd.read_csv(path_to_shared_coasts, index_col=0)
    result = pd.DataFrame(
        data=shared_coasts.dot(eez_eligibilities),
        columns=OFFSHORE_ELIGIBILITIES
    )

    result.to_csv(path_to_output, header=True)


def _test_allocation(eez_eligibilities, result):
    total_offshore = eez_eligibilities.sum().sum()
    total_allocated = result.sum().sum()
    below_rel_threshold = abs(total_allocated - total_offshore) < total_offshore * REL_TOLERANCE
    below_abs_threshold = abs(total_allocated - total_offshore) < ABS_TOLERANCE
    below_any_threshold = below_rel_threshold | below_abs_threshold
    assert below_any_threshold,\
        dedent("""Allocated offshore eligibility differs more than {}% and more than {} km^2. Allocated was:
        {}

        Real offshore eligibility is:
        {}

        """.format(REL_TOLERANCE * 100,
                   ABS_TOLERANCE,
                   total_allocated,
                   total_offshore))


if __name__ == "__main__":
    allocate_eezs()
