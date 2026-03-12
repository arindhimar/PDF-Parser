"""
run_all.py – Batch-parse all PDFs in the Dummy_Resumes/ folder using pytesseract OCR.

Usage:
    python run_all.py

Results are printed to the console and also saved to output/<filename>.txt

Prerequisites:
  • pip install -r requirements.txt
  • Tesseract-OCR installed and on PATH
      Windows: https://github.com/UB-Mannheim/tesseract/wiki
      macOS:   brew install tesseract
      Linux:   sudo apt-get install tesseract-ocr
  • Poppler installed and on PATH (needed by pdf2image)
      Windows: https://github.com/oschwartz10612/poppler-windows/releases
      macOS:   brew install poppler
      Linux:   sudo apt-get install poppler-utils
"""

import os
from parser import PDFParser

# -----------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------
RESUMES_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "Dummy_Resumes")
OUTPUT_FOLDER  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")

# OCR settings – raise dpi for better accuracy (slower)
DPI  = 300
LANG = "eng"


def save_result(result: dict, output_dir: str) -> None:
    """Save a single parse result to a .txt file in output_dir."""
    os.makedirs(output_dir, exist_ok=True)
    base_name = os.path.splitext(result["filename"])[0]
    out_path  = os.path.join(output_dir, f"{base_name}.txt")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(f"=== {result['filename']} ===\n\n")
        f.write(f"Pages: {result.get('page_count', '?')}\n\n")
        f.write("--- PLAIN TEXT (OCR) ---\n")
        f.write(result.get("text", "") + "\n")

    print(f"  ✓ Saved: {out_path}")


def main():
    print("=" * 60)
    print("  TesseractPDF Resume Parser")
    print("=" * 60)

    parser  = PDFParser(dpi=DPI, lang=LANG)
    results = parser.parse_folder(RESUMES_FOLDER)

    print("\n" + "=" * 60)
    print("  RESULTS SUMMARY")
    print("=" * 60)

    for result in results:
        print(f"\n📄 {result['filename']}  ({result.get('page_count', '?')} page(s))")

        if "error" in result:
            print(f"   ✗ Error: {result['error']}")
            continue

        preview = result["text"][:300].replace("\n", " ").strip()
        print(f"   Preview: {preview}...")

        save_result(result, OUTPUT_FOLDER)

    print(f"\nDone! Parsed {len(results)} resume(s). Output saved to: {OUTPUT_FOLDER}")


if __name__ == "__main__":
    main()
