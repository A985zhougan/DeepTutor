#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
智谱 GLM-OCR 模型测试脚本

使用智谱的 GLM-OCR 大模型识别 PDF 文档并提取内容

API 文档: https://docs.bigmodel.cn/cn/guide/models/vlm/glm-ocr
"""

import asyncio
import base64
import json
import sys
from datetime import datetime
from pathlib import Path

import requests


# 配置
ZHIPU_API_KEY = "b4589a0e5c19490fbe0e6bf434fc8700.WNVezmwy88jpTmX6"
ZHIPU_API_URL = "https://open.bigmodel.cn/api/paas/v4/layout_parsing"
MODEL = "glm-ocr"

# PDF 文件路径
PDF_PATH = Path(__file__).parent / "attention is all your need.pdf"
OUTPUT_DIR = Path(__file__).parent / "zhipu_ocr_output"


def call_zhipu_ocr(
    file_path: Path,
    return_crop_images: bool = True,
    need_layout_visualization: bool = True,
    start_page_id: int = None,
    end_page_id: int = None,
) -> dict:
    """
    调用智谱 GLM-OCR API 进行文档解析

    Args:
        file_path: PDF 或图片文件路径
        return_crop_images: 是否返回截图信息
        need_layout_visualization: 是否返回详细布局图片结果
        start_page_id: 开始解析的页码（PDF）
        end_page_id: 结束解析的页码（PDF）

    Returns:
        API 响应结果
    """
    print(f"\n📄 准备解析文件: {file_path.name}")
    
    # 检查文件是否存在
    if not file_path.exists():
        raise FileNotFoundError(f"文件不存在: {file_path}")
    
    # 检查文件大小
    file_size_mb = file_path.stat().st_size / (1024 * 1024)
    print(f"📊 文件大小: {file_size_mb:.2f} MB")
    
    if file_path.suffix.lower() == '.pdf' and file_size_mb > 50:
        raise ValueError(f"PDF 文件过大: {file_size_mb:.2f} MB (最大 50MB)")
    elif file_path.suffix.lower() in ['.jpg', '.jpeg', '.png'] and file_size_mb > 10:
        raise ValueError(f"图片文件过大: {file_size_mb:.2f} MB (最大 10MB)")
    
    # 读取文件并转换为 base64
    print("🔄 读取文件并编码为 base64...")
    with open(file_path, "rb") as f:
        file_data = base64.b64encode(f.read()).decode("utf-8")
    
    # 构建请求数据
    request_data = {
        "model": MODEL,
        "file": f"data:application/pdf;base64,{file_data}",
        "return_crop_images": return_crop_images,
        "need_layout_visualization": need_layout_visualization,
    }
    
    # 添加页码范围（如果指定）
    if start_page_id is not None:
        request_data["start_page_id"] = start_page_id
    if end_page_id is not None:
        request_data["end_page_id"] = end_page_id
    
    # 设置请求头
    headers = {
        "Authorization": f"Bearer {ZHIPU_API_KEY}",
        "Content-Type": "application/json",
    }
    
    print(f"📤 发送请求到智谱 API...")
    print(f"   模型: {MODEL}")
    print(f"   返回截图: {return_crop_images}")
    print(f"   布局可视化: {need_layout_visualization}")
    if start_page_id or end_page_id:
        print(f"   页码范围: {start_page_id or 1} - {end_page_id or '最后一页'}")
    
    # 发送请求
    try:
        response = requests.post(
            ZHIPU_API_URL,
            headers=headers,
            json=request_data,
            timeout=300,  # 5分钟超时
        )
        response.raise_for_status()
        
        result = response.json()
        print(f"✅ 请求成功!")
        
        return result
        
    except requests.exceptions.RequestException as e:
        print(f"❌ 请求失败: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"响应内容: {e.response.text}")
        raise


def save_results(result: dict, output_dir: Path):
    """
    保存解析结果到文件（只保存 Markdown 和图片）

    Args:
        result: API 响应结果
        output_dir: 输出目录
    """
    # 创建输出目录
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 1. 提取布局详情中的图片 URL
    layout_details = result.get("layout_details", [])
    crop_images = []
    
    for page_num, page_elements in enumerate(layout_details, 1):
        for element in page_elements:
            if element.get("label") == "image":
                url = element.get("content", "")
                if url.startswith("http"):
                    crop_images.append({
                        "url": url,
                        "page": page_num,
                        "index": element.get("index", 0),
                    })
    
    # 2. 下载图片到 images 目录
    images_dir = output_dir / "images"
    url_mapping = {}
    
    if crop_images:
        print(f"\n🖼️  下载文档图片 ({len(crop_images)} 张)...")
        images_dir.mkdir(parents=True, exist_ok=True)
        
        for img_info in crop_images:
            url = img_info["url"]
            page = img_info["page"]
            idx = img_info["index"]
            
            filename = f"page_{page}_image_{idx}.png"
            img_file = images_dir / filename
            
            try:
                img_response = requests.get(url, timeout=30)
                img_response.raise_for_status()
                
                with open(img_file, "wb") as f:
                    f.write(img_response.content)
                
                print(f"   ✓ 第 {page} 页图片 {idx}: {filename}")
                
                # 记录 URL 映射（相对路径）
                url_mapping[url] = f"images/{filename}"
                
            except Exception as e:
                print(f"   ✗ 下载失败: {e}")
    
    # 3. 保存 Markdown 并替换图片链接为本地路径
    md_results = result.get("md_results", "")
    if md_results:
        # 替换图片 URL 为本地路径
        for original_url, local_path in url_mapping.items():
            md_results = md_results.replace(original_url, local_path)
        
        md_file = output_dir / f"document_{timestamp}.md"
        with open(md_file, "w", encoding="utf-8") as f:
            f.write(md_results)
        
        print(f"\n📝 Markdown 文档已保存: {md_file.name}")
        print(f"   内容长度: {len(md_results)} 字符")
        print(f"   图片引用: {len(url_mapping)} 个")
    
    # 4. 显示 Token 使用情况
    usage = result.get("usage", {})
    if usage:
        print(f"\n💰 Token 使用统计:")
        print(f"   输入 Token: {usage.get('prompt_tokens', 0)}")
        print(f"   输出 Token: {usage.get('completion_tokens', 0)}")
        print(f"   总 Token: {usage.get('total_tokens', 0)}")
    
    print(f"\n✅ 结果已保存到: {output_dir}")
    print(f"   📄 Markdown: {md_file.name if md_results else '无'}")
    print(f"   🖼️  图片目录: images/ ({len(url_mapping)} 张)")


def main():
    """主函数"""
    print("=" * 70)
    print("🤖 智谱 GLM-OCR 文档解析测试")
    print("=" * 70)
    print(f"API 密钥: {ZHIPU_API_KEY[:20]}...")
    print(f"模型: {MODEL}")
    print(f"PDF 文件: {PDF_PATH.name}")
    print(f"输出目录: {OUTPUT_DIR}")
    print("=" * 70)
    
    # 检查 PDF 文件是否存在
    if not PDF_PATH.exists():
        print(f"\n❌ 错误: PDF 文件不存在")
        print(f"   期望路径: {PDF_PATH}")
        print(f"\n💡 请将 'Attention is All You Need' 论文 PDF 放到:")
        print(f"   {PDF_PATH.parent}")
        return
    
    try:
        # 调用 OCR API（解析整篇文档）
        print("\n🚀 开始解析整篇文档...")
        result = call_zhipu_ocr(
            file_path=PDF_PATH,
            return_crop_images=True,
            need_layout_visualization=True,
            start_page_id=None,  # 从第一页开始
            end_page_id=None,    # 解析到最后一页
        )
        
        # 保存结果
        save_results(result, OUTPUT_DIR)
        
        print("\n" + "=" * 70)
        print("✅ 测试完成!")
        print("=" * 70)
        
    except FileNotFoundError as e:
        print(f"\n❌ 文件错误: {e}")
    except ValueError as e:
        print(f"\n❌ 参数错误: {e}")
    except Exception as e:
        print(f"\n❌ 解析失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
