#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Parse PDF files using Zhipu GLM-OCR API and save results in MinerU-compatible format
"""

import argparse
import base64
import json
import os
from datetime import datetime
from pathlib import Path
import sys

import requests


def get_zhipu_api_key() -> str:
    """Get Zhipu API key from environment variable."""
    api_key = os.getenv("ZHIPU_API_KEY")
    if not api_key:
        raise ValueError(
            "ZHIPU_API_KEY not found in environment variables. "
            "Please set it in .env file or export it."
        )
    return api_key


def call_zhipu_ocr_api(
    pdf_path: Path,
    api_key: str,
    model: str = "glm-ocr",
    api_url: str = "https://open.bigmodel.cn/api/paas/v4/layout_parsing",
    timeout: int = 300,
) -> dict:
    """
    Call Zhipu GLM-OCR API to parse PDF document.

    Args:
        pdf_path: Path to PDF file
        api_key: Zhipu API key
        model: Model name (default: glm-ocr)
        api_url: API endpoint URL
        timeout: Request timeout in seconds

    Returns:
        API response dict containing md_results and layout_details
    """
    print(f"📄 Reading PDF file: {pdf_path.name}")

    # Check file size
    file_size_mb = pdf_path.stat().st_size / (1024 * 1024)
    print(f"📊 File size: {file_size_mb:.2f} MB")

    if file_size_mb > 50:
        raise ValueError(f"PDF file too large: {file_size_mb:.2f} MB (max 50MB)")

    # Read and encode PDF
    print("🔄 Encoding PDF to base64...")
    with open(pdf_path, "rb") as f:
        file_data = base64.b64encode(f.read()).decode("utf-8")

    # Build request payload
    request_data = {
        "model": model,
        "file": f"data:application/pdf;base64,{file_data}",
        "return_crop_images": False,  # We don't need images
        "need_layout_visualization": False,  # We don't need layout visualization
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    print(f"📤 Sending request to Zhipu API...")
    print(f"   Model: {model}")
    print(f"   Timeout: {timeout}s")

    try:
        response = requests.post(
            api_url,
            headers=headers,
            json=request_data,
            timeout=timeout,
        )
        response.raise_for_status()

        result = response.json()
        print(f"✅ API request successful!")

        # Display token usage
        usage = result.get("usage", {})
        if usage:
            print(f"💰 Token usage:")
            print(f"   Input: {usage.get('prompt_tokens', 0)}")
            print(f"   Output: {usage.get('completion_tokens', 0)}")
            print(f"   Total: {usage.get('total_tokens', 0)}")

        return result

    except requests.exceptions.RequestException as e:
        print(f"❌ API request failed: {e}")
        if hasattr(e, "response") and e.response is not None:
            print(f"Response: {e.response.text}")
        raise


def save_zhipu_results_mineru_format(
    result: dict,
    output_dir: Path,
    pdf_name: str,
) -> bool:
    """
    Save Zhipu OCR results in MinerU-compatible directory structure.

    MinerU structure:
    output_dir/
    └── auto/
        ├── {pdf_name}.md          # Main markdown content
        └── images/                # (empty, we don't use images)

    Args:
        result: Zhipu API response
        output_dir: Output directory path
        pdf_name: Original PDF filename (without extension)

    Returns:
        bool: Success status
    """
    try:
        # Create auto directory
        auto_dir = output_dir / "auto"
        auto_dir.mkdir(parents=True, exist_ok=True)

        # Create empty images directory for compatibility
        images_dir = auto_dir / "images"
        images_dir.mkdir(parents=True, exist_ok=True)

        # Extract markdown content
        md_content = result.get("md_results", "")
        layout_details = result.get("layout_details") or []
        if not md_content:
            print("⚠️ Warning: No markdown content in API response")
            return False

        # Save markdown file
        md_file = auto_dir / f"{pdf_name}.md"
        with open(md_file, "w", encoding="utf-8") as f:
            f.write(md_content)

        # Save a lightweight MinerU-compatible content_list file when layout details exist.
        if layout_details:
            content_list_file = auto_dir / f"{pdf_name}_content_list.json"
            with open(content_list_file, "w", encoding="utf-8") as f:
                json.dump(layout_details, f, ensure_ascii=False, indent=2)
            print(f"📋 Saved content list: {content_list_file.relative_to(output_dir)}")

        print(f"\n📝 Saved markdown: {md_file.relative_to(output_dir)}")
        print(f"   Content length: {len(md_content)} characters")

        # Save raw API response for debugging (optional)
        response_file = auto_dir / f"{pdf_name}_api_response.json"
        with open(response_file, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        print(f"📋 Saved API response: {response_file.relative_to(output_dir)}")

        return True

    except Exception as e:
        print(f"❌ Error saving results: {e}")
        import traceback

        traceback.print_exc()
        return False


def parse_pdf_with_zhipu(
    pdf_path: str,
    output_base_dir: str | Path | None = None,
    api_key: str | None = None,
) -> bool:
    """
    Parse PDF file using Zhipu GLM-OCR API.

    Args:
        pdf_path: Path to PDF file
        output_base_dir: Base directory for output (defaults to mimic_papers)
        api_key: Zhipu API key (defaults to ZHIPU_API_KEY env var)

    Returns:
        bool: Whether parsing was successful
    """
    print("=" * 80)
    print("🤖 Zhipu GLM-OCR PDF Parser")
    print("=" * 80)

    # Get API key
    if api_key is None:
        try:
            api_key = get_zhipu_api_key()
        except ValueError as e:
            print(f"❌ {e}")
            return False

    print("🔑 API Key: [loaded from environment or argument]")

    # Validate PDF file
    pdf_file = Path(pdf_path).resolve()
    if not pdf_file.exists():
        print(f"❌ PDF file does not exist: {pdf_file}")
        return False

    if pdf_file.suffix.lower() != ".pdf":
        print(f"❌ File is not PDF format: {pdf_file}")
        return False

    # Setup output directory
    project_root = Path(__file__).parent.parent.parent.parent
    if output_base_dir is None:
        output_root = project_root / "data" / "user" / "question" / "mimic_papers"
    else:
        output_root = Path(output_base_dir)

    output_root.mkdir(parents=True, exist_ok=True)

    # Use provided output directory directly when it already points to a batch directory.
    pdf_name = pdf_file.stem
    if output_root.name.startswith("mimic_"):
        output_dir = output_root / pdf_name
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = output_root / f"mimic_{timestamp}_{pdf_name}"

    print(f"📁 Output directory: {output_dir}")
    print()

    try:
        # Call Zhipu OCR API
        result = call_zhipu_ocr_api(pdf_file, api_key)

        # Save results in MinerU-compatible format
        success = save_zhipu_results_mineru_format(result, output_dir, pdf_name)

        if success:
            print()
            print("=" * 80)
            print("✅ Parsing completed successfully!")
            print("=" * 80)
            print(f"📂 Output: {output_dir}")
            print(f"📄 Markdown: {output_dir / 'auto' / f'{pdf_name}.md'}")
            return True
        else:
            return False

    except Exception as e:
        print(f"❌ Parsing failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """Command-line entry point."""
    parser = argparse.ArgumentParser(
        description="Parse PDF files using Zhipu GLM-OCR API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Parse a PDF file
  python pdf_parser_zhipu.py /path/to/paper.pdf

  # Parse PDF with custom output directory
  python pdf_parser_zhipu.py /path/to/paper.pdf -o /custom/output/dir

  # Parse PDF with custom API key
  python pdf_parser_zhipu.py /path/to/paper.pdf --api-key YOUR_API_KEY
        """,
    )

    parser.add_argument("pdf_path", type=str, help="Path to PDF file")

    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default=None,
        help="Base directory for output (default: data/user/question/mimic_papers)",
    )

    parser.add_argument(
        "--api-key",
        type=str,
        default=None,
        help="Zhipu API key (default: read from ZHIPU_API_KEY env var)",
    )

    args = parser.parse_args()

    success = parse_pdf_with_zhipu(args.pdf_path, args.output, args.api_key)

    if success:
        print("\n✅ Done!")
        sys.exit(0)
    else:
        print("\n❌ Failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
