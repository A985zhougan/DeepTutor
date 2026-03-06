#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
WebSocket 测试脚本：试卷仿题生成（/api/v1/question/mimic）

使用示例：
    # 1) 使用已解析试卷目录（推荐）
    python tests/test_question_generate/test_mimic_generation.py --mode parsed --paper-path mimic_20260305_xxx --max-questions 2

    # 2) 直接上传 PDF
    python tests/test_question_generate/test_mimic_generation.py --mode upload --pdf ./data/demo_exam.pdf --max-questions 2

可选参数：
    --backend ws://localhost:8001
    --timeout 300
    --show-log
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import json
from pathlib import Path
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PARSED_BASE = PROJECT_ROOT / "data" / "user" / "question" / "mimic_papers"

try:
    import websockets
except ImportError:
    print("[ERROR] 缺少 websockets 依赖，请先安装：pip install websockets")
    raise


def build_payload(args: argparse.Namespace) -> dict[str, Any]:
    """Build WebSocket payload for mimic API."""
    payload: dict[str, Any] = {"mode": args.mode, "max_questions": args.max_questions}

    if args.mode == "parsed":
        paper_path = args.paper_path
        if not paper_path:
            paper_path = pick_latest_paper_path(Path(args.paper_base_dir))
            print(f"[INFO] 未提供 --paper-path，自动使用最新目录: {paper_path}")
        payload["paper_path"] = paper_path
        return payload

    if not args.pdf:
        raise ValueError("upload 模式必须提供 --pdf")

    pdf_path = Path(args.pdf).resolve()
    if not pdf_path.exists() or not pdf_path.is_file():
        raise FileNotFoundError(f"PDF 文件不存在: {pdf_path}")
    if pdf_path.suffix.lower() != ".pdf":
        raise ValueError(f"文件不是 PDF: {pdf_path}")

    pdf_bytes = pdf_path.read_bytes()
    payload["pdf_name"] = pdf_path.name
    payload["pdf_data"] = base64.b64encode(pdf_bytes).decode("utf-8")
    return payload


def pick_latest_paper_path(base_dir: Path) -> str:
    """Pick the latest valid parsed paper path (must contain auto/)."""
    if not base_dir.exists() or not base_dir.is_dir():
        raise FileNotFoundError(
            f"parsed 目录不存在: {base_dir}. 请先运行 upload 模式解析一份试卷，或手动传 --paper-path"
        )

    candidates = []
    for item in base_dir.rglob("*"):
        if item.is_dir() and (item / "auto").exists():
            relative_path = item.relative_to(base_dir)
            candidates.append((item.stat().st_mtime, relative_path))

    if not candidates:
        raise ValueError(
            f"parsed 目录下未找到有效试卷(缺少 auto/): {base_dir}. "
            "请先运行 upload 模式解析一份试卷，或手动传 --paper-path"
        )

    candidates.sort(key=lambda item: item[0], reverse=True)
    return str(candidates[0][1]).replace("\\", "/")


def safe_print(text: str) -> None:
    """Print text safely on non-UTF8 consoles (e.g., Windows GBK)."""
    try:
        print(text)
    except UnicodeEncodeError:
        encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
        fallback = text.encode(encoding, errors="replace").decode(encoding, errors="replace")
        print(fallback)


def print_event(message: dict[str, Any], show_log: bool) -> None:
    """Pretty-print one server event."""
    msg_type = message.get("type", "unknown")

    if msg_type == "log":
        if show_log:
            content = message.get("content", "")
            if content:
                safe_print(f"[LOG] {content}")
        return

    if msg_type == "status":
        stage = message.get("stage", "-")
        content = message.get("content", "")
        safe_print(f"[STATUS] [{stage}] {content}")
        return

    if msg_type == "progress":
        stage = message.get("stage", "-")
        status = message.get("status", "-")
        current = message.get("current")
        total = message.get("total")
        msg = message.get("message", "")
        if current is not None and total is not None:
            safe_print(f"[PROGRESS] [{stage}] {status} ({current}/{total}) {msg}")
        else:
            safe_print(f"[PROGRESS] [{stage}] {status} {msg}")
        return

    if msg_type == "question_update":
        question_id = message.get("question_id", "-")
        status = message.get("status", "-")
        error = message.get("error")
        if error:
            safe_print(f"[ERROR] 题目 {question_id}: {status} - {error}")
        else:
            safe_print(f"[UPDATE] 题目 {question_id}: {status}")
        return

    if msg_type == "result":
        question_id = message.get("question_id", "-")
        question = message.get("question", {})
        question_text = ""
        if isinstance(question, dict):
            question_text = str(question.get("question", ""))
        preview = (question_text[:100] + "...") if len(question_text) > 100 else question_text
        safe_print(f"[OK] 题目 {question_id} 生成成功: {preview}")
        return

    if msg_type == "summary":
        safe_print(
            "[SUMMARY] "
            f"参考题={message.get('total_reference', 0)}, "
            f"成功={message.get('successful', 0)}, "
            f"失败={message.get('failed', 0)}"
        )
        output_file = message.get("output_file")
        if output_file:
            safe_print(f"[SAVE] 输出文件: {output_file}")
        return

    if msg_type == "error":
        safe_print(f"[ERROR] 错误: {message.get('content', 'Unknown error')}")
        return

    if msg_type == "complete":
        safe_print("[DONE] 任务完成")
        return

    safe_print(f"[EVENT] 未知消息: {message}")


async def run_test(args: argparse.Namespace) -> int:
    """Connect to WebSocket and stream mimic events."""
    uri = f"{args.backend.rstrip('/')}/api/v1/question/mimic"

    try:
        payload = build_payload(args)
    except Exception as exc:
        print(f"[ERROR] 参数错误: {exc}")
        return 2

    print("=" * 72)
    print("DeepTutor 试卷仿题生成测试")
    print("=" * 72)
    print(f"WebSocket: {uri}")
    print(f"模式: {args.mode}")
    print(f"最大题数: {args.max_questions}")
    if args.mode == "parsed":
        print(f"paper_path: {payload['paper_path']}")
    else:
        print(f"pdf_name: {payload['pdf_name']}")
    print("=" * 72)

    try:
        async with websockets.connect(
            uri,
            max_size=10 * 1024 * 1024,
            ping_interval=None,
            ping_timeout=None,
        ) as ws:
            await ws.send(json.dumps(payload, ensure_ascii=False))
            print("[SEND] 已发送请求，等待服务端响应...\n")

            while True:
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=args.timeout)
                except asyncio.TimeoutError:
                    print(f"[TIMEOUT] 超时：{args.timeout} 秒内未收到消息")
                    return 1
                except websockets.exceptions.ConnectionClosed as exc:
                    print(f"[CLOSED] 连接关闭 (code={exc.code}, reason={exc.reason})")
                    return 1

                try:
                    data = json.loads(raw)
                except json.JSONDecodeError:
                    print(f"[WARN] 非 JSON 消息: {raw}")
                    continue

                print_event(data, show_log=args.show_log)

                msg_type = data.get("type")
                if msg_type == "complete":
                    return 0
                if msg_type == "error":
                    return 1

    except OSError as exc:
        print(f"[ERROR] 无法连接到后端: {exc}")
        print("[TIP] 请先启动后端: python src/api/run_server.py")
        return 1
    except Exception as exc:
        print(f"[ERROR] 测试失败: {exc}")
        return 1


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description="测试试卷仿题 WebSocket 接口")
    parser.add_argument(
        "--mode",
        choices=["parsed", "upload"],
        default="parsed",
        help="测试模式: parsed(使用已解析目录) / upload(上传 PDF)",
    )
    parser.add_argument(
        "--paper-path",
        type=str,
        default=None,
        help="parsed 模式下的试卷目录名（不填则自动选最新目录）",
    )
    parser.add_argument(
        "--paper-base-dir",
        type=str,
        default=str(DEFAULT_PARSED_BASE),
        help="自动选择 paper_path 时扫描的目录",
    )
    parser.add_argument("--pdf", type=str, default=None, help="upload 模式下的 PDF 文件路径")
    parser.add_argument("--max-questions", type=int, default=2, help="最多生成题目数量（默认: 2）")
    parser.add_argument("--backend", type=str, default="ws://localhost:8001", help="后端 WS 地址")
    parser.add_argument("--timeout", type=int, default=300, help="消息等待超时秒数（默认: 300）")
    parser.add_argument("--show-log", action="store_true", help="显示服务端 log 消息")
    return parser.parse_args()


def main() -> int:
    """CLI entrypoint."""
    args = parse_args()
    return asyncio.run(run_test(args))


if __name__ == "__main__":
    raise SystemExit(main())
