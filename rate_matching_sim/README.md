# レート戦略シミュレーター

このプロジェクトは、ランダムなレート変動が起こる環境での複数アカウント戦略のシミュレーションを行うためのツールです。MCPサーバーとして実装されており、様々な戦略の効果を比較・分析することができます。

## 機能

- 複数のアカウント選択戦略のシミュレーション
- 戦略間の比較分析
- カスタム戦略の実装と評価
- WebSocketとREST APIによるMCPサーバー
- インタラクティブなWebインターフェース

## 戦略の種類

1. **HIGHEST_RATE**: 最も高いレートのアカウントを使用
2. **SECOND_HIGHEST_RATE**: 2番目に高いレートのアカウントを使用
3. **LOWEST_RATE**: 最も低いレートのアカウントを使用
4. **RANDOM**: ランダムにアカウントを選択
5. **THRESHOLD_LOWEST**: 閾値以上のレートを持つアカウントの中で最も低いレートのアカウントを使用
6. **CLOSEST_TO_AVERAGE**: 平均レートに最も近いアカウントを使用
7. **FARTHEST_FROM_AVERAGE**: 平均レートから最も遠いアカウントを使用
8. **CUSTOM**: カスタム戦略（Pythonコードで定義）

## 使用方法

### サーバーの起動

```bash
# MCPサーバーを起動
python run_server.py --port 12000

# クライアントサーバーを起動
python run_client.py --port 12001
```

### Webインターフェースへのアクセス

ブラウザで以下のURLにアクセスします：

```
http://localhost:12001
```

### API使用例

#### WebSocket API

```javascript
// WebSocketに接続
const ws = new WebSocket('ws://localhost:12000/ws');

// シミュレーションリクエスト
ws.send(JSON.stringify({
    type: 'run_simulation',
    id: 'request-1',
    params: {
        strategy: 'HIGHEST_RATE',
        num_accounts: 3,
        initial_rate: 1500,
        true_skill: 1500,
        rate_change: 16,
        win_rate_slope: 0.01,
        convergence_matches: 20,
        max_matches: 100,
        num_simulations: 100
    }
}));

// 戦略比較リクエスト
ws.send(JSON.stringify({
    type: 'run_comparison',
    id: 'request-2',
    params: {
        num_accounts: 3,
        initial_rate: 1500,
        true_skill: 1500,
        rate_change: 16,
        win_rate_slope: 0.01,
        convergence_matches: 20,
        max_matches: 100,
        num_simulations: 100
    }
}));
```

#### REST API

```bash
# シミュレーション実行
curl -X POST http://localhost:12000/api/simulation \
  -H "Content-Type: application/json" \
  -d '{
    "strategy": "HIGHEST_RATE",
    "num_accounts": 3,
    "initial_rate": 1500,
    "true_skill": 1500,
    "rate_change": 16,
    "win_rate_slope": 0.01,
    "convergence_matches": 20,
    "max_matches": 100,
    "num_simulations": 100
  }'

# 戦略比較実行
curl -X POST http://localhost:12000/api/comparison \
  -H "Content-Type: application/json" \
  -d '{
    "num_accounts": 3,
    "initial_rate": 1500,
    "true_skill": 1500,
    "rate_change": 16,
    "win_rate_slope": 0.01,
    "convergence_matches": 20,
    "max_matches": 100,
    "num_simulations": 100
  }'
```

## カスタム戦略の作成

カスタム戦略を作成するには、以下のような関数を定義します：

```python
def select_account(accounts, total_matches_played):
    """
    カスタム戦略関数
    
    Args:
        accounts: アカウントのリスト
        total_matches_played: 現在までの総試合数
        
    Returns:
        使用するアカウントのインデックス
    """
    # 例: 試合数が偶数なら最高レート、奇数なら最低レートのアカウントを使用
    rates = [account.rate for account in accounts]
    if total_matches_played % 2 == 0:
        return np.argmax(rates)
    else:
        return np.argmin(rates)
```

## パラメータの説明

- **num_accounts**: アカウント数
- **initial_rate**: 初期レート
- **true_skill**: 適正レート
- **rate_change**: 1試合あたりのレート変化量
- **win_rate_slope**: 勝率のレート勾配（レート差1につき勝率が変化する割合）
- **convergence_matches**: 適正レートへの収束に必要な試合数
- **max_matches**: 最大試合数
- **num_simulations**: シミュレーション回数
- **random_seed**: 乱数シード（再現性のある結果を得るため）
- **threshold_rate**: 閾値レート（THRESHOLD_LOWEST戦略用）