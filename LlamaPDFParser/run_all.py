"""
run_all.py – Batch-parse all PDFs in the Dummy_Resumes/ folder.

Usage:
    python run_all.py

Results are printed to the console and also saved to output/<filename>.txt
"""

import os
from parser import PDFParser

# -----------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------
API_KEY = "llx-"
RESUMES_FOLDER = os.path.join(os.path.dirname(__file__), "Dummy_Resumes")
OUTPUT_FOLDER = os.path.join(os.path.dirname(__file__), "output")


def save_result(result: dict, output_dir: str) -> None:
    """Save a single parse result to a .txt file in output_dir."""
    os.makedirs(output_dir, exist_ok=True)
    base_name = os.path.splitext(result["filename"])[0]
    out_path = os.path.join(output_dir, f"{base_name}.txt")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(f"=== {result['filename']} ===\n\n")
        f.write("--- MARKDOWN ---\n")
        f.write(result.get("markdown", "") + "\n\n")
        f.write("--- PLAIN TEXT ---\n")
        f.write(result.get("text", "") + "\n")

    print(f"  ✓ Saved: {out_path}")


def main():
    print("=" * 60)
    print("  LlamaPDF Resume Parser")
    print("=" * 60)

    parser = PDFParser(api_key=API_KEY)
    results = parser.parse_folder(RESUMES_FOLDER)

    print("\n" + "=" * 60)
    print("  RESULTS SUMMARY")
    print("=" * 60)

    for result in results:
        print(f"\n📄 {result['filename']}")

        if "error" in result:
            print(f"   ✗ Error: {result['error']}")
            continue

        # Preview first 300 chars of plain text
        preview = result["text"][:300].replace("\n", " ").strip()
        print(f"   Preview: {preview}...")

        # Save full output
        save_result(result, OUTPUT_FOLDER)

    print(f"\nDone! Parsed {len(results)} resume(s). Output saved to: {OUTPUT_FOLDER}")


if __name__ == "__main__":
    main()
