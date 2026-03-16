"""
parser.py – Core PDF parsing module using PyMuPDF (fitz)

How it works:
    1. fitz.open(file_path) safely opens the PDF stream.
    2. page.get_text() extracts the rich text from each page natively.
    3. All page texts are joined into a single clean string.

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
import fitz  # PyMuPDF


class PDFParser:
    """
    Parses PDF files using PyMuPDF to extract raw text natively.
    """

    def __init__(self):
        pass

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def parse_pdf(self, file_path: str) -> dict:
        """
        Parse a single PDF file and extract its text via PyMuPDF.

        Args:
            file_path (str): Absolute or relative path to the PDF file.

        Returns:
            dict: {
                "filename"   : str,   # basename of the file
                "text"       : str,   # full text (all pages joined)
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

        # ── Extract Text ─────────────────────────────────────────────
        page_texts = []
        page_count = 0
        
        # Opens document securely inside context manager
        with fitz.open(file_path) as doc:
            page_count = len(doc)
            
            for page in doc:
                text = page.get_text("text") or ""
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
