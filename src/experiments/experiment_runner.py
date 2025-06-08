"""
実験実行モジュール

x-Pプロット実験を簡単に実行するためのヘルパー関数とクラスを提供します。
"""

import numpy as np
from typing import List, Dict, Any, Tuple, Optional, Callable
from pathlib import Path
import sys

# プロジェクトのルートをPythonパスに追加
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.core.dp_wrapper import get_expected_values_per_action # MODIFIED: Import updated
from src.experiments.data_manager import ExperimentDataManager
from src.experiments.plotting import ExperimentPlotter


class ExperimentRunner:
    """実験実行クラス"""
    
    def __init__(self, data_manager: Optional[ExperimentDataManager] = None,
                 plotter: Optional[ExperimentPlotter] = None):
        """
        実験ランナーの初期化
        
        Args:
            data_manager: データ管理オブジェクト
            plotter: グラフ描画オブジェクト
        """
        self.data_manager = data_manager or ExperimentDataManager()
        self.plotter = plotter or ExperimentPlotter()
    
    def generate_equal_interval_rates(self, v0: int, dv: int, r: int) -> List[int]:
        """
        等間隔のレート配列を生成（降順）
        実験計画書の仕様に従い、v₁=v₀, v₂=v₀-dv, v₃=v₀-2dv, ..., vᵣ=v₀-(r-1)dv
        
        Args:
            v0: ベースラインレート（最大レート）
            dv: レート差
            r: アカウント数
            
        Returns:
            降順のレート配列
        """
        return [v0 - i * dv for i in range(r)]
    
    def run_n_p_experiment(self, n_values: List[int], v_rates: List[int],
                          experiment_name: Optional[str] = None,
                          save_results: bool = True,
                          show_cutoff_line: bool = False) -> Dict[str, Any]:
        """
        n-Pプロット実験を実行
        
        Args:
            n_values: 残り試合数nの値リスト
            v_rates: 各アカウントのレート配列
            experiment_name: 実験名（Noneの場合は自動生成）
            save_results: 結果を保存するか
            show_cutoff_line: 打ち切り基準線（v1-Pmax）を表示するか
            
        Returns:
            実験結果の辞書
        """
        p_values = []
        v1_values = []  # 最大レート（v1）を記録
        
        print(f"n-Pプロット実験を開始します...")
        print(f"アカウント数: {len(v_rates)}")
        print(f"レート分布: {v_rates}")
        print(f"n値の範囲: {min(n_values)} - {max(n_values)}")
        
        # 各n値に対して期待値を計算
        for n in n_values:
            # レート配列が降順になっているかチェックしてソート
            sorted_v_rates = sorted(v_rates, reverse=True)
            v1 = sorted_v_rates[0]  # 最大レート
            
            action_specific_expected_values = get_expected_values_per_action(n, sorted_v_rates)
            p_values.append(action_specific_expected_values)
            v1_values.append(v1)
            
            print(f"n={n}: レート{sorted_v_rates}, v1={v1} → 期待値{[f'{p:.2f}' for p in action_specific_expected_values]}")
        
        # Pmax値を計算（各行の期待値の最大値）
        pmax_values = [max(p_row) for p_row in p_values]
        
        # データの保存とグラフ描画
        results = {
            'x_values': n_values,
            'p_values': p_values,
            'v1_values': v1_values,
            'pmax_values': pmax_values,
            'x_label': '残り試合数 n',
            'x_type': 'n',
            'fixed_params': {'v_rates': v_rates}
        }
        
        if save_results:
            # CSVファイルの保存
            csv_path = self.data_manager.save_xp_data(
                n_values, p_values, v1_values, x_label='n'
            )
            csv_filename = Path(csv_path).name
            
            # グラフの生成と保存
            graph_filename = self.data_manager.generate_filename("xp", "png")
            graph_path = self.data_manager.graph_dir / graph_filename
            
            fig = self.plotter.plot_xp(
                n_values, p_values, v1_values, pmax_values,
                x_label='残り試合数 n',
                title='n-P プロット（期待値差分）',
                save_path=str(graph_path),
                show_cutoff_line=show_cutoff_line
            )
            
            # 設定ファイルの作成と保存
            config = self.data_manager.create_xp_config(
                csv_filename=csv_filename,
                graph_filename=graph_filename,
                account_count=len(v_rates),
                x_type='n',
                fixed_params={'v_rates': v_rates}
            )
            
            config_name = experiment_name or f"n_p_experiment_{self.data_manager.generate_filename('', '')[:-1]}"
            config_path = self.data_manager.save_experiment_config(config_name, config)
            
            results['csv_path'] = csv_path
            results['graph_path'] = str(graph_path)
            results['config_path'] = config_path
            
            print(f"\n結果を保存しました:")
            print(f"  CSV: {csv_filename}")
            print(f"  グラフ: {graph_filename}")
            print(f"  設定: {config_name}.json")
        
        return results
    
    def run_v0_p_experiment(self, v0_values: List[int], n: int, dv: int, r: int,
                           experiment_name: Optional[str] = None,
                           save_results: bool = True,
                           show_cutoff_line: bool = False) -> Dict[str, Any]:
        """
        v0-Pプロット実験を実行
        
        Args:
            v0_values: ベースラインレートv0の値リスト
            n: 残り試合数
            dv: レート差
            r: アカウント数
            experiment_name: 実験名
            save_results: 結果を保存するか
            show_cutoff_line: 打ち切り基準線（v1-Pmax）を表示するか
            
        Returns:
            実験結果の辞書
        """
        p_values = []
        v1_values = []  # 最大レート（v1）を記録
        
        print(f"v0-Pプロット実験を開始します...")
        print(f"アカウント数: {r}")
        print(f"残り試合数: {n}")
        print(f"レート差: {dv}")
        print(f"v0値の範囲: {min(v0_values)} - {max(v0_values)}")
        
        # 各v0値に対して期待値を計算
        for v0 in v0_values:
            v_rates = self.generate_equal_interval_rates(v0, dv, r)
            # 生成したレート配列は既に降順になっている
            v1 = v_rates[0]  # 最大レート（v0と同じ）
            
            action_specific_expected_values = get_expected_values_per_action(n, v_rates)
            p_values.append(action_specific_expected_values)
            v1_values.append(v1)
            
            print(f"v0={v0}: レート{v_rates}, v1={v1} → 期待値{[f'{p:.2f}' for p in action_specific_expected_values]}")
        
        # Pmax値を計算（各行の期待値の最大値）
        pmax_values = [max(p_row) for p_row in p_values]
        
        # データの保存とグラフ描画
        results = {
            'x_values': v0_values,
            'p_values': p_values,
            'v1_values': v1_values,
            'pmax_values': pmax_values,
            'x_label': 'ベースラインレート v0',
            'x_type': 'v0',
            'fixed_params': {'n': n, 'dv': dv, 'r': r}
        }
        
        if save_results:
            # CSVファイルの保存
            csv_path = self.data_manager.save_xp_data(
                v0_values, p_values, v1_values, x_label='v0'
            )
            csv_filename = Path(csv_path).name
            
            # グラフの生成と保存
            graph_filename = self.data_manager.generate_filename("xp", "png")
            graph_path = self.data_manager.graph_dir / graph_filename
            
            fig = self.plotter.plot_xp(
                v0_values, p_values, v1_values, pmax_values,
                x_label='ベースラインレート v0',
                title='v0-P プロット（期待値差分）',
                save_path=str(graph_path),
                show_cutoff_line=show_cutoff_line
            )
            
            # 設定ファイルの作成と保存
            config = self.data_manager.create_xp_config(
                csv_filename=csv_filename,
                graph_filename=graph_filename,
                account_count=r,
                x_type='v0',
                fixed_params={'n': n, 'dv': dv}
            )
            
            config_name = experiment_name or f"v0_p_experiment_{self.data_manager.generate_filename('', '')[:-1]}"
            config_path = self.data_manager.save_experiment_config(config_name, config)
            
            results['csv_path'] = csv_path
            results['graph_path'] = str(graph_path)
            results['config_path'] = config_path
            
            print(f"\n結果を保存しました:")
            print(f"  CSV: {csv_filename}")
            print(f"  グラフ: {graph_filename}")
            print(f"  設定: {config_name}.json")
        
        return results
    
    def run_dv_p_experiment(self, dv_values: List[int], n: int, v0: int, r: int,
                           experiment_name: Optional[str] = None,
                           save_results: bool = True,
                           show_cutoff_line: bool = False) -> Dict[str, Any]:
        """
        dv-Pプロット実験を実行
        
        Args:
            dv_values: レート差dvの値リスト
            n: 残り試合数
            v0: ベースラインレート
            r: アカウント数
            experiment_name: 実験名
            save_results: 結果を保存するか
            show_cutoff_line: 打ち切り基準線（v1-Pmax）を表示するか
            
        Returns:
            実験結果の辞書
        """
        p_values = []
        v1_values = []  # 最大レート（v1）を記録
        
        print(f"dv-Pプロット実験を開始します...")
        print(f"アカウント数: {r}")
        print(f"残り試合数: {n}")
        print(f"ベースラインレート: {v0}")
        print(f"dv値の範囲: {min(dv_values)} - {max(dv_values)}")
        
        # 各dv値に対して期待値を計算
        for dv in dv_values:
            v_rates = self.generate_equal_interval_rates(v0, dv, r)
            # 生成したレート配列は既に降順になっている
            v1 = v_rates[0]  # 最大レート（v0と同じ）
            
            action_specific_expected_values = get_expected_values_per_action(n, v_rates)
            p_values.append(action_specific_expected_values)
            v1_values.append(v1)
            
            print(f"dv={dv}: レート{v_rates}, v1={v1} → 期待値{[f'{p:.2f}' for p in action_specific_expected_values]}")
        
        # Pmax値を計算（各行の期待値の最大値）
        pmax_values = [max(p_row) for p_row in p_values]
        
        # データの保存とグラフ描画
        results = {
            'x_values': dv_values,
            'p_values': p_values,
            'v1_values': v1_values,
            'pmax_values': pmax_values,
            'x_label': 'レート差 dv',
            'x_type': 'dv',
            'fixed_params': {'n': n, 'v0': v0, 'r': r}
        }
        
        if save_results:
            # CSVファイルの保存
            csv_path = self.data_manager.save_xp_data(
                dv_values, p_values, v1_values, x_label='dv'
            )
            csv_filename = Path(csv_path).name
            
            # グラフの生成と保存
            graph_filename = self.data_manager.generate_filename("xp", "png")
            graph_path = self.data_manager.graph_dir / graph_filename
            
            fig = self.plotter.plot_xp(
                dv_values, p_values, v1_values, pmax_values,
                x_label='レート差 dv',
                title='dv-P プロット（期待値差分）',
                save_path=str(graph_path),
                show_cutoff_line=show_cutoff_line
            )
            
            # 設定ファイルの作成と保存
            config = self.data_manager.create_xp_config(
                csv_filename=csv_filename,
                graph_filename=graph_filename,
                account_count=r,
                x_type='dv',
                fixed_params={'n': n, 'v0': v0}
            )
            
            config_name = experiment_name or f"dv_p_experiment_{self.data_manager.generate_filename('', '')[:-1]}"
            config_path = self.data_manager.save_experiment_config(config_name, config)
            
            results['csv_path'] = csv_path
            results['graph_path'] = str(graph_path)
            results['config_path'] = config_path
            
            print(f"\n結果を保存しました:")
            print(f"  CSV: {csv_filename}")
            print(f"  グラフ: {graph_filename}")
            print(f"  設定: {config_name}.json")
        
        return results
    
    def run_custom_experiment(self, x_values: List[float],
                            param_generator: Callable[[float], Tuple[int, List[int]]],
                            x_label: str = "x",
                            x_type: str = "custom",
                            experiment_name: Optional[str] = None,
                            save_results: bool = True,
                            show_cutoff_line: bool = False) -> Dict[str, Any]:
        """
        カスタム実験を実行
        
        Args:
            x_values: xの値リスト
            param_generator: xの値から(n, v_rates)を生成する関数
            x_label: x軸のラベル
            x_type: xの種類
            experiment_name: 実験名
            save_results: 結果を保存するか
            show_cutoff_line: 打ち切り基準線（v1-Pmax）を表示するか
            
        Returns:
            実験結果の辞書
        """
        p_values = []
        v1_values = []  # 最大レート（v1）を記録
        fixed_params = {}
        
        print(f"カスタム実験 ({x_type}) を開始します...")
        print(f"x値の範囲: {min(x_values)} - {max(x_values)}")
        
        # 各x値に対して期待値を計算
        for x in x_values:
            n, v_rates = param_generator(x)
            # レート配列が降順になっているかチェックしてソート
            sorted_v_rates = sorted(v_rates, reverse=True)
            v1 = sorted_v_rates[0]  # 最大レート
            
            action_specific_expected_values = get_expected_values_per_action(n, sorted_v_rates)
            p_values.append(action_specific_expected_values)
            v1_values.append(v1)
            
            print(f"{x_label}={x}: n={n}, v={sorted_v_rates}, v1={v1} → {[f'{p:.2f}' for p in action_specific_expected_values]}")
            
            # 最初の実行で固定パラメータを記録
            if not fixed_params:
                fixed_params['sample_n'] = n
                fixed_params['sample_v_rates'] = sorted_v_rates
        
        # Pmax値を計算（各行の期待値の最大値）
        pmax_values = [max(p_row) for p_row in p_values]
        
        # データの保存とグラフ描画
        results = {
            'x_values': x_values,
            'p_values': p_values,
            'v1_values': v1_values,
            'pmax_values': pmax_values,
            'x_label': x_label,
            'x_type': x_type,
            'fixed_params': fixed_params
        }
        
        if save_results:
            # 以下、保存処理は他の実験と同様
            csv_path = self.data_manager.save_xp_data(
                x_values, p_values, v1_values, x_label=x_type
            )
            csv_filename = Path(csv_path).name
            
            graph_filename = self.data_manager.generate_filename("xp", "png")
            graph_path = self.data_manager.graph_dir / graph_filename
            
            fig = self.plotter.plot_xp(
                x_values, p_values, v1_values, pmax_values,
                x_label=x_label,
                title=f'{x_label}-P プロット（期待値差分）',
                save_path=str(graph_path),
                show_cutoff_line=show_cutoff_line
            )
            
            config = self.data_manager.create_xp_config(
                csv_filename=csv_filename,
                graph_filename=graph_filename,
                account_count=len(p_values[0]) if p_values else 0,
                x_type=x_type,
                fixed_params=fixed_params
            )
            
            config_name = experiment_name or f"{x_type}_p_experiment_{self.data_manager.generate_filename('', '')[:-1]}"
            config_path = self.data_manager.save_experiment_config(config_name, config)
            
            results['csv_path'] = csv_path
            results['graph_path'] = str(graph_path)
            results['config_path'] = config_path
            
            print(f"\n結果を保存しました:")
            print(f"  CSV: {csv_filename}")
            print(f"  グラフ: {graph_filename}")
            print(f"  設定: {config_name}.json")
        
        return results
    
    def run_n_v_expectation_experiment(self, n_values: List[int], v_rate_lists: List[List[int]],
                                     experiment_name: Optional[str] = None,
                                     save_results: bool = True) -> Dict[str, Any]:
        """
        n-v期待値実験を実行（複数アカウントのレート列について、nを横軸として期待値をプロット）
        
        Args:
            n_values: 残り試合数nの値リスト
            v_rate_lists: 複数アカウントのレート列のリスト（例：[[1500,1400,1300], [1600,1500,1400]]）
            experiment_name: 実験名（Noneの場合は自動生成）
            save_results: 結果を保存するか
            
        Returns:
            実験結果の辞書
        """
        print(f"n-v期待値実験を開始します...")
        print(f"レート列の候補: {v_rate_lists}")
        print(f"n値の範囲: {min(n_values)} - {max(n_values)}")
        
        # 各レート列について、n値ごとの期待値を計算
        expectation_data = {}
        rate_labels = []  # 凡例用のラベル
        
        for i, v_rates in enumerate(v_rate_lists):
            # レート列を降順にソート
            sorted_v_rates = sorted(v_rates, reverse=True)
            rate_label = f"({','.join(map(str, sorted_v_rates))})"
            rate_labels.append(rate_label)
            
            expectations = []
            print(f"\nレート列{rate_label}の計算中...")
            
            for n in n_values:
                # 複数アカウントの期待値を計算し、最適行動の期待値（Pmax）を取得
                action_specific_expected_values = get_expected_values_per_action(n, sorted_v_rates)
                expectation = max(action_specific_expected_values)  # 最適行動の期待値
                expectations.append(expectation)
                
                print(f"  n={n}: P(n,v)={expectation:.2f}")
            
            expectation_data[rate_label] = expectations
        
        # 結果をまとめる
        results = {
            'n_values': n_values,
            'v_rate_lists': v_rate_lists,
            'rate_labels': rate_labels,
            'expectation_data': expectation_data,
            'experiment_type': 'n_v_expectation'
        }
        
        if save_results:
            # CSVファイルの保存
            csv_path = self.data_manager.save_n_v_expectation_data(
                n_values, rate_labels, expectation_data
            )
            csv_filename = Path(csv_path).name
            
            # グラフの生成と保存
            graph_filename = self.data_manager.generate_filename("n_v_expectation", "png")
            graph_path = self.data_manager.graph_dir / graph_filename
            
            fig = self.plotter.plot_n_v_expectation(
                n_values, rate_labels, expectation_data,
                title='n-v 期待値プロット（複数アカウント）',
                save_path=str(graph_path)
            )
            
            # 設定ファイルの作成と保存
            config = {
                'experiment_type': 'n_v_expectation',
                'csv_filename': csv_filename,
                'graph_filename': graph_filename,
                'n_values': n_values,
                'v_rate_lists': v_rate_lists,
                'rate_labels': rate_labels,
                'created_at': self.data_manager.get_timestamp()
            }
            
            config_name = experiment_name or f"n_v_expectation_experiment_{self.data_manager.generate_filename('', '')[:-1]}"
            config_path = self.data_manager.save_experiment_config(config_name, config)
            
            results['csv_path'] = csv_path
            results['graph_path'] = str(graph_path)
            results['config_path'] = config_path
            
            print(f"\n結果を保存しました:")
            print(f"  CSV: {csv_filename}")
            print(f"  グラフ: {graph_filename}")
            print(f"  設定: {config_name}.json")
        
        return results 