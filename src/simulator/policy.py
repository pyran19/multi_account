"""アカウント選択ポリシーを定義するモジュール。

各種戦略（最適、ランダム、固定など）を実装する。
"""
from __future__ import annotations

import random
from abc import ABC, abstractmethod
from typing import Optional

from src.core.dp import best_action
from src.core.state import State
from src.core.parameters import Parameters


class Policy(ABC):
    """アカウント選択ポリシーの抽象基底クラス。"""
    def __init__(self, params: Parameters):
        self.params = params

    @abstractmethod
    def select_account(self, state: State, remaining_matches: int) -> Optional[int]:
        """現在の状態と残り試合数から、次にプレイするアカウントのインデックスを選択する。

        Args:
            state: 現在のレート状態（整数レート形式）
            remaining_matches: 残り試合数

        Returns:
            選択したアカウントのインデックス。None の場合は終了（打ち止め）を意味する。
        """
        pass

    @property
    def name(self) -> str:
        """ポリシーの名前を返す。"""
        return self.__class__.__name__


class OptimalPolicy(Policy):
    """DPの結果に基づく最適戦略。"""
    def __init__(self, params: Parameters):
        super().__init__(params)

    def select_account(self, state: State, remaining_matches: int) -> Optional[int]:
        """最適なアカウント選択を行う。

        Args:
            state: 現在のレート状態（整数レート形式）
            remaining_matches: 残り試合数

        Returns:
            選択したアカウントのインデックス。None の場合は終了（打ち止め）を意味する。
        """
        return best_action(remaining_matches, state, self.params)


class RandomPolicy(Policy):
    """ランダム選択戦略（ベースライン）。"""

    def __init__(self, params: Parameters, stop_prob: float = 0.0):
        """初期化。

        Args:
            stop_prob: 各ステップで終了する確率。デフォルトは 0（終了しない）。
        """
        super().__init__(params)
        self.stop_prob = stop_prob

    def select_account(self, state: State, remaining_matches: int) -> Optional[int]:
        """ランダムにアカウントを選択する。

        Args:
            state: 現在のレート状態（整数レート形式）
            remaining_matches: 残り試合数

        Returns:
            選択したアカウントのインデックス。None の場合は終了（打ち止め）を意味する。
        """
        if remaining_matches <= 0:
            return None

        # stop_prob の確率で終了
        if random.random() < self.stop_prob:
            return None

        # ランダムにアカウントを選択
        return random.randint(0, state.accounts - 1)


class FixedPolicy(Policy):
    """固定アカウント戦略（ベースライン）。"""

    def __init__(self, params: Parameters, account_idx: int = 0):
        """初期化。

        Args:
            account_idx: 常に使用するアカウントのインデックス。デフォルトは 0（最高レートのアカウント）。
        """
        super().__init__(params)
        self.account_idx = account_idx

    def select_account(self, state: State, remaining_matches: int) -> Optional[int]:
        """常に同じアカウントを選択する。

        Args:
            state: 現在のレート状態（整数レート形式）
            remaining_matches: 残り試合数

        Returns:
            選択したアカウントのインデックス。None の場合は終了（打ち止め）を意味する。
        """
        if remaining_matches <= 0:
            return None

        # インデックスが範囲外の場合は最後のアカウントを使用
        if self.account_idx >= state.accounts:
            return state.accounts - 1

        return self.account_idx

    @property
    def name(self) -> str:
        """ポリシーの名前を返す。"""
        return f"{self.__class__.__name__} (ranking={self.account_idx+1})"


class GreedyPolicy(Policy):
    """貪欲戦略（ベースライン）。

    現在最も低いレートのアカウントを選択する（勝率が高いため）。
    """
    def __init__(self, params: Parameters):
        super().__init__(params)
    def select_account(self, state: State, remaining_matches: int) -> Optional[int]:
        """最も低いレートのアカウントを選択する。

        Args:
            state: 現在のレート状態（整数レート形式）
            remaining_matches: 残り試合数

        Returns:
            選択したアカウントのインデックス。None の場合は終了（打ち止め）を意味する。
        """
        if remaining_matches <= 0:
            return None

        # 最も低いレートのアカウントのインデックスを返す
        return state.accounts - 1  # ratings は降順ソートされているため