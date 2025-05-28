# 複数アカウントにおけるレートマッチング最適戦略

<p align="center">
  <img src="https://user-images.githubusercontent.com/placeholder/elo.png" width="400" alt="illustration"/>
</p>

本リポジトリでは、**複数アカウントを保有するプレイヤーが、限られた試合数でどのようにレート戦へ参加すれば最終レート（シーズン終了時に最も高いアカウントのレート）の期待値を最大化できるか**を、理論計算と数値シミュレーションの両面から解析します。

---

## 1. 背景と課題
多くのオンラインゲームでは Elo をベースにしたレーティングが用いられ、シーズン終了時の"瞬間レート"でランキングが決まります。複数アカウントを同時運用する場合、**最も高いレートを持つアカウントだけが順位に反映される**ため、

* どのタイミングでどのアカウントを出すべきか？
* 途中で"打ち止め"にして確定すべきか？

といった戦略が総合レートの期待値に影響します。本プロジェクトはこれを**動的計画法 (DP) による逐次最適化**で厳密に評価し、Monte-Carlo シミュレーションで検証します。

---

## 2. 解析モデル
1. レート変動: 1 試合ごとに固定値 $\pm 16$ 増減。
2. 勝率関数: 線形近似 $p(r)=0.5 - k (r - \mu)$。適正レート $\mu$ に収束するイメージ。
3. 各アカウントは同じ $\mu$ を共有し、初期レートから $N_0$ 試合で近傍に到達後、"揺らぎ"フェーズに入ると仮定。
4. 全アカウントの総試合数に上限 $N$ を設け、途中で打ち切ることも可能。
5. 終了時は最大レートを採用。

詳細な数式は `document/permanent/期待値逐次解法.md` を参照してください。

---

## 3. リポジトリ構成
```
├── document/
│   ├── fleeting/   # アイデアメモ（走り書き）
│   ├── ai/         # 実装計画など自動生成ドキュメント
│   └── permanent/  # 確定仕様・最終レポート
│
└── src/            # 実装コード
    ├── core/       # DP・数式処理
    ├── simulator/  # Monte-Carlo シミュレーション
    └── tests/      # pytest
```

---

## 4. 今後のロードマップ
- [ ] ドキュメント整備
  - [x] 下書き（fleeting）
  - [x] AI による清書（current）
  - [x] レビュー後 permanent へ昇格
- [x] 期待値 DP モジュール実装
- [x] シミュレーション実装
- [ ] 小規模ケースでの検証
- [ ] 大規模実験 & 可視化
- [ ] 考察・レポートまとめ

## 5. 計算結果の保存と再利用

DP 計算は試合数 `n` とアカウント数 `r` が増えるにつれ指数的に時間が掛かります。
そこで、本リポジトリでは**計算結果をディスクにキャッシュ**し、同じ条件を再度計算する場合に再利用します。

### 5.1 仕組み
1. `src/cli.py` の `dp` サブコマンド実行時、
   - まず `results/cache/n{n}_acc{r}.txt` を探索し、該当するレート列があればその値を読み込みます (再計算しない)。
   - 無ければ通常通り DP を実行し、得られた期待値と最適アクションをファイルへ追記します。
2. これにより **一度計算した状態は永続的にキャッシュ** されるため、次回以降は即時に結果を取得できます。

### 5.2 出力ファイル形式
```
results/cache/n100_acc3.txt
n=100
r=3

account1, account2, account3, expectation, best_action
0, 0, 0, 3, 1
1, 0, 0, 4, 1
1, 1, 0, 5, 1
```
* 先頭 2 行: パラメータ (`n`, `r`)
* 空行
* ヘッダ行
* 以降は `[アカウント毎のレート], 期待値, best_action` を CSV 形式で追記します。
* **全てのレートは整数表現で記録**されます（詳細は「6. レートの整数化」参照）。

### 5.3 使い方
```bash
# 例) 残り 20 試合、アカウント 3 つで全て 1500 スタートの場合
python -m src.cli dp --n 20 --accounts 3
```
初回は DP 計算を行い、2 回目以降はキャッシュが利用されます。

## 6. レートの整数化

計算効率と数値安定性のために、内部処理では**レートを整数値**として扱います。

### 6.1 変換方法
実数レート `r` から整数レート `i` への変換：
```
i = round((r - μ) / d)
```
ここで、
- `r`: 実数レート（例: 1500、1516 など）
- `μ`: 適正レート（デフォルト 1500）
- `d`: レート変動幅（デフォルト 16）

整数レートは「適正レートから何回勝ったか」を表す値になります。
例: 1500 → 0, 1516 → 1, 1484 → -1

### 6.2 メリット
1. **キャッシュの効率化**: 微小な数値誤差でキャッシュが効かなくなる問題を防止
2. **メモリ効率**: 実数より整数のほうがメモリ使用量が少ない
3. **計算安定性**: 同じパラメータでの計算結果が常に同一になる

### 6.3 実装詳細
- ユーザー入出力インターフェースは従来通り実数レートを使用
- 内部計算と永続化（キャッシュ）では整数レートを使用
- 変換関数は `src/core/parameters.py` で定義

---

## 7. MCP Server for AI Integration

### Purpose
The MCP (Monte Carlo Planner) Server provides an HTTP interface to run Dynamic Programming (DP) calculations and Monte Carlo simulations. This allows external programs, such as AI agents or other planning tools, to leverage the core logic of this repository without direct Python integration.

### Starting the Server
To start the server, run the following command from the root of the repository:
```bash
python -m src.mcp_server
```
By default, the server listens on port `8080`. You can specify a different port using the `--port` argument (though this CLI argument is not explicitly implemented in the current `src.mcp_server.py`, the code structure allows for it to be added if needed; currently, it uses the `PORT` variable). For example, to run on port 8000 if `PORT` was changed or if argument parsing was added:
```bash
# Assuming PORT variable in mcp_server.py is changed or --port is implemented
# python -m src.mcp_server --port 8000
```
Currently, to change the port, you would need to modify the `PORT` variable in `src/mcp_server.py`.

### Endpoint
The server exposes a single endpoint for all operations:
*   **`POST /mcp`**

### Request Format
All requests must be HTTP POST requests with a JSON body and `Content-Type: application/json`.

The JSON body must contain a `command` field specifying the operation ("dp" or "sim") and other parameters based on the command.

**Common Parameters (for both `dp` and `sim`):**
*   `command` (string, required): The command to execute. Must be `"dp"` or `"sim"`.
*   `n` (integer, required): The number of remaining matches. Must be a non-negative integer.
*   `accounts` (integer, optional, default: `2`): The number of accounts. Must be a positive integer.
*   `initial` (list of numbers, optional, default: `null` which results in `mu` for all accounts): A list of initial float ratings for each account. If provided, its length must match `accounts`.
*   `rating_step` (number, optional, default: `16`): The rating change per match (e.g., 16 points).
*   `k_coeff` (number, optional, default: `math.log(10) / 1600` ≈ `0.001439`): The k-coefficient for the linear win probability approximation.
*   `mu` (number, optional, default: `1500.0`): The player's true/mean rating.

**Parameters specific to the `sim` command:**
*   `episodes` (integer, optional, default: `1000`): The number of simulation episodes to run. Must be a positive integer.
*   `policy` (string, optional, default: `"all"`): The policy to use for simulation. Valid values include `"optimal"`, `"random"`, `"fixed"`, `"greedy"`, `"all"`.
*   `fixed_idx` (integer, optional, default: `0`): The account index to use if `policy` is `"fixed"`. Must be a non-negative integer and less than `accounts`.
*   `visualize` (boolean, optional, default: `false`): Whether to generate and save visualization plots. If `true`, `matplotlib` must be installed.
*   `output_dir` (string, optional, default: `.`): The directory where visualization plots will be saved if `visualize` is `true`.

### Response Format

**Success Response (common structure):**
```json
{
  "status": "success",
  "command": "<command_executed>",
  "results": {
    // Command-specific results go here
  }
}
```

**For `dp` command, `results` will contain:**
```json
{
  "expected_value_int": 1510, // Integer representation of expected max rating
  "best_action_account_index": 0, // Index of account to play, or null to stop
  "using_cache": false,
  "initial_ratings_int": [0, 0], // Integer ratings
  "initial_ratings_float": [1500.0, 1500.0] // Float ratings
}
```

**For `sim` command, `results` will contain:**
```json
{
  "simulation_results": [ /* list of simulation result objects/dicts */ ],
  "visualization_files": [ /* list of paths to saved plot images if visualize=true */ ],
  "initial_ratings_int": [0, 0],
  "initial_ratings_float": [1500.0, 1500.0],
  "error": "Optional error message if visualization failed, e.g., matplotlib not found"
}
```
If visualization produces an error (e.g., `matplotlib` not found when `visualize: true`), the main response status will still be `200 OK` and `status: "success"`, but the `results.error` field will contain the error message, and the top-level response will also include `warning_visualization: "<error_message>"`.

**Error Response (e.g., HTTP 400 for bad request, HTTP 500 for server error):**
```json
{
  "status": "error",
  "message": "<Detailed error message>"
}
```

### Example Usage

**1. DP Calculation Request:**
```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{
        "command": "dp",
        "n": 10,
        "accounts": 2,
        "initial": [1500.0, 1520.0],
        "mu": 1500.0,
        "rating_step": 16,
        "k_coeff": 0.001439
      }' \
  http://localhost:8080/mcp
```

**Expected DP Response (example):**
```json
{
  "status": "success",
  "command": "dp",
  "results": {
    "expected_value_int": 10, 
    "best_action_account_index": 1,
    "using_cache": false,
    "initial_ratings_int": [0, 1], 
    "initial_ratings_float": [1500.0, 1516.0] 
  }
}
```
*(Note: `expected_value_int` and `initial_ratings_int` are based on the integer representation relative to `mu` and `rating_step`. The example values are illustrative.)*

**2. Simulation Request:**
```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{
        "command": "sim",
        "n": 20,
        "accounts": 2,
        "initial": [1480.0, 1500.0],
        "episodes": 100,
        "policy": "greedy",
        "visualize": false
      }' \
  http://localhost:8080/mcp
```

**Expected Simulation Response (example):**
```json
{
  "status": "success",
  "command": "sim",
  "results": {
    "simulation_results": [
      { /* result structure for GreedyPolicy */ } 
      // ... (structure depends on SimulationResult details)
    ],
    "visualization_files": [],
    "initial_ratings_int": [-1, 0], 
    "initial_ratings_float": [1484.0, 1500.0]
  }
}
```
*(Note: `initial_ratings_float` in response might be slightly different from input due to internal float to int conversion and back, if input is not a multiple of `rating_step` from `mu`.)*

