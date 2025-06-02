"""
実験サンプルスクリプト

実験モジュールの使用例を示します。
整数レート形式を使用：適正レート(1500)を0とし、16ポイント=1として表現
"""

from src.experiments.experiment_runner import ExperimentRunner
from src.experiments.data_manager import ExperimentDataManager
from src.experiments.plotting import ExperimentPlotter


def run_basic_n_p_experiment():
    """基本的なn-Pプロット実験の例"""
    print("=== 基本的なn-Pプロット実験 ===\n")
    
    runner = ExperimentRunner()
    
    # パラメータ設定（整数レート形式、動作確認用に小さい値）
    n_values = list(range(5, 26, 5))  # n = 5, 10, 15, 20, 25
    v_rates = [0, 1, 2, 3]  # 整数レート：隣り合うレートの差=1
    # 実数換算: [1500, 1516, 1532, 1548]に相当
    
    # 実験実行
    results = runner.run_n_p_experiment(
        n_values=n_values,
        v_rates=v_rates,
        experiment_name="basic_n_p_experiment"
    )
    
    print("\n実験完了！")
    return results


def run_basic_v0_p_experiment():
    """基本的なv0-Pプロット実験の例"""
    print("\n=== 基本的なv0-Pプロット実験 ===\n")
    
    runner = ExperimentRunner()
    
    # パラメータ設定（整数レート形式、動作確認用に小さい値）
    v0_values = list(range(-3, 4, 1))  # v0 = -3, -2, -1, 0, 1, 2, 3
    # 実数換算: 1452, 1468, 1484, 1500, 1516, 1532, 1548に相当
    n = 20  # 残り試合数
    dv = 1  # レート差（整数形式、実数では16に相当）
    r = 3  # アカウント数
    
    # 実験実行
    results = runner.run_v0_p_experiment(
        v0_values=v0_values,
        n=n,
        dv=dv,
        r=r,
        experiment_name="basic_v0_p_experiment"
    )
    
    print("\n実験完了！")
    return results


def run_basic_dv_p_experiment():
    """基本的なdv-Pプロット実験の例"""
    print("\n=== 基本的なdv-Pプロット実験 ===\n")
    
    runner = ExperimentRunner()
    
    # パラメータ設定（整数レート形式、動作確認用に小さい値）
    dv_values = list(range(0, 6, 1))  # dv = 0, 1, 2, 3, 4, 5
    # 実数換算: 0, 16, 32, 48, 64, 80に相当
    n = 20  # 残り試合数
    v0 = 0  # ベースラインレート（適正レート）
    r = 3  # アカウント数
    
    # 実験実行
    results = runner.run_dv_p_experiment(
        dv_values=dv_values,
        n=n,
        v0=v0,
        r=r,
        experiment_name="basic_dv_p_experiment"
    )
    
    print("\n実験完了！")
    return results


def run_comparison_experiment():
    """複数条件の比較実験の例"""
    print("\n=== 複数条件の比較実験 ===\n")
    
    data_manager = ExperimentDataManager()
    plotter = ExperimentPlotter()
    runner = ExperimentRunner(data_manager, plotter)
    
    # 3つの異なるレート分布で比較（整数レート形式、動作確認用に小さい値）
    datasets = []
    
    # 条件1: 等間隔分布（差=1）
    n_values = list(range(5, 26, 5))  # n = 5, 10, 15, 20, 25
    v_rates_equal = [0, 1, 2]  # 実数換算: [1500, 1516, 1532]
    results1 = runner.run_n_p_experiment(n_values, v_rates_equal, save_results=False)
    datasets.append({
        'x_values': results1['x_values'],
        'p_values': results1['p_values'],
        'label': '等間隔分布 (dv=1)',
        'x_label': '残り試合数 n'
    })
    
    # 条件2: 狭い分布
    v_rates_narrow = [1, 2, 3]  # 実数換算: [1516, 1532, 1548]
    results2 = runner.run_n_p_experiment(n_values, v_rates_narrow, save_results=False)
    datasets.append({
        'x_values': results2['x_values'],
        'p_values': results2['p_values'],
        'label': '高レート分布 (1516-1548)',
        'x_label': '残り試合数 n'
    })
    
    # 条件3: 広い分布
    v_rates_wide = [-1, 0, 2]  # 実数換算: [1484, 1500, 1532]
    results3 = runner.run_n_p_experiment(n_values, v_rates_wide, save_results=False)
    datasets.append({
        'x_values': results3['x_values'],
        'p_values': results3['p_values'],
        'label': '広い分布 (1484-1532)',
        'x_label': '残り試合数 n'
    })
    
    # 比較グラフの作成
    graph_filename = data_manager.generate_filename("comparison", "png")
    graph_path = data_manager.graph_dir / graph_filename
    
    fig = plotter.plot_xp_comparison(
        datasets=datasets,
        comparison_label='レート分布',
        save_path=str(graph_path)
    )
    
    print(f"\n比較グラフを保存しました: {graph_filename}")
    print("\n実験完了！")
    
    return datasets


def load_and_plot_experiment():
    """保存された実験データを読み込んで再プロットする例"""
    print("\n=== 保存データの読み込みと再プロット ===\n")
    
    data_manager = ExperimentDataManager()
    plotter = ExperimentPlotter()
    
    # 保存されている実験の一覧を表示
    experiments = data_manager.list_experiments()
    print("保存されている実験ファイル:")
    print(f"  CSV: {experiments['csv_files']}")
    print(f"  設定: {experiments['config_files']}")
    
    # 最新のCSVファイルを読み込む例
    if experiments['csv_files']:
        csv_file = experiments['csv_files'][-1]  # 最新のファイル
        print(f"\n{csv_file} を読み込みます...")
        
        x_values, p_values, x_label = data_manager.load_xp_data(csv_file)
        
        # 新しいグラフを作成
        graph_filename = data_manager.generate_filename("replot", "png")
        graph_path = data_manager.graph_dir / graph_filename
        
        fig = plotter.plot_xp(
            x_values=x_values,
            p_values=p_values,
            x_label=x_label,
            title=f"再プロット: {x_label}-P",
            save_path=str(graph_path)
        )
        
        print(f"再プロットしたグラフを保存しました: {graph_filename}")
    else:
        print("\n保存されたCSVファイルがありません。")


def run_custom_experiment_example():
    """カスタム実験の例"""
    print("\n=== カスタム実験の例 ===\n")
    
    runner = ExperimentRunner()
    
    # アカウント数を変化させる実験
    def account_count_generator(r: float) -> tuple[int, list[int]]:
        """アカウント数rから(n, v_rates)を生成"""
        n = 20  # 固定
        v0 = 0  # 適正レート
        dv = 1  # レート差（整数形式）
        v_rates = [v0 + i * dv for i in range(int(r))]
        return n, v_rates
    
    r_values = list(range(2, 6))  # アカウント数 2～5（動作確認用に小さく）
    
    results = runner.run_custom_experiment(
        x_values=r_values,
        param_generator=account_count_generator,
        x_label='アカウント数 r',
        x_type='account_count',
        experiment_name='account_count_experiment'
    )
    
    print("\n実験完了！")
    return results


if __name__ == "__main__":
    print("実験サンプルスクリプトを実行します（動作確認用の小さい値）\n")
    print("注意: 整数レート形式を使用しています")
    print("  - 適正レート(1500) = 0")
    print("  - 1勝分(+16) = +1")
    print("  - 1敗分(-16) = -1")
    print("  - 動作確認のため、n≈20、レート差=1で実行\n")
    
    # 各実験を順番に実行
    # コメントアウトして必要な実験のみ実行することも可能
    
    # 1. 基本的なn-Pプロット
    run_basic_n_p_experiment()
    
    # 2. 基本的なv0-Pプロット
    run_basic_v0_p_experiment()
    
    # 3. 基本的なdv-Pプロット  
    run_basic_dv_p_experiment()
    
    # 4. 複数条件の比較
    run_comparison_experiment()
    
    # 5. カスタム実験
    run_custom_experiment_example()
    
    # 6. 保存データの読み込み
    load_and_plot_experiment()
    
    print("\n全ての実験が完了しました！") 