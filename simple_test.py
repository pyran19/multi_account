#!/usr/bin/env python3
"""簡単なMCPサーバーテスト"""

import os
import sys

# PYTHONPATHを設定
sys.path.insert(0, os.getcwd())

try:
    from src.mcp_server import server, handle_list_tools
    print("✅ MCPサーバーモジュールのインポートが成功しました")
    
    # ツールリストを取得してみる
    import asyncio
    
    async def test_tools():
        tools = await handle_list_tools()
        print(f"✅ ツール数: {len(tools)}")
        for tool in tools:
            print(f"  - {tool.name}: {tool.description}")
        return True
    
    result = asyncio.run(test_tools())
    if result:
        print("✅ ツールリストの取得が成功しました")
    
except Exception as e:
    import traceback
    print(f"❌ エラーが発生しました: {e}")
    print("詳細:")
    traceback.print_exc()
    sys.exit(1) 