# 実験計画書

## 1. 実験目的
複数アカウントを用いたレートマッチングにおいて、最適戦略と各種非最適戦略の性能を定量的に比較し、以下を明らかにする：

1. 残り試合数 `n` に対する最終レート期待値の変化
2. アカウント数 `r` が与える影響の定量化  
3. 各アカウントのレート分布 `v` と戦略性の関係
4. 最適戦略と各種ベースライン戦略の性能差

## 2. 実験条件

### 2.1 共通パラメータ
```python
# 基本パラメータ
RATING_STEP = 16      # 1試合あたりのレート変動幅
K_COEFF = log(10)/1600  # 勝率の線形近似係数
MU = 1500             # プレイヤーの適正レート
```

### 2.2 実験変数
- 残り試合数 `n`: 10, 20, 50, 100, 200
- アカウント数 `r`: 1, 2, 3, 4, 5
- 初期レート分布パターン:
  - 均等配置: 全アカウント同一レート (μ=1500)
  - 分散配置: [1550, 1450], [1600, 1500, 1400] など
  - 偏在配置: [1600, 1400, 1400] など

## 3. 実験項目

### 3.1 最適戦略の分析
**目的**: 動的計画法により求めた最適戦略の特性を理解する

**実施方法**:
```bash
# 基本ケース (2アカウント、均等配置)
python -m src.cli dp --n 100 --accounts 2 --initial 1500 1500

# レート差がある場合
python -m src.cli dp --n 100 --accounts 2 --initial 1550 1450

# 3アカウント以上
python -m src.cli dp --n 100 --accounts 3 --initial 1500 1500 1500
```

**分析内容**:
- 各状態での最適アクション（`best_action`）の傾向
- 期待値の推移
- 打ち止め（early stopping）が発生する条件

### 3.2 残り試合数 n に対する定量性
**目的**: nの増加に伴う期待値の変化を把握する

**実施方法**:
```bash
# nを変えて期待値を計算
for n in [10, 20, 50, 100, 200]:
    for r in [1, 2, 3, 4, 5]:
        python -m src.cli dp --n $n --accounts $r
```

**可視化**: 横軸n、縦軸期待値のグラフ（アカウント数ごとに色分け）

### 3.3 アカウント数 r に対する定量性
**目的**: アカウント数増加の限界効用を検証する

**実施方法**:
```bash
# 固定n=100で、アカウント数を変化
for r in range(1, 6):
    python -m src.cli dp --n 100 --accounts $r
```

**可視化**: 横軸r、縦軸期待値のグラフ

### 3.4 レート分布 v の影響
**目的**: 初期レート分布が最終期待値に与える影響を調査

**実施パターン**:
```bash
# パターン1: 均等配置
python -m src.cli dp --n 100 --accounts 3 --initial 1500 1500 1500

# パターン2: 等間隔分散
python -m src.cli dp --n 100 --accounts 3 --initial 1600 1500 1400

# パターン3: 偏在配置
python -m src.cli dp --n 100 --accounts 3 --initial 1600 1400 1400

# パターン4: 極端な偏在
python -m src.cli dp --n 100 --accounts 3 --initial 1700 1400 1400
```

### 3.5 モンテカルロシミュレーションによる検証
**目的**: DPの結果を実際のシミュレーションで確認する

**実施方法**:
```bash
# 各種ポリシーの比較（基本ケース）
python -m src.cli sim --n 100 --accounts 2 --initial 1500 1500 \
    --episodes 10000 --policy all --visualize --output-dir results/

# 大規模ケース
python -m src.cli sim --n 200 --accounts 3 --initial 1500 1500 1500 \
    --episodes 10000 --policy all --visualize --output-dir results/
```

**比較するポリシー**:
- `OptimalPolicy`: DP による最適戦略（※現在コメントアウト中）
- `RandomPolicy`: ランダム選択
- `FixedPolicy(0)`: 常に最高レートアカウント使用
- `FixedPolicy(1)`: 常に2番目のアカウント使用
- `GreedyPolicy`: 常に最低レートアカウント使用

### 3.6 戦略間の性能比較
**目的**: 最適戦略の優位性を定量化する

**評価指標**:
- 最終レート期待値の差
- 標準偏差の比較
- レート分布のヒストグラム

## 4. 追加機能

### 4.1 必要な追加実装

#### 1. 実験自動化スクリプト
```python
# src/experiments/run_experiments.py
def run_n_dependency_experiment():
    """nに対する依存性実験を自動実行"""
    results = []
    for n in [10, 20, 50, 100, 200]:
        for r in [1, 2, 3, 4, 5]:
            state = State.from_iterable([MU] * r)
            exp = expectation(n, state, Parameters())
            results.append({'n': n, 'r': r, 'expectation': exp})
    return pd.DataFrame(results)
```

#### 2. 最適アクション分析機能
```python
# src/core/analysis.py
def analyze_optimal_actions(n: int, initial_state: State, params: Parameters):
    """最適戦略の選択パターンを分析"""
    action_history = []
    state = initial_state
    
    for i in range(n):
        action = best_action(n-i, state, params)
        if action is None:
            break
        action_history.append({
            'step': i,
            'state': state.ratings,
            'action': action,
            'selected_rating': state.ratings[action]
        })
        # シミュレートして次の状態へ
        # ...
    
    return pd.DataFrame(action_history)
```

#### 3. バッチ実験実行機能
```python
# src/experiments/batch_runner.py
def run_batch_experiments(config_file: str):
    """設定ファイルから複数の実験を一括実行"""
    with open(config_file) as f:
        configs = json.load(f)
    
    for config in configs:
        # DP実験
        if config['type'] == 'dp':
            run_dp_experiment(config)
        # シミュレーション実験
        elif config['type'] == 'sim':
            run_sim_experiment(config)
```

#### 4. 結果集計・可視化の拡張
```python
# src/visualization/advanced_plots.py
def plot_n_dependency(results_df):
    """n依存性のグラフを生成"""
    
def plot_r_dependency(results_df):
    """アカウント数依存性のグラフを生成"""
    
def plot_strategy_comparison_heatmap(results):
    """戦略比較のヒートマップを生成"""
```

### 4.2 OptimalPolicy の有効化
現在 `cli.py` でコメントアウトされている `OptimalPolicy` を有効化する必要があります：
```python
# src/cli.py line 122
policies = [
    OptimalPolicy(params),  # コメントアウトを解除
    RandomPolicy(params),
    # ...
]
```

## 5. 実験実施手順

### 5.1 環境準備
```bash
# 仮想環境の作成
python -m venv venv
venv\Scripts\activate  # Windows

# 依存パッケージのインストール
pip install numpy matplotlib pandas
```

### 5.2 実験の実行順序
1. **小規模動作確認**: n=10, r=2 で基本動作を確認
2. **DP実験**: 各種パラメータでの期待値計算
3. **シミュレーション検証**: DPの結果をMonte Carloで検証
4. **大規模実験**: n=200, r=5 などの計算量の多いケース
5. **結果分析・可視化**: 収集したデータから知見を抽出

### 5.3 結果の保存
```
results/
├── dp_results/
│   ├── n_dependency.csv
│   ├── r_dependency.csv
│   └── v_patterns.csv
├── simulation_results/
│   ├── policy_comparison_n100_r2.csv
│   └── ...
└── figures/
    ├── n_dependency.png
    ├── r_dependency.png
    └── policy_comparison.png
```

## 6. 期待される結果と仮説

### 6.1 仮説
1. **最適戦略は概ね2番目のアカウントを選択する**
   - 最高レートは温存、最低レートは改善余地が少ない
   
2. **アカウント数は2-3個で飽和する**
   - r≥3では限界効用が急減
   
3. **nに対してlog的な成長**
   - 1アカウントではO(log n)
   - 複数アカウントでも同様の傾向

### 6.2 検証ポイント
- 数値誤差による最適アクションの揺れ
- 初期レート分布による戦略の変化
- 打ち止め（early stopping）の発生条件

## 7. まとめ
本実験計画に従って体系的に実験を実施することで、複数アカウント戦略の定量的な理解が得られます。特に、最適戦略とベースライン戦略の性能差を明確に示すことで、戦略的なアカウント運用の重要性を実証できます。 