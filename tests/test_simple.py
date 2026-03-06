#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
简单的 WebSocket 测试脚本 - 测试单个问题生成
"""

import asyncio
import json
import sys

try:
    import websockets
except ImportError:
    print("正在安装 websockets...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "websockets"])
    import websockets


async def test():
    uri = "ws://localhost:8001/api/v1/question/generate"
    
    print("=" * 70)
    print("🧪 简单测试: 生成 1 个问题")
    print("=" * 70)
    
    try:
        print(f"\n📡 正在连接到 {uri}...")
        async with websockets.connect(uri) as websocket:
            print("✅ 连接成功！\n")
            
            # 配置
            config = {
                "requirement": {
                    "knowledge_point": "Python 基础",
                    "difficulty": "easy",
                    "question_type": "choice",
                    "context": "Python 是一种高级编程语言，具有简洁的语法和强大的功能。"
                },
                "count": 1
            }
            
            print("📤 发送配置:")
            print(json.dumps(config, indent=2, ensure_ascii=False))
            print()
            
            await websocket.send(json.dumps(config))
            
            # 接收所有消息
            message_count = 0
            while True:
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=60)
                    message_count += 1
                    data = json.loads(message)
                    
                    print(f"📥 消息 #{message_count}: {data.get('type', 'unknown')}")
                    
                    # 显示重要消息的详细内容
                    if data.get('type') == 'result':
                        print("\n" + "=" * 70)
                        print("✨ 生成的问题:")
                        print("=" * 70)
                        question = data.get('question', {})
                        print(f"题目: {question.get('question', 'N/A')}")
                        if question.get('options'):
                            print("\n选项:")
                            for k, v in question.get('options', {}).items():
                                print(f"  {k}. {v}")
                        print(f"\n答案: {question.get('correct_answer', 'N/A')}")
                        print(f"\n解析: {question.get('explanation', 'N/A')}")
                        print("=" * 70)
                    
                    elif data.get('type') == 'error':
                        print(f"\n❌ 错误: {data.get('content', 'Unknown')}")
                        break
                    
                    elif data.get('type') == 'complete':
                        print(f"\n🎉 完成！共收到 {message_count} 条消息")
                        break
                
                except asyncio.TimeoutError:
                    print(f"\n⏱️ 超时（60秒），共收到 {message_count} 条消息")
                    break
                except websockets.exceptions.ConnectionClosed:
                    print(f"\n🔌 连接关闭，共收到 {message_count} 条消息")
                    break
    
    except ConnectionRefusedError:
        print("❌ 连接被拒绝！")
        print("💡 请确保后端服务正在运行:")
        print("   python src/api/run_server.py")
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("DeepTutor WebSocket 测试")
    print("=" * 70)
    
    try:
        asyncio.run(test())
    except KeyboardInterrupt:
        print("\n\n⚠️  测试被中断")
    
    print("\n" + "=" * 70)
    print("测试结束")
    print("=" * 70 + "\n")
