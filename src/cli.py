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


def get_parameters(args) -> Parameters:
    """コマンドライン引数からパラメータを作成する。"""
    return Parameters(
        rating_step=args.rating_step,
        k_coeff=args.k_coeff,
        mu=args.mu,
    )


def cmd_dp(args):
    """DPコマンドを実行する。"""
    params = get_parameters(args)
    state = get_initial_state(args, params)

    # パラメータ表示
    print(f"残り試合数: {args.n}")
    print(f"アカウント数: {args.accounts}")
    print(f"初期レート（整数）: {list(state.ratings)}")
    print(f"初期レート: {list([params.int_to_float_rating(r) for r in state.ratings])}")
    print(f"レート変動幅: {params.rating_step}")
    print(f"勝率係数 k: {params.k_coeff}")
    print(f"適正レート μ: {params.mu}")
    print()

    # 期待値計算
    cache = load_cache(args.n, args.accounts)

    if state.ratings in cache:
        exp, best_idx = cache[state.ratings]
        print("[cache] 既存の計算結果を使用します。")
    else:
        exp = expectation(args.n, state, params)
        best_idx = best_action(args.n, state, params)
        # 保存
        #save_result(args.n, args.accounts, state.ratings, exp, best_idx)

    
    print(f"最終レート期待値: {params.int_to_float_rating(exp):.2f} (整数レート: {exp})")
    if best_idx is None:
        print("最適アクション: 今すぐ終了")
    else:
        print(f"最適アクション: アカウント {best_idx} で潜る")


def cmd_sim(args):
    """シミュレーションコマンドを実行する。"""
    params = get_parameters(args)
    state = get_initial_state(args, params)

    # パラメータ表示
    print(f"最大試合数: {args.n}")
    print(f"アカウント数: {args.accounts}")
    print(f"初期レート: {list(state.ratings)}")
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
    results = compare_policies(policies, state, args.n, args.episodes, params)

    # 結果表示
    for result in results:
        print(result)
        print()
    
    # 可視化
    if args.visualize:
        try:
            import matplotlib
            matplotlib.use('Agg')  # ヘッドレス環境用
            
            # 出力ディレクトリの作成
            os.makedirs(args.output_dir, exist_ok=True)
            
            # プレフィックス生成
            prefix = os.path.join(
                args.output_dir,
                f"sim_n{args.n}_acc{args.accounts}_ep{args.episodes}"
            )
            
            # グラフ保存
            image_files = save_plots(results, params, prefix=prefix)
            print(f"グラフを保存しました:")
            for f in image_files:
                print(f"  - {f}")
        except ImportError:
            print("警告: matplotlib がインストールされていないため、可視化をスキップします。")
            print("可視化するには: pip install matplotlib")
        except Exception as e:
            print(f"可視化中にエラーが発生しました: {e}")


def main():
    """メイン関数。"""
    args = parse_args()

    if args.command == "dp":
        cmd_dp(args)
    elif args.command == "sim":
        cmd_sim(args)
    else:
        print("Error: コマンドを指定してください。 'dp' または 'sim'", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()