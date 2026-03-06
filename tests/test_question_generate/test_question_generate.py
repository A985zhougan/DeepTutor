#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
WebSocket 问题生成接口测试脚本

使用方法:
    python tests/test_question_generate.py

测试场景:
    1. 自定义问题生成（带 context）
    2. 自定义问题生成（不带 context）
    3. 模仿试卷生成（需要 PDF 文件）
"""

import asyncio
import json
import sys
from pathlib import Path

try:
    import websockets
except ImportError:
    print("❌ 缺少 websockets 库，正在安装...")
    import subprocess

    subprocess.check_call([sys.executable, "-m", "pip", "install", "websockets"])
    import websockets


# 配置
BACKEND_URL = "ws://localhost:8001"


async def test_custom_with_context():
    """测试场景 1: 自定义问题生成（带 context）"""
    print("\n" + "=" * 70)
    print("📝 测试场景 1: 自定义问题生成（带 context）")
    print("=" * 70)

    uri = f"{BACKEND_URL}/api/v1/question/generate"

    try:
        async with websockets.connect(uri) as websocket:
            print("✅ WebSocket 连接成功")

            # 发送配置
            config = {
                "requirement": {
                    "knowledge_point": "深度学习基础",
                    "difficulty": "medium",
                    "question_type": "choice",
                    "context": (
                        "深度学习是机器学习的一个分支，它使用多层神经网络来学习数据的表示。"
                        "常见的深度学习模型包括卷积神经网络（CNN）用于图像处理，"
                        "循环神经网络（RNN）用于序列数据，以及Transformer用于自然语言处理。"
                        "激活函数如ReLU、Sigmoid和Tanh在神经网络中起着重要作用。"
                    ),
                },
                "count": 2,
            }

            await websocket.send(json.dumps(config))
            print(f"📤 已发送配置:")
            print(f"   知识点: {config['requirement']['knowledge_point']}")
            print(f"   难度: {config['requirement']['difficulty']}")
            print(f"   题型: {config['requirement']['question_type']}")
            print(f"   数量: {config['count']}")
            print(f"   Context: 已提供 ({len(config['requirement']['context'])} 字符)")

            # 接收消息
            question_count = 0
            while True:
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=120)
                    data = json.loads(message)

                    msg_type = data.get("type")

                    if msg_type == "task_id":
                        print(f"\n🆔 任务ID: {data['task_id']}")

                    elif msg_type == "status":
                        print(f"📊 状态: {data.get('content', 'N/A')}")

                    elif msg_type == "progress":
                        stage = data.get("stage", "unknown")
                        progress = data.get("progress", {})
                        print(f"⏳ 进度: {stage} - {progress}")

                    elif msg_type == "plan_ready":
                        plan = data.get("plan", {})
                        focuses = plan.get("focuses", [])
                        print(f"\n📋 计划生成完成:")
                        for focus in focuses:
                            print(f"   - {focus['id']}: {focus['focus']}")

                    elif msg_type == "question_update":
                        qid = data.get("question_id")
                        status = data.get("status")
                        print(f"🔄 问题 {qid}: {status}")

                    elif msg_type == "result":
                        question_count += 1
                        qid = data.get("question_id")
                        question = data.get("question", {})

                        print(f"\n✨ 问题 {qid} 生成成功:")
                        print(f"   题目: {question.get('question', 'N/A')[:80]}...")
                        print(f"   类型: {question.get('question_type', 'N/A')}")

                        if question.get("options"):
                            print(f"   选项:")
                            for key, value in question.get("options", {}).items():
                                print(f"      {key}. {value[:50]}...")

                        print(f"   答案: {question.get('correct_answer', 'N/A')}")
                        print(f"   解析: {question.get('explanation', 'N/A')[:80]}...")

                    elif msg_type == "token_stats":
                        stats = data.get("stats", {})
                        print(f"\n💰 Token 统计:")
                        print(f"   模型: {stats.get('model', 'N/A')}")
                        print(f"   调用次数: {stats.get('calls', 0)}")
                        print(f"   总 Token: {stats.get('tokens', 0)}")
                        print(f"   输入 Token: {stats.get('input_tokens', 0)}")
                        print(f"   输出 Token: {stats.get('output_tokens', 0)}")
                        print(f"   成本: ${stats.get('cost', 0):.4f}")

                    elif msg_type == "batch_summary":
                        print(f"\n📊 批次汇总:")
                        print(f"   请求: {data.get('requested', 0)}")
                        print(f"   完成: {data.get('completed', 0)}")
                        print(f"   失败: {data.get('failed', 0)}")

                    elif msg_type == "complete":
                        print(f"\n🎉 生成完成！共生成 {question_count} 个问题")
                        break

                    elif msg_type == "error":
                        print(f"\n❌ 错误: {data.get('content', 'Unknown error')}")
                        break

                    else:
                        print(f"📥 收到消息: {msg_type}")

                except asyncio.TimeoutError:
                    print("⏱️ 接收超时（120秒）")
                    break
                except websockets.exceptions.ConnectionClosed:
                    print("🔌 连接已关闭")
                    break

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()


async def test_custom_without_context():
    """测试场景 2: 自定义问题生成（不带 context）"""
    print("\n" + "=" * 70)
    print("📝 测试场景 2: 自定义问题生成（不带 context）")
    print("=" * 70)

    uri = f"{BACKEND_URL}/api/v1/question/generate"

    try:
        async with websockets.connect(uri) as websocket:
            print("✅ WebSocket 连接成功")

            # 发送配置（不带 context）
            config = {
                "requirement": {
                    "knowledge_point": "Python 列表操作",
                    "difficulty": "easy",
                    "question_type": "choice",
                },
                "count": 1,
            }

            await websocket.send(json.dumps(config))
            print(f"📤 已发送配置:")
            print(f"   知识点: {config['requirement']['knowledge_point']}")
            print(f"   难度: {config['requirement']['difficulty']}")
            print(f"   题型: {config['requirement']['question_type']}")
            print(f"   数量: {config['count']}")
            print(f"   Context: 未提供")

            # 接收消息（简化版）
            question_count = 0
            while True:
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=120)
                    data = json.loads(message)

                    msg_type = data.get("type")

                    if msg_type == "result":
                        question_count += 1
                        question = data.get("question", {})
                        print(f"\n✨ 问题生成成功:")
                        print(f"   题目: {question.get('question', 'N/A')}")
                        print(f"   答案: {question.get('correct_answer', 'N/A')}")

                    elif msg_type == "complete":
                        print(f"\n🎉 生成完成！共生成 {question_count} 个问题")
                        break

                    elif msg_type == "error":
                        print(f"\n❌ 错误: {data.get('content', 'Unknown error')}")
                        break

                except asyncio.TimeoutError:
                    print("⏱️ 接收超时（120秒）")
                    break
                except websockets.exceptions.ConnectionClosed:
                    print("🔌 连接已关闭")
                    break

    except Exception as e:
        print(f"❌ 测试失败: {e}")


async def test_mimic_mode():
    """测试场景 3: 模仿试卷生成（需要 PDF 文件）"""
    print("\n" + "=" * 70)
    print("📝 测试场景 3: 模仿试卷生成")
    print("=" * 70)
    print("⚠️  此测试需要 PDF 文件，跳过...")
    print("💡 如需测试，请准备 PDF 文件并使用以下代码:")
    print("""
    import base64
    
    # 读取 PDF 文件
    with open("exam.pdf", "rb") as f:
        pdf_data = base64.b64encode(f.read()).decode()
    
    # 发送配置
    config = {
        "mode": "upload",
        "pdf_data": pdf_data,
        "pdf_name": "exam.pdf",
        "max_questions": 5
    }
    """)


async def main():
    """主函数"""
    print("\n" + "=" * 70)
    print("🧪 DeepTutor 问题生成接口测试")
    print("=" * 70)
    print(f"后端地址: {BACKEND_URL}")
    print("=" * 70)

    # 检查后端是否运行
    print("\n🔍 检查后端服务...")
    try:
        import aiohttp

        async with aiohttp.ClientSession() as session:
            async with session.get(
                "http://localhost:8001/docs", timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                if resp.status == 200:
                    print("✅ 后端服务正常运行")
                else:
                    print(f"⚠️  后端服务响应异常: {resp.status}")
    except ImportError:
        print("⚠️  aiohttp 未安装，跳过后端检查")
    except Exception as e:
        print(f"❌ 无法连接到后端服务: {e}")
        print("💡 请确保后端服务已启动: python src/api/run_server.py")
        print("⚠️  继续尝试测试...")
        await asyncio.sleep(1)

    # 运行测试
    try:
        # 测试 1: 带 context
        await test_custom_with_context()

        # 等待一下
        await asyncio.sleep(2)

        # 测试 2: 不带 context
        await test_custom_without_context()

        # 测试 3: 模仿模式（跳过）
        await test_mimic_mode()

    except KeyboardInterrupt:
        print("\n\n⚠️  测试被用户中断")
    except Exception as e:
        print(f"\n❌ 测试过程中出错: {e}")
        import traceback

        traceback.print_exc()

    print("\n" + "=" * 70)
    print("✅ 测试完成")
    print("=" * 70)


if __name__ == "__main__":
    # 运行测试
    asyncio.run(main())
