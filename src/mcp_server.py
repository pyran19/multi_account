"""Multi-account Pokemon battle simulator MCP server."""

import asyncio
import json
import sys
from typing import Any, Dict, List, Optional

from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import (
    Resource,
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
    LoggingLevel
)

from src.core.parameters import Parameters
from src.core.state import State
from src.cli import get_parameters, get_initial_state, perform_dp_calculation, perform_simulation

# MCPサーバーのインスタンスを作成
server = Server("multi-account-simulator")

@server.list_tools()
async def handle_list_tools() -> List[Tool]:
    """利用可能なツールのリストを返す。"""
    return [
        Tool(
            name="calculate_dp",
            description="動的プログラミングを使って最適戦略を計算します",
            inputSchema={
                "type": "object",
                "properties": {
                    "n_matches": {
                        "type": "integer",
                        "description": "試合数",
                        "minimum": 0
                    },
                    "accounts": {
                        "type": "integer",
                        "description": "アカウント数（デフォルト: 2）",
                        "minimum": 1,
                        "default": 2
                    },
                    "initial_ratings": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "初期レーティング（省略時は全て1500）"
                    },
                    "rating_step": {
                        "type": "number",
                        "description": "レーティングステップ（デフォルト: 16）",
                        "default": 16
                    },
                    "k_coeff": {
                        "type": "number",
                        "description": "Kファクター係数（デフォルト: log(10)/1600）"
                    },
                    "mu": {
                        "type": "number",
                        "description": "平均レーティング（デフォルト: 1500）",
                        "default": 1500.0
                    }
                },
                "required": ["n_matches"]
            }
        ),
        Tool(
            name="run_simulation",
            description="複数のポリシーでシミュレーションを実行します",
            inputSchema={
                "type": "object",
                "properties": {
                    "n_matches": {
                        "type": "integer",
                        "description": "試合数",
                        "minimum": 0
                    },
                    "accounts": {
                        "type": "integer",
                        "description": "アカウント数（デフォルト: 2）",
                        "minimum": 1,
                        "default": 2
                    },
                    "initial_ratings": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "初期レーティング（省略時は全て1500）"
                    },
                    "episodes": {
                        "type": "integer",
                        "description": "エピソード数（デフォルト: 1000）",
                        "minimum": 1,
                        "default": 1000
                    },
                    "policy": {
                        "type": "string",
                        "description": "ポリシー名（optimal, random, fixed, greedy, all）",
                        "default": "all"
                    },
                    "fixed_idx": {
                        "type": "integer",
                        "description": "固定ポリシーのアカウントインデックス",
                        "minimum": 0,
                        "default": 0
                    },
                    "rating_step": {
                        "type": "number",
                        "description": "レーティングステップ（デフォルト: 16）",
                        "default": 16
                    },
                    "k_coeff": {
                        "type": "number",
                        "description": "Kファクター係数（デフォルト: log(10)/1600）"
                    },
                    "mu": {
                        "type": "number",
                        "description": "平均レーティング（デフォルト: 1500）",
                        "default": 1500.0
                    }
                },
                "required": ["n_matches"]
            }
        ),

    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """ツールの実行を処理する。"""
    try:
        if name == "calculate_dp":
            return await handle_calculate_dp(arguments)
        elif name == "run_simulation":
            return await handle_run_simulation(arguments)

        else:
            raise ValueError(f"Unknown tool: {name}")
    except Exception as e:
        return [TextContent(type="text", text=f"エラーが発生しました: {str(e)}")]

async def handle_calculate_dp(arguments: Dict[str, Any]) -> List[TextContent]:
    """動的プログラミング計算を実行する。"""
    n_matches = arguments["n_matches"]
    num_accounts = arguments.get("accounts", 2)
    initial_ratings_float = arguments.get("initial_ratings")
    
    # パラメータの設定
    import math
    param_data = {
        "rating_step": arguments.get("rating_step", 16),
        "k_coeff": arguments.get("k_coeff", math.log(10) / 1600),
        "mu": arguments.get("mu", 1500.0)
    }
    
    core_params = get_parameters(param_data)
    initial_state = get_initial_state(num_accounts, initial_ratings_float, core_params)
    
    results = perform_dp_calculation(n_matches, initial_state, core_params, num_accounts)
    
    # 結果をフォーマット
    result_text = f"""動的プログラミング計算結果:

試合数: {n_matches}
アカウント数: {num_accounts}
初期状態: {list(initial_state.ratings)}

期待値: {results['expected_value_int']}
最適行動: アカウント {results['best_action_account_index']} を選択
"""
    
    return [TextContent(type="text", text=result_text)]

async def handle_run_simulation(arguments: Dict[str, Any]) -> List[TextContent]:
    """シミュレーションを実行する。"""
    n_matches = arguments["n_matches"]
    num_accounts = arguments.get("accounts", 2)
    initial_ratings_float = arguments.get("initial_ratings")
    episodes = arguments.get("episodes", 1000)
    policy_name = arguments.get("policy", "all")
    fixed_idx = arguments.get("fixed_idx", 0)
    
    # パラメータの設定
    import math
    param_data = {
        "rating_step": arguments.get("rating_step", 16),
        "k_coeff": arguments.get("k_coeff", math.log(10) / 1600),
        "mu": arguments.get("mu", 1500.0)
    }
    
    core_params = get_parameters(param_data)
    initial_state = get_initial_state(num_accounts, initial_ratings_float, core_params)
    
    results = perform_simulation(
        n_matches, initial_state, core_params, num_accounts,
        episodes, policy_name, fixed_idx, False, "."  # visualize=False
    )
    
    # 結果をフォーマット
    result_text = f"""シミュレーション結果:

試合数: {n_matches}
アカウント数: {num_accounts}
エピソード数: {episodes}
ポリシー: {policy_name}
初期状態: {list(initial_state.ratings)}

"""
    
    if 'simulation_results' in results:
        for result in results['simulation_results']:
            result_text += f"\n{result['policy_name']}:\n"
            result_text += f"  平均最終レーティング: {result['mean_final_rating']:.2f}\n"
            result_text += f"  標準偏差: {result['std_final_rating']:.2f}\n"
    
    return [TextContent(type="text", text=result_text)]



async def main():
    """MCPサーバーのメインエントリーポイント。"""
    try:
        # 標準入出力を使ってサーバーを実行
        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="multi-account-simulator",
                    server_version="0.1.0",
                    capabilities={},
                ),
            )
    except Exception as e:
        import traceback
        print(f"MCPサーバーエラー: {e}", file=sys.stderr)
        print("詳細なエラー情報:", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
