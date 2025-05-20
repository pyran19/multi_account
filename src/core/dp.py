"""逐次動的計画法 (DP) による期待値計算。"""
from __future__ import annotations

from functools import lru_cache
from typing import Tuple, Optional

from .state import State
from .parameters import Parameters

__all__ = [
    "expectation",
    "best_action",
]


# ---------------------------
# メイン関数: 期待値
# ---------------------------

@lru_cache(maxsize=None)
def _expectation_cached(n: int, ratings: Tuple[float, ...], params: Parameters) -> float:
    """内部用キャッシュ付き期待値計算関数。"""
    state = State(ratings)

    # 基底ケース: これ以上試合が無い (終了)
    if n == 0:
        return state.best

    # アクション1: ここで終了する (stop) — 期待値は現在の最大レート
    best_value: float = state.best

    # アクション2: いずれかのアカウントで試合を行う
    for idx, rating in enumerate(state):
        p = params.win_prob(rating)
        # 勝利時・敗北時の次状態
        next_win = state.after_match(idx, won=True, step=params.rating_step)
        next_lose = state.after_match(idx, won=False, step=params.rating_step)

        exp = p * _expectation_cached(n - 1, next_win.ratings, params) + (
            1.0 - p
        ) * _expectation_cached(n - 1, next_lose.ratings, params)

        if exp > best_value:
            best_value = exp

    return best_value


def expectation(n: int, state: State | Tuple[float, ...], params: Parameters) -> float:  # noqa: D401
    """公開 API: 指定状態・残り試合数での最終レート期待値を返す。"""
    ratings = state.ratings if isinstance(state, State) else tuple(sorted(state, reverse=True))
    return _expectation_cached(n, ratings, params)


# ---------------------------
# 最適アクション
# ---------------------------

def best_action(n: int, state: State, params: Parameters) -> Optional[int]:
    """最適アクションを返す。

    戻り値:
        * `None` — 今すぐ終了するのが最適
        * `int`  — そのインデックスのアカウントで潜るのが最適
    """
    if n == 0:
        return None  # もう打つ手なし

    best_value: float = state.best
    best_idx: Optional[int] = None

    for idx, rating in enumerate(state):
        p = params.win_prob(rating)
        next_win = state.after_match(idx, won=True, step=params.rating_step)
        next_lose = state.after_match(idx, won=False, step=params.rating_step)
        exp = p * expectation(n - 1, next_win, params) + (1 - p) * expectation(
            n - 1, next_lose, params
        )
        if exp > best_value:
            best_value = exp
            best_idx = idx

    return best_idx 