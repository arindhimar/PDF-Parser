"""
parser.py – Core PDF parsing module using LlamaCloud.

Usage:
    from parser import PDFParser

    p = PDFParser(api_key="your-llama-cloud-api-key")

    # Parse a single PDF
    result = p.parse_pdf("path/to/resume.pdf")
    print(result["markdown"])
    print(result["text"])

    # Parse all PDFs in a folder
    results = p.parse_folder("Dummy_Resumes/")
    for r in results:
        print(r["filename"], r["text"][:200])
"""

import os
from llama_cloud import LlamaCloud


class PDFParser:
    """
    Wraps the LlamaCloud API to parse PDF files and return structured data.

    Args:
        api_key (str): Your LlamaCloud API key.
        tier (str): Parsing tier. Options: fast, cost_effective, agentic, agentic_plus.
        version (str): Parsing version to use ('latest' or a specific version string).
    """

    def __init__(self, api_key: str, tier: str = "agentic", version: str = "latest"):
        self.api_key = api_key
        self.tier = tier
        self.version = version
        self._client = LlamaCloud(api_key=api_key)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def parse_pdf(self, file_path: str) -> dict:
        """
        Parse a single PDF file using LlamaCloud.

        Args:
            file_path (str): Absolute or relative path to the PDF file.

        Returns:
            dict: {
                "filename": str,       # basename of the file
                "markdown": str,       # full document as Markdown
                "text": str,           # full document as plain text
            }

        Raises:
            FileNotFoundError: If the file does not exist.
            ValueError: If the file is not a .pdf file.
        """
        # --- Validations ---
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        if not file_path.lower().endswith(".pdf"):
            raise ValueError(f"File must be a PDF (got '{file_path}'). Only .pdf files are supported.")

        filename = os.path.basename(file_path)
        print(f"  → Uploading: {filename} ...")

        # --- Upload file ---
        with open(file_path, "rb") as f:
            file_obj = self._client.files.create(
                file=(filename, f, "application/pdf"),
                purpose="parse",
            )

        print(f"  → Parsing:   {filename} (file_id={file_obj.id}) ...")

        # --- Parse ---
        result = self._client.parsing.parse(
            file_id=file_obj.id,
            tier=self.tier,
            version=self.version,
            expand=["markdown_full", "text_full"],
        )

        return {
            "filename": filename,
            "markdown": result.markdown_full or "",
            "text": result.text_full or "",
        }

    def parse_folder(self, folder_path: str) -> list:
        """
        Parse all PDF files found directly inside a folder.

        Args:
            folder_path (str): Path to the folder containing PDF files.

        Returns:
            list[dict]: A list of parse results (one per PDF).
                        Each item has the same structure as parse_pdf().

        Raises:
            FileNotFoundError: If the folder does not exist.
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
            try:
                result = self.parse_pdf(full_path)
                results.append(result)
            except Exception as exc:
                print(f"  ✗ Failed to parse '{filename}': {exc}")
                results.append({
                    "filename": filename,
                    "markdown": "",
                    "text": "",
                    "error": str(exc),
                })

        return results
