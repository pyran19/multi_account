"""シミュレーション結果の可視化モジュール。"""
from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
from typing import List, Optional, Tuple

from src.simulator.simulation import SimulationResult
from src.core.parameters import Parameters

def plot_rating_distributions(results: List[SimulationResult], params: Parameters, title: Optional[str] = None):
    """複数のポリシーの最終レート分布をヒストグラムで表示する。

    Args:
        results: シミュレーション結果のリスト
        title: グラフのタイトル（省略可）
    """
    plt.figure(figsize=(10, 6))
    
    # 各ポリシーの結果をヒストグラムで表示
    for result in results:
        plt.hist(
            result.ratings,
            bins=15,
            alpha=0.5,
            label=f"{result.policy_name} (mean={result.mean_rating:.1f})",
        )
    
    # グラフの設定
    plt.xlabel("最終レート")
    plt.ylabel("頻度")
    plt.title(title or "ポリシー別レート分布")
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    return plt


def plot_rating_comparison(results: List[SimulationResult], params: Parameters, title: Optional[str] = None):
    """複数のポリシーの最終レート平均値と標準偏差を棒グラフで比較する。

    Args:
        results: シミュレーション結果のリスト
        title: グラフのタイトル（省略可）
    """
    plt.figure(figsize=(10, 6))
    
    # データ準備
    policies = [result.policy_name for result in results]
    means = [result.mean_rating for result in results]
    stds = [result.std_rating for result in results]
    
    # 棒グラフ
    x = np.arange(len(policies))
    width = 0.6
    
    plt.bar(x, means, width, yerr=stds, capsize=5, alpha=0.7)
    
    # グラフの設定
    plt.xlabel("ポリシー")
    plt.ylabel("最終レート")
    plt.title(title or "ポリシー比較")
    plt.xticks(x, policies)
    plt.ylim(params.mu - 100, max(means) + 100)
    plt.grid(True, alpha=0.3, axis="y")
    
    # 平均値を表示
    for i, mean in enumerate(means):
        plt.text(i, mean + stds[i] + 1, f"{mean:.1f}", ha="center")
    
    return plt


def save_plots(results: List[SimulationResult], params: Parameters, prefix: str = "sim_result"):
    """シミュレーション結果のグラフを保存する。

    Args:
        results: シミュレーション結果のリスト
        params:  シミュレーションのパラメータ
        prefix: 保存するファイル名のプレフィックス
    """
    # 初期レートと最大試合数の情報を取得（全結果で共通）
    initial_ratings = results[0].initial_ratings
    max_matches = results[0].max_matches
    
    # タイトル生成
    base_title_info = f"Initial: {initial_ratings}, Max Matches: {max_matches}"
    
    # 分布プロット
    title_dist = f"レート分布\n{base_title_info}"
    dist_plot = plot_rating_distributions(results, params, title=title_dist)
    dist_plot.savefig(f"{prefix}_distribution.png", dpi=300, bbox_inches="tight")
    
    # 比較プロット
    title_comp = f"ポリシー比較\n{base_title_info}"
    comp_plot = plot_rating_comparison(results, params, title=title_comp)
    comp_plot.savefig(f"{prefix}_comparison.png", dpi=300, bbox_inches="tight")
    
    plt.close("all")
    
    return [f"{prefix}_distribution.png", f"{prefix}_comparison.png"]