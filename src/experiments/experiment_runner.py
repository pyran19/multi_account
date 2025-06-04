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
        等間隔のレート配列を生成
        
        Args:
            v0: ベースラインレート
            dv: レート差
            r: アカウント数
            
        Returns:
            レート配列
        """
        return [v0 + i * dv for i in range(r)]
    
    def run_n_p_experiment(self, n_values: List[int], v_rates: List[int],
                          experiment_name: Optional[str] = None,
                          save_results: bool = True) -> Dict[str, Any]:
        """
        n-Pプロット実験を実行
        
        Args:
            n_values: 残り試合数nの値リスト
            v_rates: 各アカウントのレート配列
            experiment_name: 実験名（Noneの場合は自動生成）
            save_results: 結果を保存するか
            
        Returns:
            実験結果の辞書
        """
        p_values = []
        
        print(f"n-Pプロット実験を開始します...")
        print(f"アカウント数: {len(v_rates)}")
        print(f"レート分布: {v_rates}")
        print(f"n値の範囲: {min(n_values)} - {max(n_values)}")
        
        # 各n値に対して期待値を計算
        for n in n_values:
            action_specific_expected_values = get_expected_values_per_action(n, v_rates) # MODIFIED: function call and variable name
            p_values.append(action_specific_expected_values) # MODIFIED: variable name
            print(f"n={n}: Action EVs {[f'{p:.2f}' for p in action_specific_expected_values]}") # MODIFIED: print statement
        
        # データの保存とグラフ描画
        results = {
            'x_values': n_values,
            'p_values': p_values,
            'x_label': '残り試合数 n',
            'x_type': 'n',
            'fixed_params': {'v_rates': v_rates}
        }
        
        if save_results:
            # CSVファイルの保存
            csv_path = self.data_manager.save_xp_data(
                n_values, p_values, x_label='n'
            )
            csv_filename = Path(csv_path).name
            
            # グラフの生成と保存
            graph_filename = self.data_manager.generate_filename("xp", "png")
            graph_path = self.data_manager.graph_dir / graph_filename
            
            fig = self.plotter.plot_xp(
                n_values, p_values,
                x_label='残り試合数 n',
                title='n-P プロット',
                save_path=str(graph_path)
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
                           save_results: bool = True) -> Dict[str, Any]:
        """
        v0-Pプロット実験を実行
        
        Args:
            v0_values: ベースラインレートv0の値リスト
            n: 残り試合数
            dv: レート差
            r: アカウント数
            experiment_name: 実験名
            save_results: 結果を保存するか
            
        Returns:
            実験結果の辞書
        """
        p_values = []
        
        print(f"v0-Pプロット実験を開始します...")
        print(f"アカウント数: {r}")
        print(f"残り試合数: {n}")
        print(f"レート差: {dv}")
        print(f"v0値の範囲: {min(v0_values)} - {max(v0_values)}")
        
        # 各v0値に対して期待値を計算
        for v0 in v0_values:
            v_rates = self.generate_equal_interval_rates(v0, dv, r)
            action_specific_expected_values = get_expected_values_per_action(n, v_rates) # MODIFIED: function call and variable name
            p_values.append(action_specific_expected_values) # MODIFIED: variable name
            print(f"v0={v0}: レート{v_rates} → 期待値{[f'{p:.2f}' for p in action_specific_expected_values]}") # MODIFIED: print statement (var name)
        
        # データの保存とグラフ描画
        results = {
            'x_values': v0_values,
            'p_values': p_values,
            'x_label': 'ベースラインレート v0',
            'x_type': 'v0',
            'fixed_params': {'n': n, 'dv': dv, 'r': r}
        }
        
        if save_results:
            # CSVファイルの保存
            csv_path = self.data_manager.save_xp_data(
                v0_values, p_values, x_label='v0'
            )
            csv_filename = Path(csv_path).name
            
            # グラフの生成と保存
            graph_filename = self.data_manager.generate_filename("xp", "png")
            graph_path = self.data_manager.graph_dir / graph_filename
            
            fig = self.plotter.plot_xp(
                v0_values, p_values,
                x_label='ベースラインレート v0',
                title='v0-P プロット',
                save_path=str(graph_path)
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
                           save_results: bool = True) -> Dict[str, Any]:
        """
        dv-Pプロット実験を実行
        
        Args:
            dv_values: レート差dvの値リスト
            n: 残り試合数
            v0: ベースラインレート
            r: アカウント数
            experiment_name: 実験名
            save_results: 結果を保存するか
            
        Returns:
            実験結果の辞書
        """
        p_values = []
        
        print(f"dv-Pプロット実験を開始します...")
        print(f"アカウント数: {r}")
        print(f"残り試合数: {n}")
        print(f"ベースラインレート: {v0}")
        print(f"dv値の範囲: {min(dv_values)} - {max(dv_values)}")
        
        # 各dv値に対して期待値を計算
        for dv in dv_values:
            v_rates = self.generate_equal_interval_rates(v0, dv, r)
            action_specific_expected_values = get_expected_values_per_action(n, v_rates) # MODIFIED: function call and variable name
            p_values.append(action_specific_expected_values) # MODIFIED: variable name
            print(f"dv={dv}: レート{v_rates} → 期待値{[f'{p:.2f}' for p in action_specific_expected_values]}") # MODIFIED: print statement (var name)
        
        # データの保存とグラフ描画
        results = {
            'x_values': dv_values,
            'p_values': p_values,
            'x_label': 'レート差 dv',
            'x_type': 'dv',
            'fixed_params': {'n': n, 'v0': v0, 'r': r}
        }
        
        if save_results:
            # CSVファイルの保存
            csv_path = self.data_manager.save_xp_data(
                dv_values, p_values, x_label='dv'
            )
            csv_filename = Path(csv_path).name
            
            # グラフの生成と保存
            graph_filename = self.data_manager.generate_filename("xp", "png")
            graph_path = self.data_manager.graph_dir / graph_filename
            
            fig = self.plotter.plot_xp(
                dv_values, p_values,
                x_label='レート差 dv',
                title='dv-P プロット',
                save_path=str(graph_path)
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
                            save_results: bool = True) -> Dict[str, Any]:
        """
        カスタム実験を実行
        
        Args:
            x_values: xの値リスト
            param_generator: xの値から(n, v_rates)を生成する関数
            x_label: x軸のラベル
            x_type: xの種類
            experiment_name: 実験名
            save_results: 結果を保存するか
            
        Returns:
            実験結果の辞書
        """
        p_values = []
        fixed_params = {}
        
        print(f"カスタム実験 ({x_type}) を開始します...")
        print(f"x値の範囲: {min(x_values)} - {max(x_values)}")
        
        # 各x値に対して期待値を計算
        for x in x_values:
            n, v_rates = param_generator(x)
            action_specific_expected_values = get_expected_values_per_action(n, v_rates) # MODIFIED: function call and variable name
            p_values.append(action_specific_expected_values) # MODIFIED: variable name
            print(f"{x_label}={x}: n={n}, v={v_rates} → {[f'{p:.2f}' for p in action_specific_expected_values]}") # MODIFIED: print statement (var name)
            
            # 最初の実行で固定パラメータを記録
            if not fixed_params:
                fixed_params['sample_n'] = n
                fixed_params['sample_v_rates'] = v_rates
        
        # データの保存とグラフ描画
        results = {
            'x_values': x_values,
            'p_values': p_values,
            'x_label': x_label,
            'x_type': x_type,
            'fixed_params': fixed_params
        }
        
        if save_results:
            # 以下、保存処理は他の実験と同様
            csv_path = self.data_manager.save_xp_data(
                x_values, p_values, x_label=x_type
            )
            csv_filename = Path(csv_path).name
            
            graph_filename = self.data_manager.generate_filename("xp", "png")
            graph_path = self.data_manager.graph_dir / graph_filename
            
            fig = self.plotter.plot_xp(
                x_values, p_values,
                x_label=x_label,
                title=f'{x_label}-P プロット',
                save_path=str(graph_path)
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