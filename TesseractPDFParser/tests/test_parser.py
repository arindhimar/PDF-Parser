"""
TDD Tests for parser.py (TesseractPDFParser)
Tests are written BEFORE implementation (Test-Driven Development).

The pytesseract and pdf2image calls are fully mocked so no Tesseract
binary or real PDF is needed to run the suite.

Run with:
    pytest tests/ -v
"""

import os
import pytest
from unittest.mock import MagicMock, patch, call
from PIL import Image


# ---------------------------------------------------------------------------
# Helpers – tiny factory functions for mock return values
# ---------------------------------------------------------------------------

def _fake_image():
    """Return a minimal 1x1 white PIL image (stands in for a real PDF page)."""
    return Image.new("RGB", (1, 1), color=(255, 255, 255))


def _make_mock_convert(pages=2):
    """Return a side-effect factory that gives `pages` fake PIL images."""
    return [_fake_image() for _ in range(pages)]


# ============================================================
# 1. parse_pdf – happy path
# ============================================================

class TestParsePdf:

    def test_parse_pdf_returns_dict(self, tmp_path):
        """parse_pdf() must return a dict."""
        pdf = tmp_path / "resume.pdf"
        pdf.write_bytes(b"%PDF-1.4 fake")

        with patch("parser.convert_from_path", return_value=_make_mock_convert(1)), \
             patch("parser.pytesseract.image_to_string", return_value="Jane Doe"):
            from parser import PDFParser
            result = PDFParser().parse_pdf(str(pdf))

        assert isinstance(result, dict)

    def test_parse_pdf_has_required_keys(self, tmp_path):
        """parse_pdf() result must contain 'filename', 'text', 'page_count'."""
        pdf = tmp_path / "resume.pdf"
        pdf.write_bytes(b"%PDF-1.4 fake")

        with patch("parser.convert_from_path", return_value=_make_mock_convert(1)), \
             patch("parser.pytesseract.image_to_string", return_value="Jane Doe"):
            from parser import PDFParser
            result = PDFParser().parse_pdf(str(pdf))

        assert "filename"   in result
        assert "text"       in result
        assert "page_count" in result

    def test_parse_pdf_filename_is_basename(self, tmp_path):
        """filename in result must be just the file's basename, not the full path."""
        pdf = tmp_path / "my_resume.pdf"
        pdf.write_bytes(b"%PDF-1.4 fake")

        with patch("parser.convert_from_path", return_value=_make_mock_convert(1)), \
             patch("parser.pytesseract.image_to_string", return_value="text"):
            from parser import PDFParser
            result = PDFParser().parse_pdf(str(pdf))

        assert result["filename"] == "my_resume.pdf"

    def test_parse_pdf_text_contains_ocr_output(self, tmp_path):
        """text key must concatenate the OCR output from all pages."""
        pdf = tmp_path / "resume.pdf"
        pdf.write_bytes(b"%PDF-1.4 fake")

        ocr_outputs = ["John Doe\nSoftware Engineer", "Skills: Python"]

        with patch("parser.convert_from_path", return_value=_make_mock_convert(2)), \
             patch("parser.pytesseract.image_to_string", side_effect=ocr_outputs):
            from parser import PDFParser
            result = PDFParser().parse_pdf(str(pdf))

        assert "John Doe" in result["text"]
        assert "Skills: Python" in result["text"]

    def test_parse_pdf_page_count_matches(self, tmp_path):
        """page_count must equal the number of pages returned by convert_from_path."""
        pdf = tmp_path / "resume.pdf"
        pdf.write_bytes(b"%PDF-1.4 fake")

        with patch("parser.convert_from_path", return_value=_make_mock_convert(3)), \
             patch("parser.pytesseract.image_to_string", return_value="page text"):
            from parser import PDFParser
            result = PDFParser().parse_pdf(str(pdf))

        assert result["page_count"] == 3

    def test_parse_pdf_calls_ocr_once_per_page(self, tmp_path):
        """image_to_string must be called exactly once per PDF page."""
        pdf = tmp_path / "resume.pdf"
        pdf.write_bytes(b"%PDF-1.4 fake")

        with patch("parser.convert_from_path", return_value=_make_mock_convert(4)) as _, \
             patch("parser.pytesseract.image_to_string", return_value="x") as mock_ocr:
            from parser import PDFParser
            PDFParser().parse_pdf(str(pdf))

        assert mock_ocr.call_count == 4


# ============================================================
# 2. parse_pdf – error cases
# ============================================================

class TestParsePdfErrors:

    def test_parse_pdf_missing_file_raises_file_not_found(self):
        """parse_pdf() must raise FileNotFoundError for a non-existent path."""
        from parser import PDFParser
        with pytest.raises(FileNotFoundError):
            PDFParser().parse_pdf("/no/such/file.pdf")

    def test_parse_pdf_non_pdf_raises_value_error(self, tmp_path):
        """parse_pdf() must raise ValueError when the file is not a .pdf."""
        txt = tmp_path / "resume.txt"
        txt.write_text("not a pdf")

        from parser import PDFParser
        with pytest.raises(ValueError, match="must be a PDF"):
            PDFParser().parse_pdf(str(txt))


# ============================================================
# 3. parse_folder – happy path
# ============================================================

class TestParseFolder:

    def test_parse_folder_returns_list(self, tmp_path):
        """parse_folder() must return a list."""
        (tmp_path / "a.pdf").write_bytes(b"%PDF-1.4")
        (tmp_path / "b.pdf").write_bytes(b"%PDF-1.4")

        with patch("parser.convert_from_path", return_value=_make_mock_convert(1)), \
             patch("parser.pytesseract.image_to_string", return_value="text"):
            from parser import PDFParser
            results = PDFParser().parse_folder(str(tmp_path))

        assert isinstance(results, list)

    def test_parse_folder_count_matches_pdfs(self, tmp_path):
        """parse_folder() must return exactly one result per PDF (ignores non-PDFs)."""
        for name in ["cv1.pdf", "cv2.pdf", "cv3.pdf"]:
            (tmp_path / name).write_bytes(b"%PDF-1.4")
        (tmp_path / "notes.txt").write_text("ignore me")

        with patch("parser.convert_from_path", return_value=_make_mock_convert(1)), \
             patch("parser.pytesseract.image_to_string", return_value="text"):
            from parser import PDFParser
            results = PDFParser().parse_folder(str(tmp_path))

        assert len(results) == 3, f"Expected 3, got {len(results)}"

    def test_parse_folder_each_result_has_required_keys(self, tmp_path):
        """Every item in parse_folder() results must have filename, text, page_count."""
        for name in ["r1.pdf", "r2.pdf"]:
            (tmp_path / name).write_bytes(b"%PDF-1.4")

        with patch("parser.convert_from_path", return_value=_make_mock_convert(1)), \
             patch("parser.pytesseract.image_to_string", return_value="data"):
            from parser import PDFParser
            results = PDFParser().parse_folder(str(tmp_path))

        for r in results:
            assert "filename"   in r
            assert "text"       in r
            assert "page_count" in r

    def test_parse_folder_filenames_are_basenames(self, tmp_path):
        """Filenames in results must be basenames only (not full paths)."""
        (tmp_path / "only_name.pdf").write_bytes(b"%PDF-1.4")

        with patch("parser.convert_from_path", return_value=_make_mock_convert(1)), \
             patch("parser.pytesseract.image_to_string", return_value="x"):
            from parser import PDFParser
            results = PDFParser().parse_folder(str(tmp_path))

        assert results[0]["filename"] == "only_name.pdf"


# ============================================================
# 4. parse_folder – error cases
# ============================================================

class TestParseFolderErrors:

    def test_parse_folder_missing_folder_raises(self):
        """parse_folder() must raise FileNotFoundError for a non-existent folder."""
        from parser import PDFParser
        with pytest.raises(FileNotFoundError):
            PDFParser().parse_folder("/no/such/folder")

    def test_parse_folder_empty_folder_returns_empty_list(self, tmp_path):
        """parse_folder() on an empty folder must return [] (not raise)."""
        from parser import PDFParser
        results = PDFParser().parse_folder(str(tmp_path))
        assert results == []

    def test_parse_folder_failed_pdf_recorded_with_error_key(self, tmp_path):
        """If one PDF fails to parse, its result dict must contain an 'error' key."""
        (tmp_path / "bad.pdf").write_bytes(b"%PDF-1.4")

        with patch("parser.convert_from_path", side_effect=Exception("poppler error")):
            from parser import PDFParser
            results = PDFParser().parse_folder(str(tmp_path))

        assert len(results) == 1
        assert "error" in results[0]
