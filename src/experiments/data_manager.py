"""
実験データ管理モジュール

実験データのCSV保存、設定ファイル（JSON）の管理、
データの読み込み機能を提供します。
"""

import json
import csv
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
import numpy as np


class ExperimentDataManager:
    """実験データの管理クラス"""
    
    def __init__(self, base_dir: str = "data/experiments"):
        """
        データマネージャーの初期化
        
        Args:
            base_dir: データ保存のベースディレクトリ
        """
        self.base_dir = Path(base_dir)
        self.csv_dir = self.base_dir / "csv"
        self.graph_dir = self.base_dir / "graphs"
        self.config_dir = self.base_dir / "configs"
        
        # ディレクトリが存在しない場合は作成
        self._ensure_directories()
    
    def _ensure_directories(self):
        """必要なディレクトリを作成"""
        for dir_path in [self.csv_dir, self.graph_dir, self.config_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
    
    def generate_filename(self, prefix: str = "xp", extension: str = "csv") -> str:
        """
        タイムスタンプ付きのファイル名を生成
        
        Args:
            prefix: ファイル名のプレフィックス
            extension: ファイルの拡張子
            
        Returns:
            生成されたファイル名
        """
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        return f"{prefix}_{timestamp}.{extension}"
    
    def save_xp_data(self, x_values: List[float], 
                     p_values: List[List[float]], 
                     x_label: str = "x") -> str:
        """
        x-Pプロットデータをcsv保存する
        
        Args:
            x_values: xの値のリスト
            p_values: 各アカウントの期待値リスト（2次元配列）
            x_label: xのラベル（デフォルトは"x"）
            
        Returns:
            保存したファイルのパス
        """
        filename = self.generate_filename("xp", "csv")
        filepath = self.csv_dir / filename
        
        # CSVヘッダーの作成
        account_count = len(p_values[0]) if p_values else 0
        headers = [x_label] + [f"P{i+1}" for i in range(account_count)]
        
        # データの書き込み
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(headers)
            
            for x, p_row in zip(x_values, p_values):
                # 期待値は小数値として保存
                row = [x] + p_row
                writer.writerow(row)
        
        return str(filepath)
    
    def save_experiment_config(self, config_name: str, config_data: Dict[str, Any]) -> str:
        """
        実験設定をJSON形式で保存
        
        Args:
            config_name: 設定ファイル名（拡張子なし）
            config_data: 設定データの辞書
            
        Returns:
            保存したファイルのパス
        """
        filepath = self.config_dir / f"{config_name}.json"
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=2, ensure_ascii=False)
        
        return str(filepath)
    
    def create_xp_config(self, csv_filename: str, graph_filename: str,
                         account_count: int, x_type: str,
                         fixed_params: Dict[str, Any],
                         additional_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        x-Pプロット用の設定データを作成
        
        Args:
            csv_filename: CSVファイル名
            graph_filename: グラフ画像ファイル名
            account_count: アカウント数
            x_type: xの種類（n, v0, dv等）
            fixed_params: 固定パラメータの辞書
            additional_info: 追加情報（オプション）
            
        Returns:
            設定データの辞書
        """
        config = {
            "csv_ref": csv_filename,
            "graph_ref": graph_filename,
            "account_count": account_count,
            "x_type": x_type,
            "fixed_params": fixed_params,
            "timestamp": datetime.now().isoformat()
        }
        
        if additional_info:
            config["additional_info"] = additional_info
        
        return config
    
    def load_xp_data(self, csv_filename: str) -> tuple[List[float], List[List[float]], str]:
        """
        保存されたx-Pプロットデータを読み込む
        
        Args:
            csv_filename: CSVファイル名
            
        Returns:
            (x_values, p_values, x_label) のタプル
        """
        filepath = self.csv_dir / csv_filename
        
        x_values = []
        p_values = []
        x_label = "x"
        
        with open(filepath, 'r', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            headers = next(reader)
            x_label = headers[0]
            
            for row in reader:
                x_values.append(float(row[0]))
                # 期待値は小数値として保存されている
                p_values.append([float(val) for val in row[1:]])
        
        return x_values, p_values, x_label
    
    def load_experiment_config(self, config_filename: str) -> Dict[str, Any]:
        """
        実験設定を読み込む
        
        Args:
            config_filename: 設定ファイル名
            
        Returns:
            設定データの辞書
        """
        filepath = self.config_dir / config_filename
        
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def list_experiments(self) -> Dict[str, List[str]]:
        """
        保存されている実験ファイルの一覧を取得
        
        Returns:
            各ディレクトリのファイル一覧の辞書
        """
        return {
            "csv_files": [f.name for f in self.csv_dir.glob("*.csv")],
            "graph_files": [f.name for f in self.graph_dir.glob("*.png")],
            "config_files": [f.name for f in self.config_dir.glob("*.json")]
        } 