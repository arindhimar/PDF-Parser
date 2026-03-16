"""
TDD Tests for parser.py (PyMuPDFParser)
Tests are written BEFORE implementation (Test-Driven Development).

The PyMuPDF (`fitz.open`) calls are fully mocked so no real PDF
is needed to run the suite, making tests fast and deterministic.

Run with:
    pytest tests/ -v
"""

import os
import pytest
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers – build fake PyMuPDF (fitz) Document objects
# ---------------------------------------------------------------------------

def _make_mock_page(text="Mocked Page Text"):
    """Returns a mock PyMuPDF Page object."""
    mock_page = MagicMock()
    mock_page.get_text.return_value = text
    return mock_page

def _make_mock_document(pages=1, text="Mocked Page Text"):
    """Returns a mock PyMuPDF Document object with a sequence of pages."""
    mock_doc = MagicMock()
    
    # Mocking the iterator behavior for `for page in doc:`
    mock_pages = [_make_mock_page(text) for _ in range(pages)]
    mock_doc.__iter__.return_value = iter(mock_pages)
    mock_doc.__len__.return_value = pages
    
    # Mocking doc as a context manager (with fitz.open(...) as doc:)
    mock_doc.__enter__.return_value = mock_doc
    mock_doc.__exit__.return_value = None
    
    return mock_doc


# ============================================================
# 1. parse_pdf – happy path
# ============================================================

class TestParsePdf:

    def test_parse_pdf_returns_dict(self, tmp_path):
        """parse_pdf() must return a dict."""
        pdf = tmp_path / "resume.pdf"
        pdf.write_bytes(b"%PDF-1.4 fake")

        with patch("parser.fitz.open", return_value=_make_mock_document()):
            from parser import PDFParser
            result = PDFParser().parse_pdf(str(pdf))

        assert isinstance(result, dict)

    def test_parse_pdf_has_required_keys(self, tmp_path):
        """parse_pdf() result must contain 'filename', 'text', 'page_count'."""
        pdf = tmp_path / "resume.pdf"
        pdf.write_bytes(b"%PDF-1.4 fake")

        with patch("parser.fitz.open", return_value=_make_mock_document()):
            from parser import PDFParser
            result = PDFParser().parse_pdf(str(pdf))

        assert "filename"   in result
        assert "text"       in result
        assert "page_count" in result

    def test_parse_pdf_filename_is_basename(self, tmp_path):
        """filename in result must be just the file's basename, not the full path."""
        pdf = tmp_path / "my_resume.pdf"
        pdf.write_bytes(b"%PDF-1.4 fake")

        with patch("parser.fitz.open", return_value=_make_mock_document()):
            from parser import PDFParser
            result = PDFParser().parse_pdf(str(pdf))

        assert result["filename"] == "my_resume.pdf"

    def test_parse_pdf_text_concatenates_pages(self, tmp_path):
        """text key must concatenate the text from all pages."""
        pdf = tmp_path / "resume.pdf"
        pdf.write_bytes(b"%PDF-1.4 fake")

        # Mock a document where page 1 returns "John" and page 2 returns "Doe"
        mock_doc = MagicMock()
        mock_doc.__iter__.return_value = iter([_make_mock_page("John"), _make_mock_page("Doe")])
        mock_doc.__len__.return_value = 2
        mock_doc.__enter__.return_value = mock_doc
        mock_doc.__exit__.return_value = None

        with patch("parser.fitz.open", return_value=mock_doc):
            from parser import PDFParser
            result = PDFParser().parse_pdf(str(pdf))

        assert "John" in result["text"]
        assert "Doe" in result["text"]

    def test_parse_pdf_page_count_matches(self, tmp_path):
        """page_count must equal the number of pages inside the document."""
        pdf = tmp_path / "resume.pdf"
        pdf.write_bytes(b"%PDF-1.4 fake")

        with patch("parser.fitz.open", return_value=_make_mock_document(pages=5)):
            from parser import PDFParser
            result = PDFParser().parse_pdf(str(pdf))

        assert result["page_count"] == 5


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

        with patch("parser.fitz.open", return_value=_make_mock_document()):
            from parser import PDFParser
            results = PDFParser().parse_folder(str(tmp_path))

        assert isinstance(results, list)

    def test_parse_folder_count_matches_pdfs(self, tmp_path):
        """parse_folder() must return exactly one result per PDF (ignores non-PDFs)."""
        for name in ["cv1.pdf", "cv2.pdf", "cv3.pdf"]:
            (tmp_path / name).write_bytes(b"%PDF-1.4")
        (tmp_path / "notes.txt").write_text("ignore me")

        with patch("parser.fitz.open", return_value=_make_mock_document(pages=1)):
            from parser import PDFParser
            results = PDFParser().parse_folder(str(tmp_path))

        assert len(results) == 3, f"Expected 3, got {len(results)}"

    def test_parse_folder_each_result_has_required_keys(self, tmp_path):
        """Every item in parse_folder() results must have filename, text, page_count."""
        for name in ["r1.pdf", "r2.pdf"]:
            (tmp_path / name).write_bytes(b"%PDF-1.4")

        with patch("parser.fitz.open", return_value=_make_mock_document()):
            from parser import PDFParser
            results = PDFParser().parse_folder(str(tmp_path))

        for r in results:
            assert "filename"   in r
            assert "text"       in r
            assert "page_count" in r


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

        with patch("parser.fitz.open", side_effect=Exception("PyMuPDF internal error")):
            from parser import PDFParser
            results = PDFParser().parse_folder(str(tmp_path))

        assert len(results) == 1
        assert "error" in results[0]
