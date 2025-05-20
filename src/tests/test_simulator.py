"""シミュレーターのテスト。"""
import pytest
import random

from src.core.state import State
from src.core.parameters import Parameters
from src.simulator.policy import OptimalPolicy, RandomPolicy, FixedPolicy, GreedyPolicy
from src.simulator.simulation import Simulator, compare_policies


def test_policy_selection():
    """各ポリシーが期待通りのアカウント選択を行うことを確認する。"""
    # パラメータオブジェクト作成
    params = Parameters()
    
    # テスト用の状態を作成（実数レート→整数レートに変換）
    state = State.from_iterable([1500, 1400, 1300], is_float=True, mu=params.mu, step=params.rating_step)
    remaining_matches = 10

    # 最適ポリシー（実際の選択はDPに依存するため、Noneでないことだけ確認）
    optimal_policy = OptimalPolicy(params)
    optimal_selection = optimal_policy.select_account(state, remaining_matches)
    # 最適ポリシーは状態によって異なるため、具体的な値ではなく型だけ確認
    assert isinstance(optimal_selection, int) or optimal_selection is None

    # ランダムポリシー（stop_prob=0 の場合は必ずアカウントを選択）
    random_policy = RandomPolicy(params, stop_prob=0.0)
    random_selection = random_policy.select_account(state, remaining_matches)
    assert 0 <= random_selection < state.accounts

    # 固定ポリシー
    fixed_policy = FixedPolicy(params, account_idx=1)
    fixed_selection = fixed_policy.select_account(state, remaining_matches)
    assert fixed_selection == 1

    # 貪欲ポリシー（最も低いレートのアカウントを選択）
    greedy_policy = GreedyPolicy(params)
    greedy_selection = greedy_policy.select_account(state, remaining_matches)
    assert greedy_selection == 2  # 最も低いレートのアカウント（インデックス2）


def test_simulator_single_episode():
    """1エピソードのシミュレーションが正しく動作することを確認する。"""
    # 乱数シードを固定して再現性を確保
    random.seed(42)

    # パラメータ作成
    params = Parameters()

    # テスト用の状態とポリシーを作成（実数レート→整数レートに変換）
    state = State.from_iterable([1500, 1500])
    max_matches = 5
    policy = FixedPolicy(params, account_idx=0)

    # シミュレーターを作成して1エピソード実行
    simulator = Simulator(policy, params)
    final_rating = simulator.run_episode(state, max_matches)

    # 最終レートが数値であることを確認
    assert isinstance(final_rating, (int, float))
    # レートが変動していることを確認（初期値と異なる）
    assert final_rating != 1500


def test_simulator_multiple_episodes():
    """複数エピソードのシミュレーションが正しく動作することを確認する。"""
    # 乱数シードを固定して再現性を確保
    random.seed(42)
    params = Parameters()

    # テスト用の状態とポリシーを作成
    state = State.from_iterable([1500, 1500])
    max_matches = 5
    episodes = 10
    policy = FixedPolicy(params, account_idx=0)

    # シミュレーターを作成して複数エピソード実行
    simulator = Simulator(policy, params)
    result = simulator.run_simulation(state, max_matches, episodes)

    # 結果の検証
    assert len(result.ratings) == episodes
    assert result.policy_name == "FixedPolicy"
    assert result.initial_ratings == [1500, 1500]
    assert result.max_matches == max_matches


def test_compare_policies():
    """複数のポリシーを比較する機能が正しく動作することを確認する。"""
    # 乱数シードを固定して再現性を確保
    random.seed(42)

    params = Parameters()
    # テスト用の状態とポリシーを作成
    state = State.from_iterable([1500, 1500])
    max_matches = 5
    episodes = 5
    policies = [
        OptimalPolicy(params),
        RandomPolicy(params),
        FixedPolicy(params),
        GreedyPolicy(params),
    ]

    # ポリシー比較を実行
    results = compare_policies(policies, state, max_matches, episodes, params)

    # 結果の検証
    assert len(results) == len(policies)
    for i, result in enumerate(results):
        assert result.policy_name == policies[i].name
        assert len(result.ratings) == episodes