#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
完整流程测试：PDF解析 → 题目提取 → 仿题生成
使用智谱 OCR
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))


async def test_complete_flow():
    """Test complete flow from PDF to generated questions."""
    from src.tools.question.exam_mimic import mimic_exam_questions
    
    print("=" * 80)
    print("🧪 完整流程测试：智谱 OCR + 题目提取 + 仿题生成")
    print("=" * 80)
    print()
    
    # Use math test PDF
    test_pdf = Path(__file__).parent / "2024智能计算数学基础试卷B卷.pdf"
    
    if not test_pdf.exists():
        print(f"❌ 测试 PDF 不存在: {test_pdf}")
        return 1
    
    print(f"📄 测试 PDF: {test_pdf.name}")
    print(f"📊 提取题目数: 全部")
    print(f"📊 生成仿题数: 全部")
    print(f"⚡ 并发数: 50")
    print()
    print("流程:")
    print("  1. 使用智谱 OCR 解析 PDF")
    print("  2. 提取所有参考题目")
    print("  3. 并发生成所有仿题（最多50个并发）")
    print()
    print("=" * 80)
    print()
    
    try:
        result = await mimic_exam_questions(
            pdf_path=str(test_pdf),
            paper_dir=None,
            output_dir=None,
            max_questions=None,  # Generate ALL questions
            ws_callback=None,
        )
        
        print()
        print("=" * 80)
        print("📊 测试结果")
        print("=" * 80)
        
        if result.get("success"):
            print("✅ 测试成功!")
            print(f"   参考题目数: {result.get('total_reference_questions', 0)}")
            print(f"   生成成功: {len(result.get('generated_questions', []))}")
            print(f"   生成失败: {len(result.get('failed_questions', []))}")
            print(f"   输出文件: {result.get('output_file', 'N/A')}")
            
            # Show generated questions
            generated = result.get('generated_questions', [])
            if generated:
                print()
                print("📝 生成的仿题预览:")
                for i, item in enumerate(generated, 1):
                    ref_num = item.get('reference_question_number', '?')
                    q = item.get('generated_question', {})
                    question_text = q.get('question', '')
                    preview = question_text[:100] + "..." if len(question_text) > 100 else question_text
                    print(f"   {i}. [参考题 {ref_num}] {preview}")
            
            return 0
        else:
            print("❌ 测试失败!")
            print(f"   错误: {result.get('error', 'Unknown error')}")
            return 1
            
    except Exception as e:
        print()
        print("=" * 80)
        print("❌ 测试异常!")
        print("=" * 80)
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()
        return 1


def main():
    """Main entry point."""
    return asyncio.run(test_complete_flow())


if __name__ == "__main__":
    sys.exit(main())
