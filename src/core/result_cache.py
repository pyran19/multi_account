import os
import csv
from pathlib import Path
import glob
from typing import Dict, Tuple, Optional, List, Set


# ---------------------------------------------
# 出力ファイル/ディレクトリ設定
# ---------------------------------------------

OUTPUT_DIR = Path("results/cache")

# ファイル名テンプレート (例: output/n100_acc3.txt)
FILE_TEMPLATE = "n{n}_acc{acc}.txt"

# キャッシュされたレート組合せを管理するグローバル辞書
# key: (n, accounts), value: {ratings, ...}
_cached_ratings: Dict[Tuple[int, int], Set[Tuple[int, ...]]] = {}

# ---------------------------------------------
# パブリック API
# ---------------------------------------------

def load_cache(n: int, accounts: int) -> Dict[Tuple[int, ...], Tuple[float, Optional[int]]]:
    """保存済み結果ファイルを読み込み、辞書を返す。


    戻り値の dict は
        key   : ratings タプル (降順) - 整数レート
        value : (expectation, best_action)
    という形式。

    保存ファイルが存在しない場合は空 dict を返す。
    """
    path = OUTPUT_DIR / FILE_TEMPLATE.format(n=n, acc=accounts)
    if not path.exists():
        return {}

    results: Dict[Tuple[int, ...], Tuple[float, Optional[int]]] = {}
    cached_ratings_set = set()

    with path.open(mode="r", encoding="utf-8") as f:
        reader = csv.reader(_skip_header_lines(f, header_line_count=4))
        for row in reader:
            if not row:
                continue  # 空行ガード
            # ratings * accounts, expectation, best_action
            ratings = tuple(map(int, row[:accounts]))
            cached_ratings_set.add(ratings)
            
            expectation_val = float(row[accounts])
            
            best_action_val: Optional[int]
            if row[accounts + 1] == "" or row[accounts + 1].lower() == "none":
                best_action_val = None
            else:
                best_action_val = int(row[accounts + 1])
            results[ratings] = (expectation_val, best_action_val)
    
    # グローバルキャッシュに保存
    _cached_ratings[(n, accounts)] = cached_ratings_set
    return results


def load_available_caches(accounts: int) -> Dict[int, Dict[Tuple[int, ...], Tuple[float, Optional[int]]]]:
    """利用可能な全ての中間キャッシュを読み込みます。
    
    戻り値:
        Dict[int, Dict] - key: n値, value: そのnに対応するキャッシュ辞書
    """
    result = {}
    
    # results/cacheディレクトリのn*_acc{accounts}.txtファイルをすべて見つける
    cache_pattern = str(OUTPUT_DIR / f"n*_acc{accounts}.txt")
    for cache_file in glob.glob(cache_pattern):
        # ファイル名からn値を抽出
        filename = os.path.basename(cache_file)
        n_str = filename.split('_')[0][1:]  # 'n100_acc2.txt' -> '100'
        try:
            n = int(n_str)
            # キャッシュをロード
            result[n] = load_cache(n, accounts)
        except ValueError:
            # ファイル名形式が無効な場合はスキップ
            continue
    
    return result


def save_result(
    n: int,
    accounts: int,
    ratings: Tuple[int, ...],
    expectation_val: float,
    best_action_val: Optional[int],
) -> None:
    """計算結果を保存ファイルに追記 (新規/既存両対応)。

    同じ ratings が既に存在する場合はスキップ (上書きしない)。
    
    注意：内部では整数レートに変換して保存します。
    """
    # 既にキャッシュされているかチェック
    if (n, accounts) in _cached_ratings and ratings in _cached_ratings[(n, accounts)]:
        # すでにキャッシュ済みの場合は何もしない
        return
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / FILE_TEMPLATE.format(n=n, acc=accounts)

    # ファイルが無い場合はヘッダを書き込む
    new_file = not path.exists()

    with path.open(mode="a", encoding="utf-8", newline="") as f:
        if new_file:
            # 1,2 行目: パラメータ
            f.write(f"n={n}\n")
            f.write(f"r={accounts}\n\n")
            # 4 行目: ヘッダ
            header_cols = [f"account{i+1}" for i in range(accounts)] + [
                "expectation",
                "best_action",
            ]
            f.write(", ".join(header_cols) + "\n")
        writer = csv.writer(f)
        row: List[str] = [str(r) for r in ratings] + [
            str(expectation_val),
            "" if best_action_val is None else str(best_action_val),
        ]
        writer.writerow(row)
    
    # グローバルキャッシュに追加
    if (n, accounts) not in _cached_ratings:
        _cached_ratings[(n, accounts)] = set()
    _cached_ratings[(n, accounts)].add(ratings)


# ---------------------------------------------
# ヘルパ
# ---------------------------------------------

def _skip_header_lines(file_obj, header_line_count: int):
    """指定行数のヘッダを飛ばし、その後のイテレータを返す。"""
    for _ in range(header_line_count):
        next(file_obj, None)
    return file_obj 