"""共通パラメータとユーティリティ関数を定義するモジュール。

シミュレーションと DP で共通して扱う定数・関数をここに集約する。
"""
from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "RATING_STEP",
    "K_COEFF",
    "MU",
    "win_prob",
    "Parameters",
]

# ---------------------------
# 基本定数
# ---------------------------

RATING_STEP: int = 16  # 1 試合あたりのレート変動幅 d
K_COEFF: float = 1.0 / 800  # 勝率の線形近似で使う傾き k (デフォルト 800 レート差→勝率±0.5)
MU: int = 1500  # プレイヤーの適正レート（中央値）

# ---------------------------
# 勝率関数
# ---------------------------

def win_prob(rating: float, *, k: float = K_COEFF, mu: float = MU) -> float:
    """現在レート ``rating`` のアカウントが勝つ確率 ``p`` を返す。

    p(r) = 0.5 - k * (r - mu)
    上式が 0~1 に収まるようクリップする。
    """
    p = 0.5 - k * (rating - mu)
    # クリップ (0, 1) 範囲外になるケースは超低/高レートのみ想定
    if p < 0.0:
        return 0.0
    if p > 1.0:
        return 1.0
    return p


# ---------------------------
# まとめて扱いたい場合の dataclass
# ---------------------------

@dataclass(frozen=True)
class Parameters:
    """パラメータセットをまとめたクラス (任意更新用)。"""

    rating_step: int = RATING_STEP
    k_coeff: float = K_COEFF
    mu: float = MU

    def win_prob(self, rating: float) -> float:  # noqa: D401
        """``win_prob`` のインスタンスバージョン。"""
        return win_prob(rating, k=self.k_coeff, mu=self.mu) 