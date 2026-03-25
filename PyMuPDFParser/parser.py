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
from io import BytesIO
import fitz  # PyMuPDF

try:
    import pytesseract
    from PIL import Image
    OCR_AVAILABLE = True
except Exception:
    pytesseract = None
    Image = None
    OCR_AVAILABLE = False


class PDFParser:
    """
    Parses PDF files using PyMuPDF to extract raw text natively.
    """

    def __init__(self):
        pass

    def _extract_text_with_ocr(self, page) -> str:
        """
        Extract text from a page by rendering it as an image and running OCR.

        Returns an empty string if OCR is unavailable or extraction fails.
        """
        if not OCR_AVAILABLE:
            return ""

        try:
            # Render at higher resolution for better OCR accuracy.
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
            image = Image.open(BytesIO(pix.tobytes("png")))
            text = pytesseract.image_to_string(image)
            return text or ""
        except Exception:
            return ""

    def _extract_profile_picture(self, doc) -> dict | None:
        """
        Extract a likely profile picture from the PDF.

        Strategy:
            - Scan images on each page.
            - Prefer images from early pages.
            - Prefer near-square images (common for profile photos).
            - Prefer images near the top region of page 1.

        Returns:
            dict | None: {
                "ext": str,
                "image_bytes": bytes,
                "width": int,
                "height": int,
            } or None when no suitable image is found.
        """
        candidates = []

        for page_index, page in enumerate(doc):
            for image_data in page.get_images(full=True):
                xref = image_data[0]

                try:
                    extracted = doc.extract_image(xref)
                except Exception:
                    continue

                img_bytes = extracted.get("image")
                width = int(extracted.get("width", 0) or 0)
                height = int(extracted.get("height", 0) or 0)

                if not img_bytes or width < 40 or height < 40:
                    continue

                aspect_ratio = max(width / max(height, 1), height / max(width, 1))
                if aspect_ratio > 2.2:
                    # Skip very wide or tall assets (banners, separators, etc.)
                    continue

                score = (width * height) - (page_index * 20000)
                score -= abs(width - height) * 5

                # Give extra weight to images near top of first page.
                if page_index == 0:
                    try:
                        rects = page.get_image_rects(xref)
                        if rects:
                            rect = rects[0]
                            if rect.y0 <= (page.rect.height * 0.45):
                                score += 40000
                    except Exception:
                        pass

                candidates.append(
                    {
                        "score": score,
                        "ext": extracted.get("ext", "png"),
                        "image_bytes": img_bytes,
                        "width": width,
                        "height": height,
                    }
                )

        if not candidates:
            return None

        best = max(candidates, key=lambda item: item["score"])
        return {
            "ext": best["ext"],
            "image_bytes": best["image_bytes"],
            "width": best["width"],
            "height": best["height"],
        }

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
                "profile_picture": dict | None,
                "ocr_used"   : bool,  # True if OCR fallback was used
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
        profile_picture = None
        ocr_used = False
        
        # Opens document securely inside context manager
        with fitz.open(file_path) as doc:
            page_count = len(doc)
            
            for page in doc:
                text = (page.get_text("text") or "").strip()

                # Fallback for scanned/image-only PDFs where native text is empty.
                if not text:
                    text = self._extract_text_with_ocr(page).strip()
                    if text:
                        ocr_used = True

                page_texts.append(text)

            # Search once per document for a likely profile picture.
            profile_picture = self._extract_profile_picture(doc)

        full_text = "\n\n".join(page_texts)

        return {
            "filename"   : filename,
            "text"       : full_text,
            "page_count" : page_count,
            "profile_picture": profile_picture,
            "ocr_used"   : ocr_used,
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
                    "profile_picture": None,
                    "ocr_used"   : False,
                    "error"      : str(exc),
                })

        return results
