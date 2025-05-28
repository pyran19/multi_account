"""レート状態を表現するクラス。"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple, Iterable, Union

__all__ = ["State"]


@dataclass(frozen=True)
class State:
    """アカウントのレートを保持する不変オブジェクト。

    * ratings は降順 (最大→最小) のタプルとして保持。
    * 不変なのでハッシュ可能、memo 化に使える。
    * 内部では整数レート（適正レートμからの勝ち数）を使用。
    * そもそも一貫して整数レートを使用するのでこのファイル内で実数レートとの区別は出ない
    """

    ratings: Tuple[int, ...]  # 整数レート（適正レートからの勝ち数）
    # ---------------------------
    # ファクトリ
    # ---------------------------
    @classmethod
    def from_iterable(cls, ratings: Iterable[int]) -> "State":
        """Iterable から生成し、内部で降順ソートする。
        
        Args:
            ratings: レートのイテラブル
        """
        return cls(tuple(sorted(ratings, reverse=True)))

    # ---------------------------
    # プロパティ
    # ---------------------------

    @property
    def best(self) -> int:
        """現在の最大レート (= ratings[0])"""
        return self.ratings[0]

    @property
    def accounts(self) -> int:
        """アカウント数"""
        return len(self.ratings)

    # ---------------------------
    # 状態遷移
    # ---------------------------

    def after_match(self, idx: int, won: bool, step: int = 1) -> "State":
        """idx 番目のアカウントが勝利/敗北した後の新しい State を返す。
        """
        delta = step if won else -step
        new_ratings = list(self.ratings)
        new_ratings[idx] += delta
        return State.from_iterable(new_ratings)

    # ---------------------------
    # 便利メソッド
    # ---------------------------

    def __iter__(self):  # noqa: D401
        return iter(self.ratings)

    def __len__(self):  # noqa: D401
        return len(self.ratings)

    def __getitem__(self, item):  # noqa: D401
        return self.ratings[item]

    def __str__(self):
        return f"State({', '.join(map(str, self.ratings))})"

    def __repr__(self):
        return f"State({', '.join(map(repr, self.ratings))})" 