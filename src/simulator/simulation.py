"""モンテカルロシミュレーションを実行するモジュール。"""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import List, Optional, Tuple

import numpy as np

from src.core.parameters import Parameters, win_prob, int_to_float_rating
from src.core.state import State
from src.simulator.policy import Policy


@dataclass
class SimulationResult:
    """シミュレーション結果を保持するクラス。"""

    mean_rating: float  # 平均最終レート（実数表記）
    std_rating: float  # 標準偏差（実数表記）
    min_rating: float  # 最小値（実数表記）
    max_rating: float  # 最大値（実数表記）
    ratings: List[float]  # 全エピソードの結果リスト（実数表記）
    policy_name: str  # 使用したポリシー名
    initial_ratings: List[float]  # 初期レート（実数表記）
    max_matches: int  # 最大試合数

    def __str__(self) -> str:
        """人間が読みやすい形式で結果を表示する。"""
        return (
            f"Policy: {self.policy_name}\n"
            f"Initial ratings: {self.initial_ratings}\n"
            f"Max matches: {self.max_matches}\n"
            f"Results over {len(self.ratings)} episodes:\n"
            f"  Mean final rating: {self.mean_rating:.2f}\n"
            f"  Std dev: {self.std_rating:.2f}\n"
            f"  Min: {self.min_rating:.2f}\n"
            f"  Max: {self.max_rating:.2f}"
        )


class Simulator:
    """シミュレーションを実行するクラス。"""

    def __init__(self, policy: Policy, params: Parameters = Parameters()):
        """初期化。

        Args:
            policy: 使用するアカウント選択ポリシー
            params: シミュレーションパラメータ
        """
        self.policy = policy
        self.params = params

    def run_episode(self, initial_state: State, max_matches: int) -> float:
        """1エピソード（1シーズン）をシミュレーションし、最終的な最高レートを返す。

        Args:
            initial_state: 初期レート状態（整数レート形式）
            max_matches: 最大試合数

        Returns:
            最終的な最高レート（実数レート形式）
        """
        state = initial_state
        remaining_matches = max_matches

        while remaining_matches > 0:
            # ポリシーからアカウント選択
            account_idx = self.policy.select_account(state, remaining_matches)

            # None が返された場合は終了
            if account_idx is None:
                break

            # 選択されたアカウントでの勝率計算（整数レート→実数レート変換）
            int_rating = state[account_idx]
            float_rating = self.params.int_to_float_rating(int_rating)
            p_win = self.params.win_prob(float_rating)

            # 勝敗決定
            won = random.random() < p_win

            # 状態更新
            state = state.after_match(account_idx, won, step=1)  # 整数の場合step=1固定
            remaining_matches -= 1

        # 最終的な最高レートを返す（実数レート形式）
        return self.params.int_to_float_rating(state.best)

    def run_simulation(
        self, initial_state: State, max_matches: int, episodes: int
    ) -> SimulationResult:
        """複数エピソードを実行し、結果を集計する。

        Args:
            initial_state: 初期レート状態（整数レート形式）
            max_matches: 最大試合数
            episodes: シミュレーションするエピソード数

        Returns:
            シミュレーション結果
        """
        results = []

        for _ in range(episodes):
            final_rating = self.run_episode(initial_state, max_matches)
            results.append(final_rating)

        # 統計量の計算
        results_array = np.array(results)
        mean_rating = np.mean(results_array)
        std_rating = np.std(results_array)
        min_rating = np.min(results_array)
        max_rating = np.max(results_array)

        # 初期レートは実数表現に戻して保存
        float_initial_ratings = [self.params.int_to_float_rating(r) for r in initial_state.ratings]

        return SimulationResult(
            mean_rating=mean_rating,
            std_rating=std_rating,
            min_rating=min_rating,
            max_rating=max_rating,
            ratings=results,
            policy_name=self.policy.name,
            initial_ratings=list(float_initial_ratings),
            max_matches=max_matches,
        )


def compare_policies(
    policies: List[Policy],
    initial_state: State,
    max_matches: int,
    episodes: int,
    params: Parameters = Parameters(),
) -> List[SimulationResult]:
    """複数のポリシーを比較する。

    Args:
        policies: 比較するポリシーのリスト
        initial_state: 初期レート状態
        max_matches: 最大試合数
        episodes: シミュレーションするエピソード数
        params: シミュレーションパラメータ

    Returns:
        各ポリシーのシミュレーション結果のリスト
    """
    results = []

    for policy in policies:
        simulator = Simulator(policy, params)
        result = simulator.run_simulation(initial_state, max_matches, episodes)
        results.append(result)

    return results