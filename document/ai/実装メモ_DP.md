# DP モジュール実装メモ

本メモは `src/core/*` の実装で導入したクラス・関数・変数を素早く把握できるようにまとめたものです。

---

## ファイル構成
| File | 目的 |
|------|------|
| `src/core/parameters.py` | 共通定数 (`RATING_STEP` など) と勝率関数 `win_prob` |
| `src/core/state.py`      | レートの状態（タプル）を不変オブジェクト `State` として表現 |
| `src/core/dp.py`         | 逐次 DP による期待値計算 `expectation` と最適行動 `best_action` |

---

## parameters.py
* **RATING_STEP**: `int` — レート変動幅 $d$ (=16)。
* **K_COEFF**: `float` — 勝率の線形近似に使う係数 $k$。デフォルトは $1/800$ で「800 レート差で勝率 ±0.5」。
* **MU**: `int` — 共通適正レート (中央値)。
* **win_prob(r)**: 勝率 $p(r)=0.5-k",(r-\mu)$ を返す。クリップ済み。
* **Parameters dataclass**: 複数パラメータをまとめて渡したいとき用の軽量ラッパ。

---

## state.py — `State`
* **コンセプト**: 内部は降順ソートされた `Tuple[float, ...]` を不変で保持→ハッシュ可能。
* **主要メソッド**
    * `best` — 現在の最大レート。
    * `after_match(idx, won)` — 指定アカで勝敗した後の新 `State` を返す。
    * `from_iterable()` — どんな並びでも降順に整形して生成。

---

## dp.py
### 1. `expectation(n, state)`
* 返り値: 残り `n` 試合で得られる最終レート期待値。
* ロジック: `@lru_cache` 付きの内部関数 `_expectation_cached` を呼び出し。
* 行動候補:
    1. **Stop** — 今すぐ終了 → 価値 = `state.best`。
    2. **Play idx** — 各アカウントで 1 戦:
       $p(v_i) P(n-1, v_i^+)+(1-p(v_i))P(n-1, v_i^-)$

### 2. `best_action(n, state)`
* None → 打ち切りが最適。
* 0..r-1 → そのインデックスのアカウントで潜るのが最適。

---

## ユニットテスト (tests/test_dp.py)
* `test_expectation_basic` — n=0,1 の基礎ケース。
* `test_stop_is_best` — 高レートが 1 つだけあるシナリオで Stop が最適になることを確認。

---
作成: AI アシスタント @ YYYY/MM/DD 