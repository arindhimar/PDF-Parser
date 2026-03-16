"""
run_all.py – Batch-extract structured data from all PDFs in Dummy_Resumes/.

Usage:
    python run_all.py

JSON Results are saved to output/<filename>.json
"""

import os
import json
from extractor import ResumeDataExtractor
from dotenv import load_dotenv

# Load variables from .env if present
load_dotenv()

RESUMES_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "Dummy_Resumes")
OUTPUT_FOLDER  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")

def save_result(result: dict, output_dir: str) -> None:
    """Saves a parsed JSON dictionary to a structured .json file."""
    os.makedirs(output_dir, exist_ok=True)
    base_name = os.path.splitext(result.get("source_file", "unknown"))[0]
    out_path  = os.path.join(output_dir, f"{base_name}.json")

    with open(out_path, "w", encoding="utf-8") as f:
        # Tightly structured, neatly indented JSON output
        json.dump(result, f, indent=4, ensure_ascii=False)

    print(f"  ✓ Saved: {out_path}")

def main():
    print("=" * 60)
    print("  Resume Data Extractor (LLM)")
    print("=" * 60)

    try:
        extractor = ResumeDataExtractor()
    except ValueError as e:
        print(f"\n[ERROR] {e}")
        print("Please set your GEMINI_API_KEY environment variable in a .env file or your terminal.")
        return

    results = extractor.extract_folder(RESUMES_FOLDER)

    print("\n" + "=" * 60)
    print("  RESULTS SUMMARY")
    print("=" * 60)

    for result in results:
        print(f"\n📄 {result['source_file']}")
        if "error" in result:
            print(f"   ✗ Error: {result['error']}")
        else:
            print(f"   ✓ Success - Extracted candidate: {result.get('candidate_name')}")
            save_result(result, OUTPUT_FOLDER)

    print(f"\nDone! Processed {len(results)} resume(s). JSON output saved to: {OUTPUT_FOLDER}")

if __name__ == "__main__":
    main()
