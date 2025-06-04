"""
動的計画法のラッパー関数

整数レート形式での入出力を提供します。
"""

from typing import List
from .dp import expectation, get_expected_values_for_each_action # Import added
from .state import State
from .parameters import Parameters


def get_expected_values_per_action(n: int, int_ratings: List[int]) -> List[float]: # Renamed and signature updated
    """
    各アカウントで試合を行った場合の期待値を計算します。

    Args:
        n: 残り試合数。
        int_ratings: 各アカウントの整数レート（適正レートを0とした相対値）のリスト。
        
    Returns:
        期待値のリスト。各要素 i は、アカウント i で1試合行った場合の
        最終的な整数レートの期待値に対応します。
    """
    params = Parameters()
    state = State(tuple(int_ratings))
    
    # dpモジュールの新しい関数を呼び出す
    action_expectations = get_expected_values_for_each_action(n, state, params)
    
    return action_expectations