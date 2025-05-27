#!/usr/bin/env python3
"""MCPサーバーのテストスクリプト"""

import asyncio
import json
import subprocess
import sys
import os

async def test_mcp_server():
    """MCPサーバーをテストする"""
    
    # 環境変数を設定
    env = os.environ.copy()
    env['PYTHONPATH'] = os.getcwd()
    
    # MCPサーバーを起動
    process = await asyncio.create_subprocess_exec(
        'uv', 'run', 'src/mcp_server.py',
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env
    )
    
    try:
        # 初期化リクエスト
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "test-client",
                    "version": "1.0.0"
                }
            }
        }
        
        # リクエストを送信
        request_data = json.dumps(init_request) + '\n'
        process.stdin.write(request_data.encode())
        await process.stdin.drain()
        
        # レスポンスを読み取り（タイムアウト付き）
        try:
            response_data = await asyncio.wait_for(
                process.stdout.readline(), 
                timeout=5.0
            )
            
            if response_data:
                response = json.loads(response_data.decode().strip())
                print("初期化レスポンス:", json.dumps(response, indent=2, ensure_ascii=False))
                
                # ツールリストを取得
                tools_request = {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/list",
                    "params": {}
                }
                
                request_data = json.dumps(tools_request) + '\n'
                process.stdin.write(request_data.encode())
                await process.stdin.drain()
                
                tools_response_data = await asyncio.wait_for(
                    process.stdout.readline(),
                    timeout=5.0
                )
                
                if tools_response_data:
                    tools_response = json.loads(tools_response_data.decode().strip())
                    print("ツールリスト:", json.dumps(tools_response, indent=2, ensure_ascii=False))
                    
                    return True
            else:
                print("レスポンスが空です")
                # stderrを確認
                stderr_data = await process.stderr.read()
                if stderr_data:
                    print("サーバーエラー:", stderr_data.decode())
                return False
                
        except asyncio.TimeoutError:
            print("タイムアウト: サーバーからのレスポンスがありません")
            # stderrを確認
            stderr_data = await process.stderr.read()
            if stderr_data:
                print("サーバーエラー:", stderr_data.decode())
            return False
            
    except Exception as e:
        print(f"テスト中にエラーが発生しました: {e}")
        return False
        
    finally:
        # プロセスを終了
        process.terminate()
        try:
            await asyncio.wait_for(process.wait(), timeout=2.0)
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()

if __name__ == "__main__":
    result = asyncio.run(test_mcp_server())
    if result:
        print("✅ MCPサーバーのテストが成功しました！")
    else:
        print("❌ MCPサーバーのテストが失敗しました")
        sys.exit(1) 