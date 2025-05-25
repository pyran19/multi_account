"""コマンドラインインターフェース。"""
import argparse
import os
import sys
from typing import List
import math

import numpy as np

from src.core.dp import expectation, best_action
from src.core.parameters import Parameters
from src.core.state import State
from src.simulator.policy import OptimalPolicy, RandomPolicy, FixedPolicy, GreedyPolicy
from src.simulator.simulation import Simulator, compare_policies
from src.simulator.visualization import save_plots
from src.core.result_cache import load_cache, save_result


def parse_args():
    """コマンドライン引数をパースする。"""
    parser = argparse.ArgumentParser(
        description="複数アカウントにおけるレートマッチング最適戦略の計算とシミュレーション"
    )
    subparsers = parser.add_subparsers(dest="command", help="サブコマンド")

    # DPコマンド
    dp_parser = subparsers.add_parser("dp", help="動的計画法による期待値計算")
    dp_parser.add_argument("--n", type=int, required=True, help="残り試合数")
    dp_parser.add_argument("--accounts", type=int, default=2, help="アカウント数")
    dp_parser.add_argument(
        "--initial", type=float, nargs="+", help="各アカウントの初期レート（スペース区切り）"
    )

    # シミュレーションコマンド
    sim_parser = subparsers.add_parser("sim", help="モンテカルロシミュレーション")
    sim_parser.add_argument("--n", type=int, required=True, help="最大試合数")
    sim_parser.add_argument("--accounts", type=int, default=2, help="アカウント数")
    sim_parser.add_argument(
        "--initial", type=float, nargs="+", help="各アカウントの初期レート（スペース区切り）"
    )
    sim_parser.add_argument(
        "--episodes", type=int, default=1000, help="シミュレーションするエピソード数"
    )
    sim_parser.add_argument(
        "--policy",
        choices=["optimal", "random", "fixed", "greedy", "all"],
        default="all",
        help="使用するポリシー",
    )
    sim_parser.add_argument(
        "--fixed-idx", type=int, default=0, help="固定ポリシーで使用するアカウントのインデックス"
    )
    sim_parser.add_argument(
        "--visualize", action="store_true", help="結果をグラフで可視化する"
    )
    sim_parser.add_argument(
        "--output-dir", type=str, default=".", help="グラフの保存先ディレクトリ"
    )

    # パラメータオプション（共通）
    for p in [dp_parser, sim_parser]:
        p.add_argument("--rating-step", type=int, default=16, help="1試合あたりのレート変動幅")
        p.add_argument("--k-coeff", type=float, default=math.log(10) / 1600, help="勝率の線形近似で使う傾き")
        p.add_argument("--mu", type=float, default=1500, help="プレイヤーの適正レート")

    return parser.parse_args()


def get_initial_state(args, params: Parameters) -> State:
    """コマンドライン引数から初期状態を作成する。"""
    if args.initial:
        if len(args.initial) != args.accounts:
            print(
                f"Error: 指定されたアカウント数 ({args.accounts}) と初期レートの数 ({len(args.initial)}) が一致しません。",
                file=sys.stderr,
            )
            sys.exit(1)
        initial_ratings = args.initial
    else:
        # デフォルトは全て同じレート
        initial_ratings = [args.mu] * args.accounts

    int_initial_ratings = [params.float_to_int_rating(r) for r in initial_ratings]

    return State.from_iterable(int_initial_ratings)


def get_parameters(param_data: dict) -> Parameters:
    """パラメータ辞書からパラメータを作成する。"""
    return Parameters(
        rating_step=param_data['rating_step'],
        k_coeff=param_data['k_coeff'],
        mu=param_data['mu'],
    )

def get_initial_state_from_args(args, params: Parameters) -> State:
    """コマンドライン引数から初期状態を作成する。"""
    if args.initial:
        if len(args.initial) != args.accounts:
            # エラーメッセージは呼び出し元で処理する想定
            raise ValueError(
                f"指定されたアカウント数 ({args.accounts}) と初期レートの数 ({len(args.initial)}) が一致しません。"
            )
        initial_ratings_float = args.initial
    else:
        initial_ratings_float = None # get_initial_stateでデフォルト処理

    return get_initial_state(args.accounts, initial_ratings_float, params)


def get_initial_state(num_accounts: int, initial_ratings_float: List[float] | None, params: Parameters) -> State:
    """パラメータから初期状態を作成する。"""
    if initial_ratings_float:
        if len(initial_ratings_float) != num_accounts:
            raise ValueError(
                f"指定されたアカウント数 ({num_accounts}) と初期レートの数 ({len(initial_ratings_float)}) が一致しません。"
            )
    else:
        # デフォルトは全て同じレート
        initial_ratings_float = [params.mu] * num_accounts

    int_initial_ratings = [params.float_to_int_rating(r) for r in initial_ratings_float]
    return State.from_iterable(int_initial_ratings)


def cmd_dp(args):
    """DPコマンドを実行する。"""
    params_dict = {
        "rating_step": args.rating_step,
        "k_coeff": args.k_coeff,
        "mu": args.mu,
    }
    params = get_parameters(params_dict)
    
    try:
        state = get_initial_state_from_args(args, params)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    # パラメータ表示
    print(f"残り試合数: {args.n}")
    print(f"アカウント数: {args.accounts}")
    print(f"初期レート（整数）: {list(state.ratings)}")
    print(f"初期レート: {list([params.int_to_float_rating(r) for r in state.ratings])}") # cmd_dpでは表示する
    print(f"レート変動幅: {params.rating_step}")
    print(f"勝率係数 k: {params.k_coeff}")
    print(f"適正レート μ: {params.mu}")
    print()

    # 期待値計算
    dp_results = perform_dp_calculation(args.n, state, params, args.accounts)

    if dp_results['using_cache']:
        print("[cache] 既存の計算結果を使用します。")
    
    print(f"最終レート期待値: {params.int_to_float_rating(dp_results['expected_value_int']):.2f} (整数レート: {dp_results['expected_value_int']})")
    if dp_results['best_action_account_index'] is None:
        print("最適アクション: 今すぐ終了")
    else:
        print(f"最適アクション: アカウント {dp_results['best_action_account_index']} で潜る")


def perform_dp_calculation(n_matches: int, initial_state: State, params: Parameters, num_accounts: int):
    """動的計画法による期待値計算を実行する。"""
    cache = load_cache(n_matches, num_accounts)
    using_cache = False
    if initial_state.ratings in cache:
        exp, best_idx = cache[initial_state.ratings]
        using_cache = True
    else:
        exp = expectation(n_matches, initial_state, params)
        best_idx = best_action(n_matches, initial_state, params)
        # Note: save_result is not called here as per original logic in cmd_dp for the refactored part
        # save_result(n_matches, num_accounts, initial_state.ratings, exp, best_idx)

    return {
        'expected_value_int': exp,
        'best_action_account_index': best_idx,
        'using_cache': using_cache,
        'initial_ratings_int': list(initial_state.ratings),
        'initial_ratings_float': [params.int_to_float_rating(r) for r in initial_state.ratings],
    }


def cmd_sim(args):
    """シミュレーションコマンドを実行する。"""
    params_dict = {
        "rating_step": args.rating_step,
        "k_coeff": args.k_coeff,
        "mu": args.mu,
    }
    params = get_parameters(params_dict)
    try:
        state = get_initial_state_from_args(args, params)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


    # パラメータ表示
    print(f"最大試合数: {args.n}")
    print(f"アカウント数: {args.accounts}")
    print(f"初期レート: {list(state.ratings)}") # cmd_simでは表示する
    print(f"エピソード数: {args.episodes}")
    print(f"レート変動幅: {params.rating_step}")
    print(f"勝率係数 k: {params.k_coeff}")
    print(f"適正レート μ: {params.mu}")
    print()

    # ポリシー選択
    if args.policy == "all":
        policies = [
            #OptimalPolicy(params),
            RandomPolicy(params),
            FixedPolicy(params, account_idx=0),
            FixedPolicy(params, account_idx=1),
            GreedyPolicy(params),
        ]
    elif args.policy == "optimal":
        policies = [OptimalPolicy(params)]
    elif args.policy == "random":
        policies = [RandomPolicy(params)]
    elif args.policy == "fixed":
        policies = [FixedPolicy(params, account_idx=args.fixed_idx)]
    elif args.policy == "greedy":
        policies = [GreedyPolicy(params)]
    else:
        print(f"Error: 不明なポリシー '{args.policy}'", file=sys.stderr)
        sys.exit(1)

    # シミュレーション実行
    sim_results_data = perform_simulation(
        n_matches=args.n,
        initial_state=state,
        params=params,
        num_accounts=args.accounts,
        episodes=args.episodes,
        policy_name=args.policy,
        fixed_idx=args.fixed_idx,
        visualize=args.visualize,
        output_dir=args.output_dir
    )

    # 結果表示 (cmd_simでは表示する)
    for result in sim_results_data['simulation_results']:
        # Assuming result objects have a __str__ method or are dicts
        print(result) 
        print()
    
    # 可視化結果表示 (cmd_simでは表示する)
    if sim_results_data['visualization_files']:
        print(f"グラフを保存しました:")
        for f in sim_results_data['visualization_files']:
            print(f"  - {f}")
    
    # Handle visualization errors if perform_simulation is designed to return them
    if 'error' in sim_results_data:
        print(f"警告: {sim_results_data['error']}")
        if "matplotlib" in sim_results_data['error']:
             print("可視化するには: pip install matplotlib")


def perform_simulation(
    n_matches: int, 
    initial_state: State, 
    params: Parameters, 
    num_accounts: int, 
    episodes: int, 
    policy_name: str, 
    fixed_idx: int, 
    visualize: bool, 
    output_dir: str
):
    """モンテカルロシミュレーションを実行する。"""
    # ポリシー選択
    # Note: num_accounts is available, can be used if policies need it (e.g. FixedPolicy validation)
    if policy_name == "all":
        policies_to_run = [
            #OptimalPolicy(params), # OptimalPolicy might need n_matches, state, params for each step
            RandomPolicy(params),
            FixedPolicy(params, account_idx=0), # Ensure fixed_idx is valid for num_accounts
            FixedPolicy(params, account_idx=1 if num_accounts > 1 else 0), # Ensure valid second policy
            GreedyPolicy(params),
        ]
    elif policy_name == "optimal":
        # OptimalPolicy may require more arguments or a different setup for simulation
        # For now, assuming it can be instantiated simply; adjust if needed.
        policies_to_run = [OptimalPolicy(params)]
    elif policy_name == "random":
        policies_to_run = [RandomPolicy(params)]
    elif policy_name == "fixed":
        if fixed_idx >= num_accounts:
            # This error should ideally be caught earlier (e.g. in MCP server validation)
            # Or return an error status in the dictionary
            raise ValueError(f"fixed_idx {fixed_idx} is out of bounds for {num_accounts} accounts.")
        policies_to_run = [FixedPolicy(params, account_idx=fixed_idx)]
    elif policy_name == "greedy":
        policies_to_run = [GreedyPolicy(params)]
    else:
        # This error should ideally be caught earlier
        raise ValueError(f"不明なポリシー '{policy_name}'")

    # シミュレーション実行
    simulation_results = compare_policies(policies_to_run, initial_state, n_matches, episodes, params)

    image_files = []
    error_message = None
    if visualize:
        try:
            import matplotlib
            matplotlib.use('Agg')  # ヘッドレス環境用
            
            os.makedirs(output_dir, exist_ok=True)
            prefix = os.path.join(
                output_dir,
                f"sim_n{n_matches}_acc{num_accounts}_ep{episodes}"
            )
            image_files = save_plots(simulation_results, params, prefix=prefix)
        except ImportError:
            error_message = "matplotlib がインストールされていません。"
        except Exception as e:
            error_message = f"可視化中にエラーが発生しました: {e}"
            
    results_dict = {
        'simulation_results': simulation_results, # These might be objects, ensure they are serializable if needed for MCP
        'visualization_files': image_files,
        'initial_ratings_int': list(initial_state.ratings),
        'initial_ratings_float': [params.int_to_float_rating(r) for r in initial_state.ratings],
    }
    if error_message:
        results_dict['error'] = error_message
        
    return results_dict


def main():
    """メイン関数。"""
    args = parse_args()

    if args.command == "dp":
        cmd_dp(args)
    elif args.command == "sim":
        # In cmd_sim, we now call perform_simulation and print its output.
        # Error handling for visualization is done based on the returned dict.
        # params and state are already prepared inside cmd_sim before calling perform_simulation.
        cmd_sim(args)
    else:
        print("Error: コマンドを指定してください。 'dp' または 'sim'", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()