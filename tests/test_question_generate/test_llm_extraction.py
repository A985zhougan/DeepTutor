#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
直接测试 LLM 题目提取，查看返回结果
"""

import asyncio
import json
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))


async def test_llm_extraction():
    """Test LLM extraction directly."""
    from src.services.llm import complete as llm_complete
    from src.services.llm.config import get_llm_config
    
    print("=" * 80)
    print("🧪 测试 LLM 题目提取")
    print("=" * 80)
    print()
    
    # Read the markdown file
    md_file = project_root / "data" / "user" / "question" / "mimic_papers" / "mimic_20260309_131754_2024智能计算数学基础试卷B卷" / "auto" / "2024智能计算数学基础试卷B卷.md"
    
    if not md_file.exists():
        print(f"❌ Markdown 文件不存在: {md_file}")
        return 1
    
    with open(md_file, encoding="utf-8") as f:
        markdown_content = f.read()
    
    print(f"📄 Markdown 文件: {md_file.name}")
    print(f"📊 内容长度: {len(markdown_content)} 字符")
    print()
    
    # Simple prompt to extract first 5 questions
    system_prompt = """You are a professional exam paper analysis assistant.
Extract the first 5 questions from the exam paper.

Return in JSON format:
{
    "questions": [
        {
            "question_number": "1",
            "question_text": "Complete question text..."
        }
    ]
}"""
    
    user_prompt = f"""Exam paper content:

{markdown_content[:3000]}

Extract the first 5 questions and return in JSON format."""
    
    print("🤖 调用 LLM...")
    print(f"📝 输入长度: {len(user_prompt)} 字符")
    print()
    
    try:
        llm_config = get_llm_config()
        
        result = await llm_complete(
            prompt=user_prompt,
            system_prompt=system_prompt,
            model=llm_config.model,
            api_key=llm_config.api_key,
            base_url=llm_config.base_url,
            temperature=0.1,
            max_tokens=2000,
        )
        
        print("✅ LLM 返回成功!")
        print()
        print("=" * 80)
        print("返回内容:")
        print("=" * 80)
        print(result[:1000])
        print()
        
        # Try to parse JSON
        try:
            # Remove markdown code blocks if present
            if "```json" in result:
                result = result.split("```json")[1].split("```")[0].strip()
            elif "```" in result:
                result = result.split("```")[1].split("```")[0].strip()
            
            data = json.loads(result)
            questions = data.get("questions", [])
            
            print("=" * 80)
            print(f"📊 解析结果: 提取了 {len(questions)} 道题")
            print("=" * 80)
            
            for i, q in enumerate(questions[:5], 1):
                num = q.get("question_number", "?")
                text = q.get("question_text", "")
                preview = text[:80] + "..." if len(text) > 80 else text
                print(f"{i}. [题号 {num}] {preview}")
            
            return 0
            
        except json.JSONDecodeError as e:
            print(f"❌ JSON 解析失败: {e}")
            return 1
        
    except Exception as e:
        print(f"❌ LLM 调用失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


def main():
    """Main entry point."""
    return asyncio.run(test_llm_extraction())


if __name__ == "__main__":
    sys.exit(main())
