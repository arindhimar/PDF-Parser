"""
parser.py – Core PDF parsing module using pytesseract (OCR) + pdf2image.

How it works:
    1. pdf2image.convert_from_path() converts each PDF page → PIL Image.
    2. pytesseract.image_to_string()  runs OCR on each image.
    3. All page texts are joined into a single string.

Usage:
    from parser import PDFParser

    p = PDFParser()

    # Parse a single PDF
    result = p.parse_pdf("path/to/resume.pdf")
    print(result["text"])
    print(result["page_count"])

    # Parse all PDFs in a folder
    results = p.parse_folder("../Dummy_Resumes/")
    for r in results:
        print(r["filename"], r["text"][:200])
"""

import os
import pytesseract
from pdf2image import convert_from_path


class PDFParser:
    """
    Parses PDF files via OCR using pytesseract + pdf2image.

    Args:
        dpi (int): Resolution used when rasterising PDF pages to images.
                   Higher values give better OCR accuracy at the cost of speed.
                   Default: 300.
        lang (str): Tesseract language code(s).  Default: 'eng'.
    """

    def __init__(self, dpi: int = 300, lang: str = "eng"):
        self.dpi  = dpi
        self.lang = lang

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def parse_pdf(self, file_path: str) -> dict:
        """
        Parse a single PDF file and extract its text via OCR.

        Args:
            file_path (str): Absolute or relative path to the PDF file.

        Returns:
            dict: {
                "filename"   : str,   # basename of the file
                "text"       : str,   # full OCR text (all pages joined)
                "page_count" : int,   # number of pages found
            }

        Raises:
            FileNotFoundError: If the file does not exist.
            ValueError:        If the file is not a .pdf file.
        """
        # ── Validations ──────────────────────────────────────────────
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        if not file_path.lower().endswith(".pdf"):
            raise ValueError(
                f"File must be a PDF (got '{file_path}'). Only .pdf files are supported."
            )

        filename = os.path.basename(file_path)
        print(f"  → Rasterising: {filename} (dpi={self.dpi}) ...")

        # ── Convert PDF pages → PIL images ───────────────────────────
        pages = convert_from_path(file_path, dpi=self.dpi)
        page_count = len(pages)
        print(f"  → Running OCR on {page_count} page(s) ...")

        # ── OCR each page ────────────────────────────────────────────
        page_texts = []
        for i, page_img in enumerate(pages, start=1):
            print(f"     page {i}/{page_count} ...", end="\r")
            text = pytesseract.image_to_string(page_img, lang=self.lang)
            page_texts.append(text)

        full_text = "\n\n".join(page_texts)

        return {
            "filename"   : filename,
            "text"       : full_text,
            "page_count" : page_count,
        }

    def parse_folder(self, folder_path: str) -> list:
        """
        Parse all PDF files found directly inside a folder.

        Args:
            folder_path (str): Path to the folder containing PDF files.

        Returns:
            list[dict]: A list of parse results (one per PDF).
                        Each item has the same structure as parse_pdf().
                        Failed files include an extra 'error' key.

        Raises:
            FileNotFoundError: If the folder does not exist.
        """
        if not os.path.exists(folder_path):
            raise FileNotFoundError(f"Folder not found: {folder_path}")

        pdf_files = sorted(
            f for f in os.listdir(folder_path) if f.lower().endswith(".pdf")
        )

        results = []
        total   = len(pdf_files)

        if total == 0:
            print(f"  No PDF files found in: {folder_path}")
            return results

        print(f"\nFound {total} PDF(s) in '{folder_path}':")
        for i, filename in enumerate(pdf_files, start=1):
            full_path = os.path.join(folder_path, filename)
            print(f"\n[{i}/{total}] {filename}")
            try:
                result = self.parse_pdf(full_path)
                results.append(result)
            except Exception as exc:
                print(f"  ✗ Failed to parse '{filename}': {exc}")
                results.append({
                    "filename"   : filename,
                    "text"       : "",
                    "page_count" : 0,
                    "error"      : str(exc),
                })

        return results
