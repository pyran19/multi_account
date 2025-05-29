"""
動的計画法のラッパー関数

整数レート形式での入出力を提供します。
"""

from typing import List
from .dp import expectation
from .state import State
from .parameters import Parameters


def evaluate_multi_account_expected_rating(n: int, int_ratings: List[int]) -> List[float]:
    """
    複数アカウントの期待値を計算
    
    Args:
        n: 残り試合数
        int_ratings: 各アカウントの整数レート（適正レートを0とした相対値）
        
    Returns:
        各アカウントの期待値（整数レート形式）のリスト
    """
    params = Parameters()
    state = State(tuple(int_ratings))
    
    # 全体の期待値を計算
    total_expectation = expectation(n, state, params)
    
    # 各アカウントの期待値を計算
    # 簡易的に、現在のレート + (全体期待値 - 現在の最高レート) の比例配分
    current_max = max(int_ratings)
    improvement = total_expectation - current_max
    
    # 各アカウントの期待値を計算
    expected_ratings = []
    for rating in int_ratings:
        # 簡易的な実装：現在のレートに改善分を加える
        # より精密な実装が必要な場合は後で修正
        if rating == current_max:
            expected_ratings.append(total_expectation)
        else:
            # 他のアカウントは現在のレートに比例した改善を加える
            expected_ratings.append(rating + improvement * 0.5)
    
    return expected_ratings 