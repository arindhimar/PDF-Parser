"""
extractor.py – AI-powered Resume Parsing Module.

1. Uses PyMuPDF (fitz) to extract raw text rapidly locally.
2. Uses Gemini 2.5 Flash via `google-genai` to structure the raw text
   into the exact 21 fields requested in `schema.py`.
"""

import os
import time
import base64
import re
import shutil
import tempfile
import threading
from queue import Queue
from io import BytesIO
import fitz  # PyMuPDF
from google import genai
from google.genai import types
from schema import CandidateProfile, JobDescriptionProfile

try:
    from docx2pdf import convert as docx2pdf_convert
    DOCX_CONVERTER_AVAILABLE = True
except Exception:
    docx2pdf_convert = None
    DOCX_CONVERTER_AVAILABLE = False

try:
    import pytesseract
    from PIL import Image
    OCR_AVAILABLE = True
except Exception:
    pytesseract = None
    Image = None
    OCR_AVAILABLE = False


class ResumeDataExtractor:
    """
    Extracts structured data from a PDF resume using PyMuPDF and Gemini.
    """

    def __init__(self, api_key: str = None):
        """
        Initializes the extractor with a Gemini API key.
        If api_key is None, it will look for the GEMINI_API_KEY env variable.
        """
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("A Gemini API Key must be provided either via arguments or the GEMINI_API_KEY environment variable.")

        self.client = genai.Client(api_key=self.api_key)
        # Using Gemini 2.5 Flash as it is highly efficient and excellent at structured data
        self.model_name = "gemini-2.5-flash"
        self.request_timeout_seconds = int(os.environ.get("GEMINI_REQUEST_TIMEOUT_SECONDS", "120"))

    def _prepare_pdf_input(self, file_path: str) -> tuple[str, str | None]:
        """
        Ensure the input is a PDF path.

        Returns:
            tuple[str, str | None]: (pdf_path, temp_dir_to_cleanup)
        """
        ext = os.path.splitext(file_path)[1].lower()

        if ext == ".pdf":
            return file_path, None

        if ext in (".doc", ".docx"):
            if not DOCX_CONVERTER_AVAILABLE:
                raise ValueError(
                    "Word input received (.doc/.docx) but converter is unavailable. "
                    "Install dependency 'docx2pdf' and ensure Microsoft Word is available on Windows."
                )

            temp_dir = tempfile.mkdtemp(prefix="resume_extractor_")
            pdf_name = f"{os.path.splitext(os.path.basename(file_path))[0]}.pdf"
            pdf_path = os.path.join(temp_dir, pdf_name)

            try:
                docx2pdf_convert(file_path, pdf_path)
            except Exception as exc:
                shutil.rmtree(temp_dir, ignore_errors=True)
                raise ValueError(f"Failed to convert Word document to PDF: {exc}") from exc

            if not os.path.exists(pdf_path):
                shutil.rmtree(temp_dir, ignore_errors=True)
                raise ValueError("Word to PDF conversion failed: output PDF was not created.")

            return pdf_path, temp_dir

        raise ValueError(
            f"Unsupported file type '{ext}'. Supported types are .pdf, .doc, .docx."
        )

    def _cleanup_temp_dir(self, temp_dir: str | None) -> None:
        """Delete temporary conversion directory when it exists."""
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)

    def _extract_text_with_ocr(self, page) -> str:
        """Run OCR on a rendered page image when native text is missing."""
        if not OCR_AVAILABLE:
            return ""

        try:
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
            image = Image.open(BytesIO(pix.tobytes("png")))
            text = pytesseract.image_to_string(image)
            return text or ""
        except Exception:
            return ""

    def _extract_profile_picture(self, doc) -> dict | None:
        """
        Extract a likely profile picture and return JSON-safe metadata.
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
                    continue

                score = (width * height) - (page_index * 20000)
                score -= abs(width - height) * 5

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
            "width": best["width"],
            "height": best["height"],
            "image_base64": base64.b64encode(best["image_bytes"]).decode("ascii"),
        }

    def _extract_raw_text(self, file_path: str) -> str:
        """Internal helper to extract text from a PDF, with OCR fallback."""
        page_texts = []
        ocr_used = False
        profile_picture = None

        with fitz.open(file_path) as doc:
            for page in doc:
                text = (page.get_text("text") or "").strip()
                if not text:
                    text = self._extract_text_with_ocr(page).strip()
                    if text:
                        ocr_used = True

                page_texts.append(text)

            profile_picture = self._extract_profile_picture(doc)

        return "\n\n".join(page_texts), ocr_used, profile_picture

    def _clean_string(self, value: str) -> str:
        """Normalize whitespace/control characters to avoid malformed multi-line fields."""
        if not isinstance(value, str):
            return value

        # Keep text single-line and compact while preserving readable content.
        compact = re.sub(r"[\r\n\t]+", " ", value)
        compact = re.sub(r"\s+", " ", compact).strip()
        return compact

    def _sanitize_skills(self, skills, candidate_name: str | None):
        """Split noisy multiline skills, trim noise, remove duplicates and obvious false positives."""
        if not isinstance(skills, list):
            return skills

        cleaned = []
        seen = set()
        candidate_name_clean = self._clean_string(candidate_name).lower() if isinstance(candidate_name, str) else None

        for skill in skills:
            if not isinstance(skill, str):
                continue

            # Break concatenated/newline blobs into individual candidates.
            parts = [self._clean_string(part) for part in re.split(r"[\r\n]+", skill)]
            for part in parts:
                if not part:
                    continue
                if candidate_name_clean and candidate_name_clean in part.lower():
                    pattern = re.compile(re.escape(candidate_name), flags=re.IGNORECASE)
                    part = self._clean_string(pattern.sub("", part))
                if not part:
                    continue
                if candidate_name_clean and part.lower() == candidate_name_clean:
                    continue
                if len(part) > 80:
                    continue

                key = part.lower()
                if key in seen:
                    continue
                seen.add(key)
                cleaned.append(part)

        return cleaned or None

    def _sanitize_result(self, payload: dict) -> dict:
        """Clean noisy string fields and fix known LLM extraction artifacts."""
        if not isinstance(payload, dict):
            return payload

        def walk(node):
            if isinstance(node, dict):
                return {k: walk(v) for k, v in node.items()}
            if isinstance(node, list):
                return [walk(item) for item in node]
            if isinstance(node, str):
                return self._clean_string(node)
            return node

        cleaned = walk(payload)
        cleaned["skills"] = self._sanitize_skills(
            cleaned.get("skills"),
            cleaned.get("candidate_name"),
        )
        return cleaned

    def _normalize_raw_text_for_llm(self, raw_text: str) -> str:
        """Normalize problematic unicode punctuation/control chars before sending text to Gemini."""
        if not isinstance(raw_text, str):
            return raw_text

        translation = str.maketrans(
            {
                "\u2018": "'",  # left single quote
                "\u2019": "'",  # right single quote
                "\u201B": "'",  # single high-reversed-9 quote
                "\u2032": "'",  # prime
                "\u201C": '"',  # left double quote
                "\u201D": '"',  # right double quote
                "\u2013": "-",  # en dash
                "\u2014": "-",  # em dash
                "\u00A0": " ",  # non-breaking space
            }
        )

        normalized = raw_text.translate(translation)
        normalized = normalized.replace("\x00", "")
        normalized = re.sub(r"\r\n?", "\n", normalized)
        normalized = re.sub(r"\n{4,}", "\n\n\n", normalized)
        return normalized.strip()

    def _generate_content_with_timeout(self, raw_text: str, instruction: str):
        """Call Gemini with a hard timeout so a stuck request does not halt the whole batch."""
        result_queue = Queue(maxsize=1)

        def _worker():
            try:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=raw_text,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=CandidateProfile,
                        system_instruction=instruction,
                        temperature=0.0,
                    ),
                )
                result_queue.put((True, response))
            except Exception as exc:
                result_queue.put((False, exc))

        thread = threading.Thread(target=_worker, daemon=True)
        thread.start()
        thread.join(timeout=self.request_timeout_seconds)

        if thread.is_alive():
            raise TimeoutError(
                f"Gemini request timed out after {self.request_timeout_seconds}s. "
                "Please retry or increase GEMINI_REQUEST_TIMEOUT_SECONDS."
            )

        ok, payload = result_queue.get()
        if ok:
            return payload
        raise payload

    def extract_from_pdf(self, file_path: str) -> dict:
        """
        Extracts raw text from a PDF and uses Gemini to map it to JSON.

        Args:
            file_path (str): Path to the resume file (.pdf/.doc/.docx).

        Returns:
            dict: The 21 parsed schema fields as a dictionary.

        Raises:
            FileNotFoundError, ValueError
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        pdf_path, temp_dir = self._prepare_pdf_input(file_path)

        try:
            print(f"  → 1. Reading document: {os.path.basename(file_path)} ...")
            raw_text, ocr_used, profile_picture = self._extract_raw_text(pdf_path)
            raw_text = self._normalize_raw_text_for_llm(raw_text)

            if not raw_text.strip():
                # If the document is blank or image-based and OCR fails, we skip cost.
                raise ValueError("No extractable text found in document (native + OCR both empty).")

            print(f"  → 2. Structuring {len(raw_text)} chars using Gemini ...")

            # System instructions to guide the extraction
            instruction = (
                "You are an expert technical recruiter."
                "Extract the requested candidate profile fields from the provided raw resume text."
                "Obey the Pydantic schema strictly. If a piece of information is definitively missing "
                "from the resume text, leave it as null (None)."
            )

            response = self._generate_content_with_timeout(raw_text, instruction)

            # Returns the parsed Pydantic object, which we convert to a dict
            candidate_obj = response.parsed
            result = candidate_obj.model_dump(mode="json")
            result = self._sanitize_result(result)
            result["ocr_used"] = ocr_used
            result["profile_picture"] = profile_picture
            return result
        finally:
            self._cleanup_temp_dir(temp_dir)

    def extract_jd_from_pdf(self, file_path: str) -> dict:
        """
        Extracts raw text from a JD PDF and maps it to the JD schema.

        Args:
            file_path (str): Path to the JD file (.pdf/.doc/.docx).

        Returns:
            dict: Parsed JD fields.

        Raises:
            FileNotFoundError, ValueError
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        pdf_path, temp_dir = self._prepare_pdf_input(file_path)

        try:
            print(f"  → 1. Reading JD document: {os.path.basename(file_path)} ...")
            raw_text, ocr_used, _ = self._extract_raw_text(pdf_path)

            if not raw_text.strip():
                raise ValueError("No extractable text found in document (native + OCR both empty).")

            print(f"  → 2. Structuring {len(raw_text)} chars using Gemini ...")

            instruction = (
                "You are an expert talent acquisition specialist. "
                "Extract requested job description fields from the provided JD text. "
                "Obey the Pydantic schema strictly. "
                "If a value is truly missing from the JD, return null. "
                "For boolean fields, map yes/no style language to true/false. "
                "Extract must-have and good-to-have skills as arrays when possible."
            )

            response = self.client.models.generate_content(
                model=self.model_name,
                contents=raw_text,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=JobDescriptionProfile,
                    system_instruction=instruction,
                    temperature=0.0,
                ),
            )

            jd_obj = response.parsed
            result = jd_obj.model_dump(mode="json")
            result["jd_document"] = os.path.basename(file_path)
            result["ocr_used"] = ocr_used
            return result
        finally:
            self._cleanup_temp_dir(temp_dir)

    def extract_folder(self, folder_path: str) -> list:
        """
        Processes all PDFs in a folder returning a list of dictionaries.
        """
        if not os.path.exists(folder_path):
            raise FileNotFoundError(f"Folder not found: {folder_path}")

        document_files = sorted(
            f for f in os.listdir(folder_path) if f.lower().endswith((".pdf", ".doc", ".docx"))
        )

        results = []
        total = len(document_files)

        if total == 0:
            print(f"  No supported files found in: {folder_path}")
            return results

        print(f"\nFound {total} document(s) in '{folder_path}':")
        for i, filename in enumerate(document_files, start=1):
            full_path = os.path.join(folder_path, filename)
            print(f"\n[{i}/{total}] {filename}")
            last_exc = None
            for attempt in range(2):  # 1 initial attempt + 1 retry
                try:
                    result_dict = self.extract_from_pdf(full_path)
                    result_dict["source_file"] = filename
                    results.append(result_dict)
                    last_exc = None
                    break
                except Exception as exc:
                    last_exc = exc
                    if attempt == 0:
                        print(f"  ⚠ Attempt 1 failed: {exc}")
                        print(f"  ↻ Retrying in 3 seconds...")
                        time.sleep(3)
            if last_exc is not None:
                print(f"  ✗ Failed after retry: {last_exc}")
                results.append({
                    "source_file": filename,
                    "error": str(last_exc),
                })

        return results

    def extract_jd_folder(self, folder_path: str) -> list:
        """
        Processes all JD PDFs in a folder returning a list of dictionaries.
        """
        if not os.path.exists(folder_path):
            raise FileNotFoundError(f"Folder not found: {folder_path}")

        document_files = sorted(
            f for f in os.listdir(folder_path) if f.lower().endswith((".pdf", ".doc", ".docx"))
        )

        results = []
        total = len(document_files)

        if total == 0:
            print(f"  No supported files found in: {folder_path}")
            return results

        print(f"\nFound {total} JD document(s) in '{folder_path}':")
        for i, filename in enumerate(document_files, start=1):
            full_path = os.path.join(folder_path, filename)
            print(f"\n[{i}/{total}] {filename}")
            last_exc = None
            for attempt in range(2):
                try:
                    result_dict = self.extract_jd_from_pdf(full_path)
                    result_dict["source_file"] = filename
                    results.append(result_dict)
                    last_exc = None
                    break
                except Exception as exc:
                    last_exc = exc
                    if attempt == 0:
                        print(f"  ⚠ Attempt 1 failed: {exc}")
                        print("  ↻ Retrying in 3 seconds...")
                        time.sleep(3)

            if last_exc is not None:
                print(f"  ✗ Failed after retry: {last_exc}")
                results.append(
                    {
                        "source_file": filename,
                        "error": str(last_exc),
                    }
                )

        return results
