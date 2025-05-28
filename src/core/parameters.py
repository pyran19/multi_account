"""共通パラメータとユーティリティ関数を定義するモジュール。

シミュレーションと DP で共通して扱う定数・関数をここに集約する。
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Tuple

__all__ = [
    "RATING_STEP",
    "K_COEFF",
    "MU",
    "win_prob",
    "Parameters",
    "float_to_int_rating",
    "int_to_float_rating",
]

# ---------------------------
# 基本定数
# ---------------------------



RATING_STEP: int = 16  # 1 試合あたりのレート変動幅 d
K_COEFF: float = math.log(10) / 1600  # 勝率の線形近似で使う傾き k (デフォルト ln10/1600 レート差→勝率±0.5)
MU: int = 1500  # プレイヤーの適正レート（中央値）

# ---------------------------
# レート変換関数
# 事故の元なのでこちらはimportしない。paramsを引数で受け取ってそのメソッドから呼ぶ。
# ---------------------------

def float_to_int_rating(float_rating: float, mu: float = MU, step: int = RATING_STEP) -> int:
    """浮動小数点レートを整数レートに変換する
    
    整数レートは「適正レートμから何回勝ったか」を表す整数値。
    """
    return round((float_rating - mu) / step)

def int_to_float_rating(int_rating: int, mu: float = MU, step: int = RATING_STEP) -> float:
    """整数レートを浮動小数点レートに変換する"""
    return mu + int_rating * step

def float_ratings_to_int(float_ratings: Tuple[float, ...], mu: float = MU, step: int = RATING_STEP) -> Tuple[int, ...]:
    """複数の浮動小数点レートを整数レートに変換する"""
    return tuple(float_to_int_rating(r, mu, step) for r in float_ratings)

def int_ratings_to_float(int_ratings: Tuple[int, ...], mu: float = MU, step: int = RATING_STEP) -> Tuple[float, ...]:
    """複数の整数レートを浮動小数点レートに変換する"""
    return tuple(int_to_float_rating(r, mu, step) for r in int_ratings)

# ---------------------------
# 勝率関数
# 外部関数で直接インポートしない
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
    
    def float_to_int_rating(self, float_rating: float) -> int:
        """浮動小数点レートを整数レートに変換する"""
        return float_to_int_rating(float_rating, mu=self.mu, step=self.rating_step)
    
    def int_to_float_rating(self, int_rating: int) -> float:
        """整数レートを浮動小数点レートに変換する"""
        return int_to_float_rating(int_rating, mu=self.mu, step=self.rating_step)
    
    def float_ratings_to_int(self, float_ratings: Tuple[float, ...]) -> Tuple[int, ...]:
        """複数の浮動小数点レートを整数レートに変換する"""
        return float_ratings_to_int(float_ratings, mu=self.mu, step=self.rating_step)
    
    def int_ratings_to_float(self, int_ratings: Tuple[int, ...]) -> Tuple[float, ...]:
        """複数の整数レートを浮動小数点レートに変換する"""
        return int_ratings_to_float(int_ratings, mu=self.mu, step=self.rating_step) 