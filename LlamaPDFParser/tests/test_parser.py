"""
TDD Tests for parser.py
Tests are written BEFORE implementation (Test-Driven Development).

Run with:
    pytest tests/ -v
"""

import os
import pytest
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers – build a fake result object that mimics the LlamaCloud response
# ---------------------------------------------------------------------------

def _make_mock_result(markdown="# Resume\nSome content", text="Resume Some content"):
    result = MagicMock()
    result.markdown_full = markdown
    result.text_full = text
    return result


def _make_mock_client(markdown="# Resume\nSome content", text="Resume Some content"):
    """Return a mock AsyncLlamaCloud client with preset responses."""
    mock_result = _make_mock_result(markdown, text)

    mock_file_obj = MagicMock()
    mock_file_obj.id = "fake-file-id-123"

    mock_client = MagicMock()
    mock_client.files.create.return_value = mock_file_obj
    mock_client.parsing.parse.return_value = mock_result
    return mock_client


# ============================================================
# 1. parse_pdf – happy path
# ============================================================

class TestParsePdf:

    def test_parse_pdf_returns_dict(self, tmp_path):
        """parse_pdf() must return a dict with markdown, text, and filename keys."""
        pdf_file = tmp_path / "sample.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 fake content")

        mock_client = _make_mock_client()
        with patch("parser.LlamaCloud", return_value=mock_client):
            from parser import PDFParser
            p = PDFParser(api_key="test-key")
            result = p.parse_pdf(str(pdf_file))

        assert isinstance(result, dict), "Result must be a dict"
        assert "markdown" in result, "Result must have a 'markdown' key"
        assert "text" in result, "Result must have a 'text' key"
        assert "filename" in result, "Result must have a 'filename' key"

    def test_parse_pdf_filename_matches(self, tmp_path):
        """filename in result must match the uploaded file's basename."""
        pdf_file = tmp_path / "my_resume.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 fake content")

        mock_client = _make_mock_client()
        with patch("parser.LlamaCloud", return_value=mock_client):
            from parser import PDFParser
            p = PDFParser(api_key="test-key")
            result = p.parse_pdf(str(pdf_file))

        assert result["filename"] == "my_resume.pdf"

    def test_parse_pdf_markdown_content(self, tmp_path):
        """markdown key must contain the content returned by the API."""
        pdf_file = tmp_path / "resume.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 fake content")

        mock_client = _make_mock_client(markdown="# John Doe\nSoftware Engineer")
        with patch("parser.LlamaCloud", return_value=mock_client):
            from parser import PDFParser
            p = PDFParser(api_key="test-key")
            result = p.parse_pdf(str(pdf_file))

        assert "John Doe" in result["markdown"]

    def test_parse_pdf_text_content(self, tmp_path):
        """text key must contain the plain-text content returned by the API."""
        pdf_file = tmp_path / "resume.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 fake content")

        mock_client = _make_mock_client(text="John Doe Software Engineer")
        with patch("parser.LlamaCloud", return_value=mock_client):
            from parser import PDFParser
            p = PDFParser(api_key="test-key")
            result = p.parse_pdf(str(pdf_file))

        assert "John Doe" in result["text"]


# ============================================================
# 2. parse_pdf – error cases
# ============================================================

class TestParsePdfErrors:

    def test_parse_pdf_file_not_found(self):
        """parse_pdf() must raise FileNotFoundError for a path that doesn't exist."""
        with patch("parser.LlamaCloud", return_value=_make_mock_client()):
            from parser import PDFParser
            p = PDFParser(api_key="test-key")
            with pytest.raises(FileNotFoundError):
                p.parse_pdf("/non/existent/path/resume.pdf")

    def test_parse_pdf_non_pdf_raises_value_error(self, tmp_path):
        """parse_pdf() must raise ValueError when given a non-.pdf file."""
        txt_file = tmp_path / "resume.txt"
        txt_file.write_text("This is not a PDF")

        with patch("parser.LlamaCloud", return_value=_make_mock_client()):
            from parser import PDFParser
            p = PDFParser(api_key="test-key")
            with pytest.raises(ValueError, match="must be a PDF"):
                p.parse_pdf(str(txt_file))


# ============================================================
# 3. parse_folder – happy path
# ============================================================

class TestParseFolder:

    def test_parse_folder_returns_list(self, tmp_path):
        """parse_folder() must return a list."""
        (tmp_path / "a.pdf").write_bytes(b"%PDF-1.4")
        (tmp_path / "b.pdf").write_bytes(b"%PDF-1.4")

        mock_client = _make_mock_client()
        with patch("parser.LlamaCloud", return_value=mock_client):
            from parser import PDFParser
            p = PDFParser(api_key="test-key")
            results = p.parse_folder(str(tmp_path))

        assert isinstance(results, list), "parse_folder must return a list"

    def test_parse_folder_count_matches_pdfs(self, tmp_path):
        """parse_folder() must return one result per PDF in the folder."""
        for name in ["cv1.pdf", "cv2.pdf", "cv3.pdf"]:
            (tmp_path / name).write_bytes(b"%PDF-1.4")
        # non-pdf should be ignored
        (tmp_path / "notes.txt").write_text("ignore me")

        mock_client = _make_mock_client()
        with patch("parser.LlamaCloud", return_value=mock_client):
            from parser import PDFParser
            p = PDFParser(api_key="test-key")
            results = p.parse_folder(str(tmp_path))

        assert len(results) == 3, f"Expected 3 results, got {len(results)}"

    def test_parse_folder_each_result_has_required_keys(self, tmp_path):
        """Every result from parse_folder must contain markdown, text, filename."""
        (tmp_path / "r1.pdf").write_bytes(b"%PDF-1.4")
        (tmp_path / "r2.pdf").write_bytes(b"%PDF-1.4")

        mock_client = _make_mock_client()
        with patch("parser.LlamaCloud", return_value=mock_client):
            from parser import PDFParser
            p = PDFParser(api_key="test-key")
            results = p.parse_folder(str(tmp_path))

        for r in results:
            assert "markdown" in r
            assert "text" in r
            assert "filename" in r


# ============================================================
# 4. parse_folder – error cases
# ============================================================

class TestParseFolderErrors:

    def test_parse_folder_missing_folder_raises(self):
        """parse_folder() must raise FileNotFoundError for a folder that doesn't exist."""
        with patch("parser.LlamaCloud", return_value=_make_mock_client()):
            from parser import PDFParser
            p = PDFParser(api_key="test-key")
            with pytest.raises(FileNotFoundError):
                p.parse_folder("/no/such/folder")

    def test_parse_folder_empty_folder_returns_empty_list(self, tmp_path):
        """parse_folder() on an empty folder must return an empty list (not raise)."""
        with patch("parser.LlamaCloud", return_value=_make_mock_client()):
            from parser import PDFParser
            p = PDFParser(api_key="test-key")
            results = p.parse_folder(str(tmp_path))

        assert results == [], "Empty folder should return empty list"
