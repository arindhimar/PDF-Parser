"""
extractor.py – AI-powered Resume Parsing Module.

1. Uses PyMuPDF (fitz) to extract raw text rapidly locally.
2. Uses Gemini 2.5 Flash via `google-genai` to structure the raw text
   into the exact 21 fields requested in `schema.py`.
"""

import os
import time
import fitz  # PyMuPDF
from google import genai
from google.genai import types
from schema import CandidateProfile


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

    def _extract_raw_text(self, file_path: str) -> str:
        """Internal helper to extract text from a PDF."""
        page_texts = []
        with fitz.open(file_path) as doc:
            for page in doc:
                text = page.get_text("text") or ""
                page_texts.append(text)
        return "\n\n".join(page_texts)

    def extract_from_pdf(self, file_path: str) -> dict:
        """
        Extracts raw text from a PDF and uses Gemini to map it to JSON.

        Args:
            file_path (str): Path to the PDF resume.

        Returns:
            dict: The 21 parsed schema fields as a dictionary.

        Raises:
            FileNotFoundError, ValueError
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        if not file_path.lower().endswith(".pdf"):
            raise ValueError(
                f"File must be a PDF (got '{file_path}'). Only .pdf files are supported."
            )

        print(f"  → 1. Reading PDF natively: {os.path.basename(file_path)} ...")
        raw_text = self._extract_raw_text(file_path)

        if not raw_text.strip():
            # If the PDF is completely blank or an image with no text layer, we skip cost
            raise ValueError("No extractable text found in PDF (might be an image/scan).")

        print(f"  → 2. Structuring {len(raw_text)} chars using Gemini ...")

        # System instructions to guide the extraction
        instruction = (
            "You are an expert technical recruiter."
            "Extract the requested candidate profile fields from the provided raw resume text."
            "Obey the Pydantic schema strictly. If a piece of information is definitively missing "
            "from the resume text, leave it as null (None)."
        )

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=raw_text,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=CandidateProfile,
                system_instruction=instruction,
                temperature=0.0, # Zero temp for maximum deterministic extraction
            ),
        )

        # Returns the parsed Pydantic object, which we convert to a dict
        candidate_obj = response.parsed
        return candidate_obj.model_dump(mode="json")

    def extract_folder(self, folder_path: str) -> list:
        """
        Processes all PDFs in a folder returning a list of dictionaries.
        """
        if not os.path.exists(folder_path):
            raise FileNotFoundError(f"Folder not found: {folder_path}")

        pdf_files = sorted(
            f for f in os.listdir(folder_path) if f.lower().endswith(".pdf")
        )

        results = []
        total = len(pdf_files)

        if total == 0:
            print(f"  No PDF files found in: {folder_path}")
            return results

        print(f"\nFound {total} PDF(s) in '{folder_path}':")
        for i, filename in enumerate(pdf_files, start=1):
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
