#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
下载智谱 OCR 结果中的所有图片到本地

用途：
1. 下载裁剪的内容图片（crop）- 从 PDF 中提取的图表
2. 下载布局可视化图片（layout）- 页面布局标注图
3. 替换 Markdown 中的临时链接为本地路径
"""

import json
import re
from pathlib import Path
from urllib.parse import urlparse

import requests


def download_image(url: str, output_path: Path) -> bool:
    """
    下载图片到本地

    Args:
        url: 图片 URL
        output_path: 保存路径

    Returns:
        是否下载成功
    """
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "wb") as f:
            f.write(response.content)

        return True

    except Exception as e:
        print(f"   ✗ 下载失败: {e}")
        return False


def extract_crop_images_from_layout(layout_details: list) -> list:
    """
    从布局详情中提取所有裁剪图片的 URL

    Args:
        layout_details: 布局详情数据

    Returns:
        图片信息列表 [(url, page_num, index), ...]
    """
    crop_images = []

    for page_num, page_elements in enumerate(layout_details, 1):
        for element in page_elements:
            if element.get("label") == "image":
                url = element.get("content", "")
                if url.startswith("http"):
                    crop_images.append(
                        {
                            "url": url,
                            "page": page_num,
                            "index": element.get("index", 0),
                            "bbox": element.get("bbox_2d", []),
                        }
                    )

    return crop_images


def replace_urls_in_markdown(md_file: Path, url_mapping: dict) -> Path:
    """
    替换 Markdown 中的临时 URL 为本地路径

    Args:
        md_file: Markdown 文件路径
        url_mapping: URL 映射字典 {原始URL: 本地路径}

    Returns:
        新的 Markdown 文件路径
    """
    with open(md_file, "r", encoding="utf-8") as f:
        content = f.read()

    # 替换所有 URL
    for original_url, local_path in url_mapping.items():
        # 转换为相对路径
        relative_path = local_path.replace("\\", "/")
        content = content.replace(original_url, relative_path)

    # 保存为新文件
    new_md_file = md_file.parent / f"{md_file.stem}_local.md"
    with open(new_md_file, "w", encoding="utf-8") as f:
        f.write(content)

    return new_md_file


def main():
    """主函数"""
    print("=" * 70)
    print("📥 下载智谱 OCR 图片到本地")
    print("=" * 70)

    # 查找最新的 OCR 结果
    output_dir = Path(__file__).parent / "zhipu_ocr_output"

    if not output_dir.exists():
        print(f"\n❌ 输出目录不存在: {output_dir}")
        return

    # 查找 JSON 文件
    json_files = sorted(output_dir.glob("layout_details_*.json"))

    if not json_files:
        print(f"\n❌ 未找到布局详情文件")
        return

    latest_json = json_files[-1]
    print(f"\n📄 使用文件: {latest_json.name}")

    # 读取布局详情
    with open(latest_json, "r", encoding="utf-8") as f:
        layout_details = json.load(f)

    # 提取裁剪图片
    crop_images = extract_crop_images_from_layout(layout_details)

    print(f"\n🖼️  发现 {len(crop_images)} 个裁剪图片")

    if not crop_images:
        print("   没有需要下载的图片")
        return

    # 创建图片目录
    images_dir = output_dir / "extracted_images"
    images_dir.mkdir(parents=True, exist_ok=True)

    # 下载图片
    url_mapping = {}
    success_count = 0

    for idx, img_info in enumerate(crop_images, 1):
        url = img_info["url"]
        page = img_info["page"]
        element_idx = img_info["index"]

        # 生成文件名
        filename = f"page_{page}_image_{element_idx}.png"
        output_path = images_dir / filename

        print(f"\n📥 [{idx}/{len(crop_images)}] 下载图片:")
        print(f"   页码: {page}")
        print(f"   索引: {element_idx}")
        print(f"   位置: {img_info['bbox']}")
        print(f"   保存: {filename}")

        if download_image(url, output_path):
            print(f"   ✓ 下载成功")
            success_count += 1

            # 记录 URL 映射
            url_mapping[url] = f"extracted_images/{filename}"
        else:
            print(f"   ✗ 下载失败")

    print(f"\n📊 下载统计:")
    print(f"   总数: {len(crop_images)}")
    print(f"   成功: {success_count}")
    print(f"   失败: {len(crop_images) - success_count}")

    # 替换 Markdown 中的 URL
    if url_mapping:
        print(f"\n📝 更新 Markdown 文件...")

        md_files = sorted(output_dir.glob("ocr_result_*.md"))
        if md_files:
            latest_md = md_files[-1]
            new_md = replace_urls_in_markdown(latest_md, url_mapping)
            print(f"   ✓ 已创建本地版本: {new_md.name}")
            print(f"   原始文件: {latest_md.name}")
        else:
            print(f"   ⚠️  未找到 Markdown 文件")

    print(f"\n✅ 完成！所有图片已保存到: {images_dir}")
    print(f"\n💡 提示:")
    print(f"   - 原始图片链接将在 4 天后过期")
    print(f"   - 本地图片已永久保存")
    print(f"   - 使用 *_local.md 文件查看本地图片版本")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
