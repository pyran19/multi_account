import os
import csv
from pathlib import Path
from typing import Dict, Tuple, Optional, List

from src.core.parameters import float_ratings_to_int, int_ratings_to_float, Parameters

# ---------------------------------------------
# 出力ファイル/ディレクトリ設定
# ---------------------------------------------

OUTPUT_DIR = Path("results/cache")

# ファイル名テンプレート (例: output/n100_acc3.txt)
FILE_TEMPLATE = "n{n}_acc{acc}.txt"

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

    with path.open(mode="r", encoding="utf-8") as f:
        reader = csv.reader(_skip_header_lines(f, header_line_count=4))
        for row in reader:
            if not row:
                continue  # 空行ガード
            # ratings * accounts, expectation, best_action
            ratings = tuple(map(int, row[:accounts]))
            
            expectation_val = float(row[accounts])
            
            best_action_val: Optional[int]
            if row[accounts + 1] == "" or row[accounts + 1].lower() == "none":
                best_action_val = None
            else:
                best_action_val = int(row[accounts + 1])
            results[ratings] = (expectation_val, best_action_val)
    return results


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
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / FILE_TEMPLATE.format(n=n, acc=accounts)

    
    # 既存の結果を読み込み (存在しない場合は空辞書)
    # 整数レートで保存されているため、整数レートベースでキーを検索する必要がある
    # キャッシュが実数レートで存在するかは検査しない（新旧混在あり得る）
    
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


# ---------------------------------------------
# ヘルパ
# ---------------------------------------------

def _skip_header_lines(file_obj, header_line_count: int):
    """指定行数のヘッダを飛ばし、その後のイテレータを返す。"""
    for _ in range(header_line_count):
        next(file_obj, None)
    return file_obj 