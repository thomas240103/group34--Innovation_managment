"""Concentration measures on the two toy sectors of Step 2, and the Wilson interval of Step 0."""
import numpy as np
import pytest

from measures import concentration_ratio, gini, herfindahl, six_measures, wilson


def test_equal_firms():
    m = six_measures([5] * 10)
    assert m["CR4 (%)"] == pytest.approx(40.0)
    assert m["1/HH"] == pytest.approx(10.0)
    assert m["Gini"] == pytest.approx(0.0)


def test_one_giant():
    x = [91] + [1] * 9
    assert concentration_ratio(x, 4) == pytest.approx(94.0)
    assert 1 / herfindahl(x) == pytest.approx(1.206, abs=1e-3)
    assert gini(x) == pytest.approx(0.81, abs=1e-3)


def test_wilson_of_the_accepted_sample():
    lo, hi = wilson(37, 40)
    assert (round(lo, 3), round(hi, 3)) == (0.801, 0.974)
    assert np.isnan(wilson(0, 0)[0])
