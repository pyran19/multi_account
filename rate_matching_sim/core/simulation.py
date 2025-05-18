import numpy as np
import pandas as pd
from typing import List, Dict, Tuple, Optional, Callable, Any
import uuid
from dataclasses import dataclass, field
import time
import json
from enum import Enum, auto


class AccountSelectionStrategy(Enum):
    """アカウント選択戦略の列挙型"""
    HIGHEST_RATE = auto()  # 最も高いレートのアカウントを選択
    SECOND_HIGHEST_RATE = auto()  # 2番目に高いレートのアカウントを選択
    LOWEST_RATE = auto()  # 最も低いレートのアカウントを選択
    RANDOM = auto()  # ランダムにアカウントを選択
    THRESHOLD_LOWEST = auto()  # 閾値以上のアカウントの中で最も低いレートのアカウントを選択
    CLOSEST_TO_AVERAGE = auto()  # 平均レートに最も近いアカウントを選択
    FARTHEST_FROM_AVERAGE = auto()  # 平均レートから最も遠いアカウントを選択
    CUSTOM = auto()  # カスタム戦略


@dataclass
class Account:
    """レート戦に参加するアカウント"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    initial_rate: float = 1500.0
    rate: float = 1500.0
    true_skill: float = 1500.0  # 適正レート
    matches_played: int = 0
    match_history: List[Dict] = field(default_factory=list)
    
    def reset(self):
        """アカウントの状態をリセット"""
        self.rate = self.initial_rate
        self.matches_played = 0
        self.match_history = []
    
    def play_match(self, rate_change: float, timestamp: float) -> Dict:
        """レート戦に参加し、結果を記録
        
        Args:
            rate_change: レートの変化量（勝ちなら正、負けなら負）
            timestamp: 試合の時間
            
        Returns:
            試合の詳細
        """
        match_result = {
            "timestamp": timestamp,
            "rate_before": self.rate,
            "rate_change": rate_change,
            "won": rate_change > 0,
            "match_number": self.matches_played + 1
        }
        
        self.rate += rate_change
        self.matches_played += 1
        match_result["rate_after"] = self.rate
        self.match_history.append(match_result)
        
        return match_result
    
    def get_stats(self) -> Dict:
        """アカウントの統計情報を取得"""
        if not self.match_history:
            return {
                "account_id": self.id,
                "initial_rate": self.initial_rate,
                "current_rate": self.rate,
                "true_skill": self.true_skill,
                "matches_played": 0,
                "wins": 0,
                "losses": 0,
                "win_rate": 0.0,
                "rate_change": 0.0
            }
            
        wins = sum(1 for match in self.match_history if match["won"])
        losses = self.matches_played - wins
        win_rate = (wins / self.matches_played) * 100 if self.matches_played > 0 else 0
        rate_change = self.rate - self.initial_rate
        
        return {
            "account_id": self.id,
            "initial_rate": self.initial_rate,
            "current_rate": self.rate,
            "true_skill": self.true_skill,
            "matches_played": self.matches_played,
            "wins": wins,
            "losses": losses,
            "win_rate": round(win_rate, 2),
            "rate_change": round(rate_change, 2)
        }


class RateMatchingSimulator:
    """レート戦シミュレーター"""
    
    def __init__(
        self,
        num_accounts: int = 3,
        initial_rate: float = 1500.0,
        true_skill: float = 1500.0,
        rate_change: float = 16.0,
        win_rate_slope: float = 0.01,  # 勝率のレート勾配（レート差1につき勝率が変化する割合）
        convergence_matches: int = 20,  # 適正レートへの収束に必要な試合数
        random_seed: Optional[int] = None
    ):
        """レート戦シミュレーターの初期化
        
        Args:
            num_accounts: アカウント数
            initial_rate: 初期レート
            true_skill: 適正レート
            rate_change: 1試合あたりのレート変化量
            win_rate_slope: 勝率のレート勾配
            convergence_matches: 適正レートへの収束に必要な試合数
            random_seed: 乱数シード
        """
        if random_seed is not None:
            np.random.seed(random_seed)
            
        self.accounts = [
            Account(
                initial_rate=initial_rate,
                rate=initial_rate,
                true_skill=true_skill
            )
            for _ in range(num_accounts)
        ]
        
        self.rate_change = rate_change
        self.win_rate_slope = win_rate_slope
        self.convergence_matches = convergence_matches
        self.current_time = 0
        self.match_history = []
        
    def reset(self):
        """シミュレーターの状態をリセット"""
        for account in self.accounts:
            account.reset()
        self.current_time = 0
        self.match_history = []
    
    def calculate_win_probability(self, account: Account) -> float:
        """アカウントの勝率を計算
        
        Args:
            account: 対象のアカウント
            
        Returns:
            勝率（0.0〜1.0）
        """
        # 適正レートへの収束フェーズ
        if account.matches_played < self.convergence_matches:
            # 線形に適正レートに近づける
            progress = account.matches_played / self.convergence_matches
            expected_rate = account.initial_rate + (account.true_skill - account.initial_rate) * progress
            
            # 現在のレートと期待レートの差に基づいて勝率を調整
            rate_diff = expected_rate - account.rate
            # 勝率を調整（レート差がプラスなら勝ちやすく、マイナスなら負けやすく）
            win_prob = 0.5 + 0.5 * np.sign(rate_diff) * min(0.5, abs(rate_diff) / (2 * self.rate_change))
            return win_prob
        
        # 適正レート周辺での揺らぎフェーズ
        else:
            # 現在のレートと適正レートの差に基づいて勝率を計算
            rate_diff = account.true_skill - account.rate
            win_prob = 0.5 + self.win_rate_slope * rate_diff
            # 勝率を0.0〜1.0の範囲に制限
            return max(0.0, min(1.0, win_prob))
    
    def play_match(self, account_idx: int) -> Dict:
        """指定されたアカウントでレート戦を行う
        
        Args:
            account_idx: 使用するアカウントのインデックス
            
        Returns:
            試合の詳細
        """
        account = self.accounts[account_idx]
        
        # 勝率を計算
        win_prob = self.calculate_win_probability(account)
        
        # 勝敗を決定
        won = np.random.random() < win_prob
        
        # レート変化を計算
        rate_change = self.rate_change if won else -self.rate_change
        
        # 時間を進める
        self.current_time += 1
        
        # 試合を記録
        match_result = account.play_match(rate_change, self.current_time)
        self.match_history.append({
            "timestamp": self.current_time,
            "account_id": account.id,
            "account_idx": account_idx,
            "rate_before": match_result["rate_before"],
            "rate_after": match_result["rate_after"],
            "rate_change": match_result["rate_change"],
            "won": match_result["won"],
            "win_probability": win_prob
        })
        
        return match_result
    
    def get_account_stats(self) -> List[Dict]:
        """全アカウントの統計情報を取得"""
        return [account.get_stats() for account in self.accounts]
    
    def get_highest_rate(self) -> float:
        """最も高いレートを取得"""
        return max(account.rate for account in self.accounts)
    
    def get_match_history_df(self) -> pd.DataFrame:
        """試合履歴をDataFrameとして取得"""
        return pd.DataFrame(self.match_history)


class MultiAccountStrategy:
    """複数アカウント戦略"""
    
    def __init__(
        self,
        simulator: RateMatchingSimulator,
        strategy: AccountSelectionStrategy = AccountSelectionStrategy.HIGHEST_RATE,
        max_matches: int = 100,
        threshold_rate: float = None,
        custom_strategy_fn: Callable = None,
        early_stopping: bool = False,
        early_stopping_patience: int = 10,
        random_seed: Optional[int] = None
    ):
        """複数アカウント戦略の初期化
        
        Args:
            simulator: レート戦シミュレーター
            strategy: アカウント選択戦略
            max_matches: 最大試合数
            threshold_rate: 閾値レート（THRESHOLD_LOWEST戦略用）
            custom_strategy_fn: カスタム戦略関数
            early_stopping: 早期終了を使用するかどうか
            early_stopping_patience: 早期終了の忍耐回数
            random_seed: 乱数シード
        """
        self.simulator = simulator
        self.strategy = strategy
        self.max_matches = max_matches
        self.threshold_rate = threshold_rate
        self.custom_strategy_fn = custom_strategy_fn
        self.early_stopping = early_stopping
        self.early_stopping_patience = early_stopping_patience
        
        if random_seed is not None:
            np.random.seed(random_seed)
        
        self.total_matches_played = 0
        self.best_rate = -float('inf')
        self.matches_without_improvement = 0
        self.stopped_early = False
        
    def reset(self):
        """戦略の状態をリセット"""
        self.simulator.reset()
        self.total_matches_played = 0
        self.best_rate = -float('inf')
        self.matches_without_improvement = 0
        self.stopped_early = False
    
    def select_account(self) -> int:
        """次の試合に使用するアカウントを選択
        
        Returns:
            選択されたアカウントのインデックス
        """
        accounts = self.simulator.accounts
        rates = [account.rate for account in accounts]
        
        if self.strategy == AccountSelectionStrategy.HIGHEST_RATE:
            return np.argmax(rates)
            
        elif self.strategy == AccountSelectionStrategy.SECOND_HIGHEST_RATE:
            if len(rates) < 2:
                return 0
            sorted_indices = np.argsort(rates)
            return sorted_indices[-2]
            
        elif self.strategy == AccountSelectionStrategy.LOWEST_RATE:
            return np.argmin(rates)
            
        elif self.strategy == AccountSelectionStrategy.RANDOM:
            return np.random.randint(0, len(accounts))
            
        elif self.strategy == AccountSelectionStrategy.THRESHOLD_LOWEST:
            if self.threshold_rate is None:
                # 閾値が設定されていない場合は平均レートを使用
                self.threshold_rate = np.mean(rates)
                
            # 閾値以上のアカウントを抽出
            valid_indices = [i for i, rate in enumerate(rates) if rate >= self.threshold_rate]
            if not valid_indices:
                # 該当するアカウントがない場合は最も高いレートのアカウントを選択
                return np.argmax(rates)
                
            # 該当するアカウントの中で最も低いレートのアカウントを選択
            valid_rates = [rates[i] for i in valid_indices]
            return valid_indices[np.argmin(valid_rates)]
            
        elif self.strategy == AccountSelectionStrategy.CLOSEST_TO_AVERAGE:
            avg_rate = np.mean(rates)
            return np.argmin([abs(rate - avg_rate) for rate in rates])
            
        elif self.strategy == AccountSelectionStrategy.FARTHEST_FROM_AVERAGE:
            avg_rate = np.mean(rates)
            return np.argmax([abs(rate - avg_rate) for rate in rates])
            
        elif self.strategy == AccountSelectionStrategy.CUSTOM and self.custom_strategy_fn is not None:
            return self.custom_strategy_fn(accounts, self.total_matches_played)
            
        # デフォルトは最も高いレートのアカウント
        return np.argmax(rates)
    
    def should_continue(self) -> bool:
        """レート戦を続けるかどうかを判断
        
        Returns:
            続ける場合はTrue、終了する場合はFalse
        """
        # 最大試合数に達した場合は終了
        if self.total_matches_played >= self.max_matches:
            return False
            
        # 早期終了が有効で、一定回数改善がない場合は終了
        if self.early_stopping:
            current_best_rate = self.simulator.get_highest_rate()
            
            if current_best_rate > self.best_rate:
                self.best_rate = current_best_rate
                self.matches_without_improvement = 0
            else:
                self.matches_without_improvement += 1
                
            if self.matches_without_improvement >= self.early_stopping_patience:
                self.stopped_early = True
                return False
                
        return True
    
    def run(self) -> Dict:
        """戦略を実行
        
        Returns:
            実行結果
        """
        self.reset()
        
        while self.should_continue():
            account_idx = self.select_account()
            self.simulator.play_match(account_idx)
            self.total_matches_played += 1
        
        # 結果を集計
        final_highest_rate = self.simulator.get_highest_rate()
        account_stats = self.simulator.get_account_stats()
        
        result = {
            "strategy": self.strategy.name,
            "total_matches": self.total_matches_played,
            "final_highest_rate": final_highest_rate,
            "stopped_early": self.stopped_early,
            "account_stats": account_stats
        }
        
        return result


class StrategyComparison:
    """複数の戦略を比較"""
    
    def __init__(
        self,
        num_accounts: int = 3,
        initial_rate: float = 1500.0,
        true_skill: float = 1500.0,
        rate_change: float = 16.0,
        win_rate_slope: float = 0.01,
        convergence_matches: int = 20,
        max_matches: int = 100,
        num_simulations: int = 100,
        random_seed: Optional[int] = None
    ):
        """戦略比較の初期化
        
        Args:
            num_accounts: アカウント数
            initial_rate: 初期レート
            true_skill: 適正レート
            rate_change: 1試合あたりのレート変化量
            win_rate_slope: 勝率のレート勾配
            convergence_matches: 適正レートへの収束に必要な試合数
            max_matches: 最大試合数
            num_simulations: シミュレーション回数
            random_seed: 乱数シード
        """
        self.num_accounts = num_accounts
        self.initial_rate = initial_rate
        self.true_skill = true_skill
        self.rate_change = rate_change
        self.win_rate_slope = win_rate_slope
        self.convergence_matches = convergence_matches
        self.max_matches = max_matches
        self.num_simulations = num_simulations
        
        if random_seed is not None:
            self.random_seed = random_seed
            np.random.seed(random_seed)
        else:
            self.random_seed = None
        
        # 比較する戦略
        self.strategies = [
            AccountSelectionStrategy.HIGHEST_RATE,
            AccountSelectionStrategy.SECOND_HIGHEST_RATE,
            AccountSelectionStrategy.LOWEST_RATE,
            AccountSelectionStrategy.RANDOM,
            AccountSelectionStrategy.THRESHOLD_LOWEST,
            AccountSelectionStrategy.CLOSEST_TO_AVERAGE,
            AccountSelectionStrategy.FARTHEST_FROM_AVERAGE
        ]
        
        self.results = {}
    
    def run_comparison(self) -> Dict:
        """戦略比較を実行
        
        Returns:
            比較結果
        """
        self.results = {}
        
        for strategy in self.strategies:
            strategy_results = []
            
            for sim_idx in range(self.num_simulations):
                # シミュレーションごとに異なる乱数シードを使用
                if self.random_seed is not None:
                    sim_seed = self.random_seed + sim_idx
                else:
                    sim_seed = None
                
                # シミュレーターを初期化
                simulator = RateMatchingSimulator(
                    num_accounts=self.num_accounts,
                    initial_rate=self.initial_rate,
                    true_skill=self.true_skill,
                    rate_change=self.rate_change,
                    win_rate_slope=self.win_rate_slope,
                    convergence_matches=self.convergence_matches,
                    random_seed=sim_seed
                )
                
                # 戦略を実行
                multi_strategy = MultiAccountStrategy(
                    simulator=simulator,
                    strategy=strategy,
                    max_matches=self.max_matches,
                    random_seed=sim_seed
                )
                
                result = multi_strategy.run()
                strategy_results.append(result["final_highest_rate"])
            
            # 結果を集計
            self.results[strategy.name] = {
                "mean_highest_rate": np.mean(strategy_results),
                "std_highest_rate": np.std(strategy_results),
                "min_highest_rate": np.min(strategy_results),
                "max_highest_rate": np.max(strategy_results),
                "median_highest_rate": np.median(strategy_results),
                "all_results": strategy_results
            }
        
        return self.results
    
    def get_best_strategy(self) -> Tuple[str, Dict]:
        """最も良い戦略を取得
        
        Returns:
            (戦略名, 結果)のタプル
        """
        if not self.results:
            self.run_comparison()
            
        best_strategy = max(self.results.items(), key=lambda x: x[1]["mean_highest_rate"])
        return best_strategy
    
    def get_results_df(self) -> pd.DataFrame:
        """結果をDataFrameとして取得"""
        if not self.results:
            self.run_comparison()
            
        data = []
        for strategy_name, result in self.results.items():
            data.append({
                "strategy": strategy_name,
                "mean_highest_rate": result["mean_highest_rate"],
                "std_highest_rate": result["std_highest_rate"],
                "min_highest_rate": result["min_highest_rate"],
                "max_highest_rate": result["max_highest_rate"],
                "median_highest_rate": result["median_highest_rate"]
            })
            
        return pd.DataFrame(data)


def run_custom_simulation(
    strategy_name: str,
    num_accounts: int = 3,
    initial_rate: float = 1500.0,
    true_skill: float = 1500.0,
    rate_change: float = 16.0,
    win_rate_slope: float = 0.01,
    convergence_matches: int = 20,
    max_matches: int = 100,
    num_simulations: int = 100,
    random_seed: Optional[int] = None,
    custom_strategy_fn: Callable = None
) -> Dict:
    """カスタムシミュレーションを実行
    
    Args:
        strategy_name: 戦略名
        num_accounts: アカウント数
        initial_rate: 初期レート
        true_skill: 適正レート
        rate_change: 1試合あたりのレート変化量
        win_rate_slope: 勝率のレート勾配
        convergence_matches: 適正レートへの収束に必要な試合数
        max_matches: 最大試合数
        num_simulations: シミュレーション回数
        random_seed: 乱数シード
        custom_strategy_fn: カスタム戦略関数
        
    Returns:
        シミュレーション結果
    """
    # 戦略を選択
    try:
        strategy = AccountSelectionStrategy[strategy_name]
    except KeyError:
        if custom_strategy_fn is not None:
            strategy = AccountSelectionStrategy.CUSTOM
        else:
            strategy = AccountSelectionStrategy.HIGHEST_RATE
    
    results = []
    detailed_results = []
    
    for sim_idx in range(num_simulations):
        # シミュレーションごとに異なる乱数シードを使用
        if random_seed is not None:
            sim_seed = random_seed + sim_idx
        else:
            sim_seed = None
        
        # シミュレーターを初期化
        simulator = RateMatchingSimulator(
            num_accounts=num_accounts,
            initial_rate=initial_rate,
            true_skill=true_skill,
            rate_change=rate_change,
            win_rate_slope=win_rate_slope,
            convergence_matches=convergence_matches,
            random_seed=sim_seed
        )
        
        # 戦略を実行
        multi_strategy = MultiAccountStrategy(
            simulator=simulator,
            strategy=strategy,
            max_matches=max_matches,
            custom_strategy_fn=custom_strategy_fn,
            random_seed=sim_seed
        )
        
        result = multi_strategy.run()
        results.append(result["final_highest_rate"])
        detailed_results.append(result)
    
    # 結果を集計
    summary = {
        "strategy": strategy_name,
        "mean_highest_rate": float(np.mean(results)),
        "std_highest_rate": float(np.std(results)),
        "min_highest_rate": float(np.min(results)),
        "max_highest_rate": float(np.max(results)),
        "median_highest_rate": float(np.median(results)),
        "num_simulations": num_simulations,
        "detailed_results": detailed_results[:5]  # 最初の5つの詳細結果のみ含める
    }
    
    return summary