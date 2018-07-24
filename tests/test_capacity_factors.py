import math

import pandas as pd

from src.capacity_factors_demand import average_capacity_factor


def test_average_capacity_factor():
    cap_factors = pd.Series([1.0, 0.0])
    demands = pd.Series([2 / 3, 1 / 3])
    expected_average = 2 / 3
    assert math.isclose(average_capacity_factor(cap_factors, demands), expected_average)
