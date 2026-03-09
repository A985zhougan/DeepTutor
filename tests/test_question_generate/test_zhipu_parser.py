#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试智谱 OCR PDF 解析器

使用示例：
    python tests/test_question_generate/test_zhipu_parser.py
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from src.tools.question.pdf_parser_zhipu import parse_pdf_with_zhipu


def main():
    """Test Zhipu OCR parser with a sample PDF."""
    print("=" * 80)
    print("Testing Zhipu OCR PDF Parser")
    print("=" * 80)
    print()

    # Use the test PDF
    test_pdf = Path(__file__).parent / "2024智能计算数学基础试卷B卷.pdf"

    if not test_pdf.exists():
        print(f"[ERROR] Test PDF not found: {test_pdf}")
        print("Please ensure the test PDF exists in the test directory.")
        return 1

    print(f"PDF: {test_pdf.name}")
    print()

    # Parse the PDF
    success = parse_pdf_with_zhipu(
        pdf_path=str(test_pdf),
        output_base_dir=None,  # Use default output directory
    )

    if success:
        print()
        print("=" * 80)
        print("[OK] Test passed!")
        print("=" * 80)
        return 0
    else:
        print()
        print("=" * 80)
        print("[ERROR] Test failed!")
        print("=" * 80)
        return 1


if __name__ == "__main__":
    sys.exit(main())
