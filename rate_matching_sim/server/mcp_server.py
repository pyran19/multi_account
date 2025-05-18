import sys
import os
import json
from typing import Dict, List, Any, Optional, Callable
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from pydantic import BaseModel, Field
import numpy as np
import pandas as pd
import logging
import uuid
from enum import Enum

# Add parent directory to path so we can import simulation module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.simulation import (
    RateMatchingSimulator, 
    MultiAccountStrategy, 
    StrategyComparison, 
    AccountSelectionStrategy,
    run_custom_simulation
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(title="Rate Matching Simulation MCP Server")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models for request/response validation
class StrategyEnum(str, Enum):
    HIGHEST_RATE = "HIGHEST_RATE"
    SECOND_HIGHEST_RATE = "SECOND_HIGHEST_RATE"
    LOWEST_RATE = "LOWEST_RATE"
    RANDOM = "RANDOM"
    THRESHOLD_LOWEST = "THRESHOLD_LOWEST"
    CLOSEST_TO_AVERAGE = "CLOSEST_TO_AVERAGE"
    FARTHEST_FROM_AVERAGE = "FARTHEST_FROM_AVERAGE"
    CUSTOM = "CUSTOM"

class SimulationParams(BaseModel):
    strategy: StrategyEnum = Field(StrategyEnum.HIGHEST_RATE, description="アカウント選択戦略")
    num_accounts: int = Field(3, description="アカウント数", ge=1, le=10)
    initial_rate: float = Field(1500.0, description="初期レート")
    true_skill: float = Field(1500.0, description="適正レート")
    rate_change: float = Field(16.0, description="1試合あたりのレート変化量", gt=0)
    win_rate_slope: float = Field(0.01, description="勝率のレート勾配", ge=0.001, le=0.1)
    convergence_matches: int = Field(20, description="適正レートへの収束に必要な試合数", ge=0)
    max_matches: int = Field(100, description="最大試合数", ge=1)
    num_simulations: int = Field(100, description="シミュレーション回数", ge=1, le=1000)
    random_seed: Optional[int] = Field(None, description="乱数シード")
    threshold_rate: Optional[float] = Field(None, description="閾値レート（THRESHOLD_LOWEST戦略用）")
    custom_strategy_code: Optional[str] = Field(None, description="カスタム戦略のPythonコード")

class ComparisonParams(BaseModel):
    num_accounts: int = Field(3, description="アカウント数", ge=1, le=10)
    initial_rate: float = Field(1500.0, description="初期レート")
    true_skill: float = Field(1500.0, description="適正レート")
    rate_change: float = Field(16.0, description="1試合あたりのレート変化量", gt=0)
    win_rate_slope: float = Field(0.01, description="勝率のレート勾配", ge=0.001, le=0.1)
    convergence_matches: int = Field(20, description="適正レートへの収束に必要な試合数", ge=0)
    max_matches: int = Field(100, description="最大試合数", ge=1)
    num_simulations: int = Field(100, description="シミュレーション回数", ge=1, le=1000)
    random_seed: Optional[int] = Field(None, description="乱数シード")

class SimulationResponse(BaseModel):
    simulation_id: str
    strategy: str
    mean_highest_rate: float
    std_highest_rate: float
    min_highest_rate: float
    max_highest_rate: float
    median_highest_rate: float
    num_simulations: int
    detailed_results: List[Dict[str, Any]]

class ComparisonResponse(BaseModel):
    comparison_id: str
    results: Dict[str, Dict[str, Any]]
    best_strategy: str
    best_strategy_mean_rate: float

# Store active simulations and comparisons
active_simulations = {}
active_comparisons = {}

# WebSocket connections
websocket_connections = set()

# Custom strategy execution
def execute_custom_strategy(code_str: str) -> Callable:
    """カスタム戦略コードを実行可能な関数に変換
    
    Args:
        code_str: Pythonコード文字列
        
    Returns:
        戦略関数
    """
    if not code_str:
        return None
        
    try:
        # ローカル名前空間を作成
        local_namespace = {}
        
        # コードを実行
        exec(code_str, {"np": np}, local_namespace)
        
        # select_account関数を取得
        if "select_account" in local_namespace:
            return local_namespace["select_account"]
        else:
            logger.error("Custom strategy code must define a 'select_account' function")
            return None
    except Exception as e:
        logger.error(f"Error executing custom strategy code: {e}")
        return None

# MCP protocol handlers
async def handle_mcp_message(websocket: WebSocket, message: Dict):
    """MCP protocol messages handler"""
    try:
        message_type = message.get("type")
        
        if message_type == "run_simulation":
            # Run a new simulation
            params = SimulationParams(**message.get("params", {}))
            simulation_results = run_simulation(params)
            
            # Send response
            await websocket.send_json({
                "type": "simulation_results",
                "id": message.get("id"),
                "results": simulation_results
            })
            
        elif message_type == "run_comparison":
            # Run a strategy comparison
            params = ComparisonParams(**message.get("params", {}))
            comparison_results = run_comparison(params)
            
            # Send response
            await websocket.send_json({
                "type": "comparison_results",
                "id": message.get("id"),
                "results": comparison_results
            })
            
        elif message_type == "get_simulation":
            # Get existing simulation results
            simulation_id = message.get("simulation_id")
            if simulation_id not in active_simulations:
                await websocket.send_json({
                    "type": "error",
                    "id": message.get("id"),
                    "error": f"Simulation {simulation_id} not found"
                })
                return
                
            await websocket.send_json({
                "type": "simulation_results",
                "id": message.get("id"),
                "results": active_simulations[simulation_id]
            })
            
        elif message_type == "get_comparison":
            # Get existing comparison results
            comparison_id = message.get("comparison_id")
            if comparison_id not in active_comparisons:
                await websocket.send_json({
                    "type": "error",
                    "id": message.get("id"),
                    "error": f"Comparison {comparison_id} not found"
                })
                return
                
            await websocket.send_json({
                "type": "comparison_results",
                "id": message.get("id"),
                "results": active_comparisons[comparison_id]
            })
            
        elif message_type == "list_simulations":
            # List all active simulations
            simulation_list = [
                {
                    "simulation_id": sim_id,
                    "strategy": sim_data["strategy"],
                    "mean_highest_rate": sim_data["mean_highest_rate"]
                }
                for sim_id, sim_data in active_simulations.items()
            ]
            
            await websocket.send_json({
                "type": "simulation_list",
                "id": message.get("id"),
                "simulations": simulation_list
            })
            
        elif message_type == "list_comparisons":
            # List all active comparisons
            comparison_list = [
                {
                    "comparison_id": comp_id,
                    "best_strategy": comp_data["best_strategy"],
                    "best_strategy_mean_rate": comp_data["best_strategy_mean_rate"]
                }
                for comp_id, comp_data in active_comparisons.items()
            ]
            
            await websocket.send_json({
                "type": "comparison_list",
                "id": message.get("id"),
                "comparisons": comparison_list
            })
            
        else:
            # Unknown message type
            await websocket.send_json({
                "type": "error",
                "id": message.get("id"),
                "error": f"Unknown message type: {message_type}"
            })
            
    except Exception as e:
        logger.error(f"Error handling message: {e}")
        await websocket.send_json({
            "type": "error",
            "id": message.get("id", "unknown"),
            "error": str(e)
        })

def run_simulation(params: SimulationParams) -> Dict:
    """Run a simulation with the given parameters"""
    # カスタム戦略関数を取得
    custom_strategy_fn = None
    if params.strategy == StrategyEnum.CUSTOM and params.custom_strategy_code:
        custom_strategy_fn = execute_custom_strategy(params.custom_strategy_code)
    
    # シミュレーションを実行
    results = run_custom_simulation(
        strategy_name=params.strategy.value,
        num_accounts=params.num_accounts,
        initial_rate=params.initial_rate,
        true_skill=params.true_skill,
        rate_change=params.rate_change,
        win_rate_slope=params.win_rate_slope,
        convergence_matches=params.convergence_matches,
        max_matches=params.max_matches,
        num_simulations=params.num_simulations,
        random_seed=params.random_seed,
        custom_strategy_fn=custom_strategy_fn
    )
    
    # シミュレーションIDを生成
    simulation_id = str(uuid.uuid4())
    
    # 結果を保存
    active_simulations[simulation_id] = {
        "simulation_id": simulation_id,
        **results
    }
    
    return active_simulations[simulation_id]

def run_comparison(params: ComparisonParams) -> Dict:
    """Run a strategy comparison with the given parameters"""
    # 比較を実行
    comparison = StrategyComparison(
        num_accounts=params.num_accounts,
        initial_rate=params.initial_rate,
        true_skill=params.true_skill,
        rate_change=params.rate_change,
        win_rate_slope=params.win_rate_slope,
        convergence_matches=params.convergence_matches,
        max_matches=params.max_matches,
        num_simulations=params.num_simulations,
        random_seed=params.random_seed
    )
    
    results = comparison.run_comparison()
    best_strategy, best_result = comparison.get_best_strategy()
    
    # 比較IDを生成
    comparison_id = str(uuid.uuid4())
    
    # 結果を保存
    active_comparisons[comparison_id] = {
        "comparison_id": comparison_id,
        "results": results,
        "best_strategy": best_strategy,
        "best_strategy_mean_rate": float(best_result["mean_highest_rate"])
    }
    
    return active_comparisons[comparison_id]

# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    websocket_connections.add(websocket)
    
    try:
        while True:
            # Receive message
            message = await websocket.receive_json()
            await handle_mcp_message(websocket, message)
            
    except WebSocketDisconnect:
        websocket_connections.remove(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        if websocket in websocket_connections:
            websocket_connections.remove(websocket)

# REST API endpoints
@app.post("/api/simulation", response_model=SimulationResponse)
async def create_simulation(params: SimulationParams):
    """Run a new simulation"""
    return run_simulation(params)

@app.post("/api/comparison", response_model=ComparisonResponse)
async def create_comparison(params: ComparisonParams):
    """Run a strategy comparison"""
    return run_comparison(params)

@app.get("/api/simulation/{simulation_id}", response_model=SimulationResponse)
async def get_simulation(simulation_id: str):
    """Get simulation results"""
    if simulation_id not in active_simulations:
        raise HTTPException(status_code=404, detail=f"Simulation {simulation_id} not found")
    return active_simulations[simulation_id]

@app.get("/api/comparison/{comparison_id}", response_model=ComparisonResponse)
async def get_comparison(comparison_id: str):
    """Get comparison results"""
    if comparison_id not in active_comparisons:
        raise HTTPException(status_code=404, detail=f"Comparison {comparison_id} not found")
    return active_comparisons[comparison_id]

@app.get("/api/simulations")
async def list_simulations():
    """List all active simulations"""
    return {
        "simulations": [
            {
                "simulation_id": sim_id,
                "strategy": sim_data["strategy"],
                "mean_highest_rate": sim_data["mean_highest_rate"]
            }
            for sim_id, sim_data in active_simulations.items()
        ]
    }

@app.get("/api/comparisons")
async def list_comparisons():
    """List all active comparisons"""
    return {
        "comparisons": [
            {
                "comparison_id": comp_id,
                "best_strategy": comp_data["best_strategy"],
                "best_strategy_mean_rate": comp_data["best_strategy_mean_rate"]
            }
            for comp_id, comp_data in active_comparisons.items()
        ]
    }

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "ok"}

# Run the server
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 12000))
    uvicorn.run(app, host="0.0.0.0", port=port)