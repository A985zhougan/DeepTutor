#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试完整的参考试卷生成题目流程（不依赖 WebSocket）

测试流程：
1. 使用智谱 OCR 解析 PDF
2. 提取参考题目
3. 生成仿题（简化版，只生成1题）
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))


async def test_full_pipeline():
    """Test the complete pipeline."""
    from src.tools.question.exam_mimic import mimic_exam_questions
    
    print("=" * 80)
    print("🧪 测试完整的参考试卷生成题目流程")
    print("=" * 80)
    print()
    
    # Use test PDF
    test_pdf = Path(__file__).parent / "2024智能计算数学基础试卷B卷.pdf"
    
    if not test_pdf.exists():
        print(f"❌ 测试 PDF 不存在: {test_pdf}")
        return 1
    
    print(f"📄 测试 PDF: {test_pdf.name}")
    print(f"📊 最大题数: 无限制（提取所有题目）")
    print()
    
    try:
        # Run the complete pipeline
        result = await mimic_exam_questions(
            pdf_path=str(test_pdf),
            paper_dir=None,
            output_dir=None,
            max_questions=None,  # Extract all questions
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
            
            # Show generated question preview
            generated = result.get('generated_questions', [])
            if generated:
                print()
                print("📝 生成的题目预览:")
                q = generated[0].get('generated_question', {})
                question_text = q.get('question', '')
                preview = question_text[:200] + "..." if len(question_text) > 200 else question_text
                print(f"   {preview}")
            
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
    return asyncio.run(test_full_pipeline())


if __name__ == "__main__":
    sys.exit(main())
