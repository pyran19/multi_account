"""
グラフ描画モジュール

x-Pプロットの描画機能を提供します。
各アカウントは異なる色で表示され、見やすいグラフを生成します。
"""

import matplotlib.pyplot as plt
import matplotlib.cm as cm
import numpy as np
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
import seaborn as sns


class ExperimentPlotter:
    """実験結果のグラフ描画クラス"""
    
    def __init__(self, style: str = "seaborn-v0_8", font_size: int = 12):
        """
        プロッターの初期化
        
        Args:
            style: matplotlibのスタイル
            font_size: フォントサイズ
        """
        plt.style.use(style)
        plt.rcParams['font.size'] = font_size
        plt.rcParams['font.family'] = ['DejaVu Sans', 'Yu Gothic', 'Meiryo', 'sans-serif']
        
        # カラーパレットの設定
        self.colors = sns.color_palette("husl", n_colors=10)
    
    def plot_xp(self, x_values: List[float], p_values: List[List[float]], 
                v1_values: List[float],
                x_label: str = "x", title: Optional[str] = None,
                save_path: Optional[str] = None,
                figsize: Tuple[int, int] = (10, 6),
                show_grid: bool = True,
                show_legend: bool = True,
                y_label: str = "期待レート増分（vs 打ち切り）",
                line_style: str = '-o') -> plt.Figure:
        """
        x-Pプロットを描画（期待値と最大レートの差分をプロット）
        
        Args:
            x_values: xの値のリスト
            p_values: 各アカウントの期待値リスト（2次元配列）
            v1_values: 最大レート（v1）の値のリスト
            x_label: x軸のラベル
            title: グラフのタイトル
            save_path: 保存先のパス（Noneの場合は保存しない）
            figsize: 図のサイズ
            show_grid: グリッドを表示するか
            show_legend: 凡例を表示するか
            y_label: y軸のラベル
            line_style: 線のスタイル
            
        Returns:
            作成したFigureオブジェクト
        """
        fig, ax = plt.subplots(figsize=figsize)
        
        # アカウント数を取得
        account_count = len(p_values[0]) if p_values else 0
        
        # 各アカウントのデータをプロット（期待値 - 最大レートの差分）
        for i in range(account_count):
            p_i_values = [p_row[i] for p_row in p_values]
            # 期待値から最大レートを引いた差分を計算
            diff_values = [p_i - v1 for p_i, v1 in zip(p_i_values, v1_values)]
            
            color = self.colors[i % len(self.colors)]
            
            ax.plot(x_values, diff_values, line_style, 
                   color=color, 
                   label=f'アカウント{i+1}',
                   markersize=6,
                   linewidth=2,
                   alpha=0.8)
        
        # 水平線（y=0）を追加して打ち切り基準線を示す
        ax.axhline(y=0, color='gray', linestyle='--', alpha=0.5, 
                   label='打ち切り基準線')
        
        # 軸ラベルとタイトルの設定
        ax.set_xlabel(x_label, fontsize=14)
        ax.set_ylabel(y_label, fontsize=14)
        
        if title:
            ax.set_title(title, fontsize=16, pad=20)
        else:
            ax.set_title(f'{x_label}-{y_label}プロット', fontsize=16, pad=20)
        
        # グリッドの表示
        if show_grid:
            ax.grid(True, alpha=0.3, linestyle='--')
        
        # 凡例の表示
        if show_legend:
            ax.legend(loc='best', framealpha=0.9)
        
        # レイアウトの調整
        plt.tight_layout()
        
        # ファイルへの保存
        if save_path:
            fig.savefig(save_path, dpi=300, bbox_inches='tight')
        
        return fig
    
    def plot_xp_comparison(self, datasets: List[Dict[str, Any]], 
                          comparison_label: str = "条件",
                          save_path: Optional[str] = None,
                          figsize: Tuple[int, int] = (12, 8)) -> plt.Figure:
        """
        複数のx-Pプロットを比較表示
        
        Args:
            datasets: 各データセットの辞書のリスト
                      各辞書は以下のキーを含む:
                      - 'x_values': xの値のリスト
                      - 'p_values': 期待値の2次元配列
                      - 'label': データセットのラベル
                      - 'x_label': x軸のラベル（オプション）
            comparison_label: 比較条件のラベル
            save_path: 保存先のパス
            figsize: 図のサイズ
            
        Returns:
            作成したFigureオブジェクト
        """
        account_count = len(datasets[0]['p_values'][0])
        num_datasets = len(datasets)
        
        fig, axes = plt.subplots(1, account_count, figsize=figsize, sharey=True)
        if account_count == 1:
            axes = [axes]
        
        # 各アカウントごとにサブプロットを作成
        for i, ax in enumerate(axes):
            for j, dataset in enumerate(datasets):
                x_values = dataset['x_values']
                p_i_values = [p_row[i] for p_row in dataset['p_values']]
                color = self.colors[j % len(self.colors)]
                
                ax.plot(x_values, p_i_values, '-o',
                       color=color,
                       label=dataset['label'],
                       markersize=5,
                       linewidth=2,
                       alpha=0.8)
            
            ax.set_title(f'アカウント{i+1}', fontsize=14)
            ax.set_xlabel(dataset.get('x_label', 'x'), fontsize=12)
            if i == 0:
                ax.set_ylabel('期待レート（整数形式）', fontsize=12)
            
            ax.grid(True, alpha=0.3, linestyle='--')
            
            if i == account_count - 1:
                ax.legend(title=comparison_label, loc='best', framealpha=0.9)
        
        plt.suptitle('アカウント別期待値の比較', fontsize=16, y=1.02)
        plt.tight_layout()
        
        if save_path:
            fig.savefig(save_path, dpi=300, bbox_inches='tight')
        
        return fig
    
    def plot_heatmap(self, x_values: List[float], y_values: List[float],
                    z_values: List[List[float]], 
                    x_label: str = "x", y_label: str = "y",
                    title: str = "ヒートマップ",
                    save_path: Optional[str] = None,
                    figsize: Tuple[int, int] = (10, 8),
                    cmap: str = 'viridis') -> plt.Figure:
        """
        2パラメータの影響をヒートマップで表示
        
        Args:
            x_values: x軸の値
            y_values: y軸の値
            z_values: z値の2次元配列
            x_label: x軸のラベル
            y_label: y軸のラベル
            title: グラフのタイトル
            save_path: 保存先のパス
            figsize: 図のサイズ
            cmap: カラーマップ
            
        Returns:
            作成したFigureオブジェクト
        """
        fig, ax = plt.subplots(figsize=figsize)
        
        # データを numpy 配列に変換
        Z = np.array(z_values)
        
        # ヒートマップの作成
        im = ax.imshow(Z, cmap=cmap, aspect='auto', 
                      extent=[min(x_values), max(x_values), 
                              min(y_values), max(y_values)],
                      origin='lower')
        
        # カラーバーの追加
        cbar = plt.colorbar(im, ax=ax)
        cbar.set_label('期待値', fontsize=12)
        
        # 軸ラベルとタイトル
        ax.set_xlabel(x_label, fontsize=14)
        ax.set_ylabel(y_label, fontsize=14)
        ax.set_title(title, fontsize=16, pad=20)
        
        plt.tight_layout()
        
        if save_path:
            fig.savefig(save_path, dpi=300, bbox_inches='tight')
        
        return fig
    
    @staticmethod
    def close_all():
        """すべての図を閉じる"""
        plt.close('all') 