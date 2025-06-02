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

    # アクション1: ここで終了する (stop) — 期待値は現在の最大レート
    best_value: int = state.best
    best_idx: Optional[int] = None

    # アクション2: いずれかのアカウントで試合を行う
    for idx, int_rating in enumerate(state):
        # 整数レートから勝率計算
        p = params.win_prob(params.int_to_float_rating(int_rating))
        
        # 勝利時・敗北時の次状態（整数レートのまま）
        next_win = state.after_match(idx, won=True, step=1)  # 整数の場合step=1固定
        next_lose = state.after_match(idx, won=False, step=1)

        exp = p * _expectation_cached(n - 1, next_win.ratings, params) + (
            1.0 - p
        ) * _expectation_cached(n - 1, next_lose.ratings, params)

        if exp > best_value:
            best_value = exp
            best_idx = idx

    # nがCACHE_INTERVALの倍数の場合、中間結果を保存
    if n % CACHE_INTERVAL == 0:
        # 最適アクションとともに結果を保存
        save_result(n, len(ratings), ratings, best_value, best_idx)
        # 計算キャッシュに保存
        _calc_cache[(n, ratings)] = (best_value, best_idx)

    return best_value


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

    best_value: int = state.best
    best_idx: Optional[int] = None

    for idx, int_rating in enumerate(state):
        # 整数レートから実数レートに変換して勝率計算
        float_rating = params.int_to_float_rating(int_rating)
        p = params.win_prob(float_rating)
        
        # 次状態は整数レートで計算
        next_win = state.after_match(idx, won=True, step=1)
        next_lose = state.after_match(idx, won=False, step=1)
        
        # 期待値計算 - 内部は整数レートで返ってくる
        next_win_exp = expectation(n - 1, next_win, params)
        next_lose_exp = expectation(n - 1, next_lose, params)
        
        expected_value = p * next_win_exp + (1 - p) * next_lose_exp
        
        if expected_value > best_value:
            best_value = expected_value
            best_idx = idx

    # キャッシュに保存
    _calc_cache[cache_key] = (best_value, best_idx)
    return best_idx 


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

    action_expectations: List[float] = []

    for idx, int_rating in enumerate(state.ratings):
        # 整数レートから勝率計算
        # Note: _expectation_cached は内部で整数レートを扱うが、
        # params.win_prob は実数レートを期待する可能性がある。
        # ここでは既存の best_action のロジックに合わせて実数レートを使用する。
        float_rating = params.int_to_float_rating(int_rating)
        p = params.win_prob(float_rating)

        # 勝利時・敗北時の次状態（整数レートのまま）
        # State.after_match は内部でよしなに処理してくれる
        next_win_state = state.after_match(idx, won=True) # stepはState内部で処理
        next_lose_state = state.after_match(idx, won=False) # stepはState内部で処理

        # 再帰的に期待値を計算
        # _expectation_cached は (n, ratings_tuple, params) を引数に取る
        exp_win = _expectation_cached(n - 1, next_win_state.ratings, params)
        exp_lose = _expectation_cached(n - 1, next_lose_state.ratings, params)
        
        # このアクションの期待値
        # _expectation_cached が返すのは整数レートの期待値なので、そのまま計算に使う
        exp_action_idx = p * float(exp_win) + (1.0 - p) * float(exp_lose)
        action_expectations.append(exp_action_idx)

    return action_expectations