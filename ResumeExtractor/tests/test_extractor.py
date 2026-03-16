"""
test_extractor.py - TDD tests for the Resume Extractor module.

Tests the logic surrounding file validation, PyMuPDF extraction,
and formatting the final dictionary *without* making actual API calls.
"""

import os
import pytest
from unittest.mock import MagicMock, patch

from schema import CandidateProfile, CurrentStatus

# ---------------------------------------------------------------------------
# Helpers – build fake objects for PyMuPDF and Gemini
# ---------------------------------------------------------------------------

def _make_mock_page(text="Mocked Resume Text"):
    mock_page = MagicMock()
    mock_page.get_text.return_value = text
    return mock_page

def _make_mock_fitz_doc(pages=1, text="Mocked Resume Text"):
    mock_doc = MagicMock()
    mock_pages = [_make_mock_page(text) for _ in range(pages)]
    # Use side_effect to return a fresh iterator every time `iter(doc)` is called
    mock_doc.__iter__.side_effect = lambda: iter(mock_pages)
    mock_doc.__len__.return_value = pages
    mock_doc.__enter__.return_value = mock_doc
    mock_doc.__exit__.return_value = None
    return mock_doc

def _make_mock_gemini_response(structured_obj=None):
    """Mocks the google-genai response object that contains a parsed Pydantic object."""
    mock_response = MagicMock()
    if structured_obj is None:
        # Provide a minimal valid Pydantic object
        structured_obj = CandidateProfile(
            candidate_name="John Doe",
            email_id="john@example.com",
            phone_number="1234567890",
            current_status=CurrentStatus.WORKING,
            notice_period="30 days",
            current_salary=50000.0
        )
    mock_response.parsed = structured_obj
    return mock_response


# ============================================================
# 1. extract_from_pdf – happy path
# ============================================================

class TestExtractFromPdf:

    def test_extract_returns_valid_dict(self, tmp_path):
        """extract_from_pdf() must return a dictionary with the 21+ requested keys."""
        pdf = tmp_path / "resume.pdf"
        pdf.write_bytes(b"%PDF-1.4 fake")

        mock_gemini = MagicMock()
        mock_gemini.models.generate_content.return_value = _make_mock_gemini_response()

        with patch("extractor.fitz.open", return_value=_make_mock_fitz_doc(text="Mock text")), \
             patch("extractor.genai.Client", return_value=mock_gemini):
            from extractor import ResumeDataExtractor
            
            # Use fake api key so it doesn't try to look for real env var
            extractor = ResumeDataExtractor(api_key="fake-key")
            result = extractor.extract_from_pdf(str(pdf))

        assert isinstance(result, dict)
        # Checking some core fields exist in output
        assert "candidate_name" in result
        assert result["candidate_name"] == "John Doe"
        assert result["email_id"] == "john@example.com"
        assert "current_salary" in result
        
        # Test default/optional handles
        assert "expected_salary" in result
        assert result["expected_salary"] is None  # Defaults to None (null)

    def test_gemini_called_with_resume_text(self, tmp_path):
        """Ensures the text extracted from the PDF is correctly passed to the Gemini prompt."""
        pdf = tmp_path / "resume.pdf"
        pdf.write_bytes(b"%PDF-1.4 fake")

        mock_gemini = MagicMock()
        mock_gemini.models.generate_content.return_value = _make_mock_gemini_response()

        with patch("extractor.fitz.open", return_value=_make_mock_fitz_doc(text="TESTING OCR DATA")), \
             patch("extractor.genai.Client", return_value=mock_gemini):
            from extractor import ResumeDataExtractor
            extractor = ResumeDataExtractor(api_key="fake-key")
            extractor.extract_from_pdf(str(pdf))

        # Check what was passed to generate_content
        call_args = mock_gemini.models.generate_content.call_args[1]
        assert "TESTING OCR DATA" in call_args["contents"]


# ============================================================
# 2. Extract Errors
# ============================================================

class TestExtractErrors:

    def test_extract_missing_file_raises(self):
        """Must raise FileNotFoundError for bad paths."""
        with patch("extractor.genai.Client"):
            from extractor import ResumeDataExtractor
            extractor = ResumeDataExtractor(api_key="fake-key")
            with pytest.raises(FileNotFoundError):
                extractor.extract_from_pdf("/no/such/file.pdf")

    def test_extract_non_pdf_raises(self, tmp_path):
        """Must raise ValueError for non-.pdf files."""
        txt = tmp_path / "resume.txt"
        txt.write_text("not a pdf")

        with patch("extractor.genai.Client"):
            from extractor import ResumeDataExtractor
            extractor = ResumeDataExtractor(api_key="fake-key")
            with pytest.raises(ValueError, match="must be a PDF"):
                extractor.extract_from_pdf(str(txt))


# ============================================================
# 3. Batch extraction
# ============================================================

class TestExtractFolder:

    def test_extract_folder_returns_list(self, tmp_path):
        """extract_folder() must return a list of parsed dictionaries."""
        (tmp_path / "a.pdf").write_bytes(b"%PDF-1.4")
        (tmp_path / "b.pdf").write_bytes(b"%PDF-1.4")

        mock_gemini = MagicMock()
        mock_gemini.models.generate_content.return_value = _make_mock_gemini_response()

        with patch("extractor.fitz.open", return_value=_make_mock_fitz_doc(text="Mocked Text")), \
             patch("extractor.genai.Client", return_value=mock_gemini):
            from extractor import ResumeDataExtractor
            extractor = ResumeDataExtractor(api_key="fake-key")
            results = extractor.extract_folder(str(tmp_path))

        assert isinstance(results, list)
        assert len(results) == 2
        
        for r in results:
            assert "candidate_name" in r
            assert "source_file" in r # Custom key specific to folder runner 

    def test_failed_pdfs_record_error(self, tmp_path):
        """If fitz fails, record an error key gracefully without crashing batch."""
        (tmp_path / "bad.pdf").write_bytes(b"%PDF-1.4")

        mock_gemini = MagicMock()

        # Fitz crashes on open
        with patch("extractor.fitz.open", side_effect=Exception("Corrupted PDF")), \
             patch("extractor.genai.Client", return_value=mock_gemini):
            from extractor import ResumeDataExtractor
            extractor = ResumeDataExtractor(api_key="fake-key")
            results = extractor.extract_folder(str(tmp_path))

        assert len(results) == 1
        assert "error" in results[0]
        assert "Corrupted PDF" in results[0]["error"]
