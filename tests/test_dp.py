import math

import pytest

from src.core.state import State
from src.core.dp import expectation, best_action
from src.core.parameters import Parameters

@pytest.fixture
def params():
    return Parameters(
        rating_step=16,
        k_coeff=20,
        mu=1500,
    )


@pytest.mark.parametrize(
    "n, ratings, expected",
    [
        (0, (1500, 1400), 1500),
        (1, (1500, 1500), 1500),  # レート期待値は適切に設定してください
    ],
)
def test_expectation_basic(n, ratings, expected, params):
    state = State.from_iterable(ratings)
    assert expectation(n, state, params) == pytest.approx(expected)


def test_stop_is_best(params):
    """高レートが1つある場合、打ち切りが最適になる。"""
    n = 3
    ratings = (1600, 1500)
    state = State.from_iterable(ratings)
    exp = expectation(n, state, params)
    assert exp == pytest.approx(1600)
    assert best_action(n, state, params) is None 