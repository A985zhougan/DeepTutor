#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试题目提取功能
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from src.tools.question.question_extractor import extract_questions_from_paper


def main():
    """Test question extraction."""
    print("=" * 80)
    print("🧪 测试题目提取功能")
    print("=" * 80)
    print()
    
    # Use the latest parsed paper
    paper_dir = project_root / "data" / "user" / "question" / "mimic_papers" / "mimic_20260309_131754_2024智能计算数学基础试卷B卷"
    
    if not paper_dir.exists():
        print(f"❌ 试卷目录不存在: {paper_dir}")
        return 1
    
    print(f"📁 试卷目录: {paper_dir.name}")
    print(f"📊 提取限制: 无（提取所有题目）")
    print()
    
    # Extract questions
    success = extract_questions_from_paper(
        paper_dir=str(paper_dir),
        output_dir=None,
        max_questions=None,  # Extract all questions
    )
    
    if success:
        print()
        print("=" * 80)
        print("✅ 提取成功!")
        print("=" * 80)
        
        # Check the result
        import json
        json_files = list(paper_dir.glob("*_questions.json"))
        if json_files:
            latest_json = max(json_files, key=lambda p: p.stat().st_mtime)
            with open(latest_json, encoding="utf-8") as f:
                data = json.load(f)
            
            print(f"📄 结果文件: {latest_json.name}")
            print(f"📊 提取题目数: {data.get('total_questions', 0)}")
            print()
            print("前5道题预览:")
            for i, q in enumerate(data.get('questions', [])[:5], 1):
                text = q.get('question_text', '')
                preview = text[:80] + "..." if len(text) > 80 else text
                print(f"  {i}. {preview}")
        
        return 0
    else:
        print()
        print("=" * 80)
        print("❌ 提取失败!")
        print("=" * 80)
        return 1


if __name__ == "__main__":
    sys.exit(main())
