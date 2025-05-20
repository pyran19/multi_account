import math

import pytest

from src.core.state import State
from src.core.dp import expectation, best_action
from src.core.parameters import Parameters


@pytest.mark.parametrize(
    "n, ratings, expected",
    [
        (0, (1500, 1400), 1500),
        (1, (1500, 1500), 1508),  # レート期待値は適切に設定してください
    ],
)
def test_expectation_basic(n, ratings, expected):
    params = Parameters()
    state = State.from_iterable(ratings)
    assert expectation(n, state, params) == pytest.approx(expected)


def test_stop_is_best():
    """高レートが1つある場合、打ち切りが最適になる。"""
    params = Parameters()
    n = 3
    ratings = (1600, 1500)
    state = State.from_iterable(ratings)
    exp = expectation(n, state)
    assert exp == pytest.approx(1600)
    assert best_action(n, state, params) is None 