"""逐次動的計画法 (DP) による期待値計算。"""
from __future__ import annotations

from functools import lru_cache
from typing import Tuple, Optional, Dict, List

from .state import State
from .parameters import Parameters
from .result_cache import save_result, load_available_caches

__all__ = [
    "expectation",
    "best_action",
    "get_expected_values_for_each_action",
]

# キャッシュ計算データを保持するためのグローバル変数
_calc_cache: Dict[Tuple[int, Tuple[int, ...]], Tuple[int, Optional[int]]] = {}

# 外部ファイルからロードした可能なキャッシュ
_loaded_caches: Dict[int, Dict[Tuple[int, ...], Tuple[float, Optional[int]]]] = {}

CACHE_INTERVAL = 50

# ---------------------------
# 内部ヘルパー関数
# ---------------------------

def _calculate_expected_values_for_all_options(
    n: int, state: State, params: Parameters
) -> Dict[Optional[int], float]:
    """
    現在の状態から取りうる全選択肢（停止または各アカウントでのプレイ）の期待値を計算する。

    Args:
        n: 残り試合数
        state: 現在の状態 (Stateオブジェクト)
        params: パラメータ設定

    Returns:
        選択肢をキー（Noneが停止、intがアカウントインデックス）、期待値を値とする辞書。
    """
    options_with_values: Dict[Optional[int], float] = {}

    # 選択肢1: ここで終了する (stop)
    options_with_values[None] = float(state.best)

    # 選択肢2: いずれかのアカウントで試合を行う
    for idx, int_rating in enumerate(state.ratings):
        # 整数レートから勝率計算
        float_rating = params.int_to_float_rating(int_rating)
        p = params.win_prob(float_rating)

        # 勝利時・敗北時の次状態（整数レートのタプル）
        # state.after_match は State オブジェクトを返すので .ratings でタプルを取得
        next_win_state_ratings = state.after_match(idx, won=True, step=1).ratings
        next_lose_state_ratings = state.after_match(idx, won=False, step=1).ratings

        # 再帰的に期待値を計算 (内部関数 _expectation_cached を使用)
        # _expectation_cached は (n, ratings_tuple, params) を引数に取る
        e_win = _expectation_cached(n - 1, next_win_state_ratings, params)
        e_lose = _expectation_cached(n - 1, next_lose_state_ratings, params)

        # このアクション（アカウントidxでプレイ）の期待値
        exp_action_idx = p * e_win + (1.0 - p) * e_lose
        options_with_values[idx] = exp_action_idx

    return options_with_values

# ---------------------------
# メイン関数: 期待値
# ---------------------------

@lru_cache(maxsize=None)
def _expectation_cached(n: int, ratings: Tuple[int, ...], params: Parameters) -> float:
    """内部用キャッシュ付き期待値計算関数。
    
    注意: 整数レートベースで計算し、整数レートの期待値を返す
    """
    # 事前にロードしたキャッシュに存在するか確認
    if n in _loaded_caches and ratings in _loaded_caches[n]:
        # キャッシュから値を取得
        exp_value, best_act = _loaded_caches[n][ratings]
        # メモリ内キャッシュにも保存
        _calc_cache[(n, ratings)] = (exp_value, best_act)
        return exp_value  # 整数レートの期待値を返す

    state = State(ratings)  # 整数レート形式のState

    # 基底ケース: これ以上試合が無い (終了)
    if n == 0:
        return state.best

    # 全ての選択肢（停止含む）の期待値を計算
    options_with_values = _calculate_expected_values_for_all_options(n, state, params)

    # 全体での最大期待値
    overall_max_value = -float('inf') # 初期値をマイナス無限大に
    for value in options_with_values.values():
        if value > overall_max_value:
            overall_max_value = value

    # overall_max_value = max(options_with_values.values()) # もしoptions_with_valuesが空ならエラーになるので上記ループで対応

    # キャッシュ用の最適アクションインデックスを決定
    # options_with_values のキーのイテレーション順 (None, 0, 1, ...) で最初に見つかった最大値を持つキー
    best_idx_for_cache: Optional[int] = None
    # まずNoneキー（停止）を確認
    if options_with_values.get(None) == overall_max_value:
        best_idx_for_cache = None
    else:
        for idx in range(len(state.ratings)):
            if options_with_values.get(idx) == overall_max_value:
                best_idx_for_cache = idx
                break # 最初に見つかったものを採用

    # nがCACHE_INTERVALの倍数の場合、中間結果を保存
    if n % CACHE_INTERVAL == 0:
        # 最適アクションとともに結果を保存
        save_result(n, len(ratings), ratings, overall_max_value, best_idx_for_cache)
        # 計算キャッシュに保存
        _calc_cache[(n, ratings)] = (overall_max_value, best_idx_for_cache)

    return overall_max_value


def expectation(n: int, state: State | Tuple[int, ...], params: Parameters) -> float:  # noqa: D401
    """公開 API: 指定状態・残り試合数での最終レート期待値を返す。
    """
    global _loaded_caches
    
    # キャッシュが空の場合は、初期化
    if not _loaded_caches:
        # 入力がStateの場合はアカウント数を取得
        if isinstance(state, State):
            accounts = len(state.ratings)
        else:
            accounts = len(state)
        
        # 利用可能なキャッシュを全てロード
        _loaded_caches = load_available_caches(accounts)
        
    # 入力が整数レートタプルの場合はStateに変換
    if not isinstance(state, State):
        state = State.from_iterable(state)
    
    # 内部の_expectation_cachedは整数レートベースで計算
    int_exp = _expectation_cached(n, state.ratings, params)
    
    return int_exp


# ---------------------------
# 最適アクション
# ---------------------------

def best_action(n: int, state: State, params: Parameters) -> Optional[int]:
    """最適アクションを返す。

    戻り値:
        * `None` — 今すぐ終了するのが最適
        * `int`  — そのインデックスのアカウントで潜るのが最適
    """
    # キャッシュにあれば、そこから取得
    cache_key = (n, state.ratings)
    if cache_key in _calc_cache:
        _, best_idx = _calc_cache[cache_key]
        return best_idx
    
    # 事前にロードしたキャッシュに存在するか確認
    if n in _loaded_caches and state.ratings in _loaded_caches[n]:
        # キャッシュから値を取得
        _, best_idx = _loaded_caches[n][state.ratings]
        # メモリ内キャッシュにも保存
        _calc_cache[cache_key] = _loaded_caches[n][state.ratings]
        return best_idx

    # n=0の場合は何もできない
    if n == 0:
        return None  # もう打つ手なし

    # 全ての選択肢（停止含む）の期待値を計算
    # best_action は State オブジェクトを直接受け取るのでそのまま渡す
    options_with_values = _calculate_expected_values_for_all_options(n, state, params)

    # 最適アクションを決定 (値が最大のキーを取得)
    # max関数のキーは辞書のgetメソッドを指定し、値に基づいて最大値を持つキー(アクション)を返す
    # 同値の場合は、辞書のイテレーション順で最初に出現するキー (None, 0, 1, ...)
    best_action_idx: Optional[int] = None
    current_max_val = -float('inf')

    # None (停止) が最適かチェック
    if options_with_values[None] >= current_max_val:
        current_max_val = options_with_values[None]
        best_action_idx = None

    # 各アカウントでのプレイが最適かチェック
    for i in range(len(state.ratings)):
        if options_with_values[i] > current_max_val: # Stopより明確に良い場合のみ更新
            current_max_val = options_with_values[i]
            best_action_idx = i
        elif options_with_values[i] == current_max_val and best_action_idx is not None and i < best_action_idx :
            # 同じ期待値ならインデックスが小さい方を優先（ただしNoneよりは優先しない）
             best_action_idx = i


    # キャッシュに保存 (値は best_action_idx に対応する期待値)
    # options_with_valuesが空でないことはn>0であることから保証される
    _calc_cache[cache_key] = (options_with_values[best_action_idx], best_action_idx) # type: ignore
    return best_action_idx


# ---------------------------
# 各アクションの期待値
# ---------------------------

def get_expected_values_for_each_action(
    n: int, state_input: State | Tuple[int, ...], params: Parameters
) -> List[float]:
    """指定された状態から各アカウントでプレイした場合の期待値を計算してリストで返す。"""
    global _loaded_caches

    # 入力がタプルの場合はStateオブジェクトに変換
    if isinstance(state_input, tuple):
        state = State.from_iterable(state_input)
    else:
        state = state_input

    # キャッシュが空の場合は、初期化 (expectation関数と同様のロジック)
    if not _loaded_caches:
        accounts = len(state.ratings)
        _loaded_caches = load_available_caches(accounts)

    # n=0 の場合: これ以上試合はできないので、各アクションの期待値は現在の最大レートとする
    # (実際にはアクションは不可能だが、呼び出し元が一貫した処理をできるようにするため)
    if n == 0:
        return [float(state.best)] * len(state.ratings)

    # 全ての選択肢（停止含む）の期待値を計算
    # get_expected_values_for_each_action は State オブジェクトを直接受け取るのでそのまま渡す
    options_with_values = _calculate_expected_values_for_all_options(n, state, params)

    # アカウントプレイアクションの期待値リストを構築
    # options_with_values には None キーも含まれるため、アカウント数分だけ取得
    action_expectations = [
        options_with_values[i] for i in range(len(state.ratings))
    ]

    return action_expectations