"""
main.py – Quick demo: parse a single PDF using PDFParser.

To parse ALL resumes in Dummy_Resumes/, run:
    python run_all.py
"""

from parser import PDFParser

API_KEY = "llx-"

# Pick any one PDF from Dummy_Resumes to test with
PDF_PATH = "./Dummy_Resumes/Arin Avinash Dhimar.pdf"

parser = PDFParser(api_key=API_KEY)
result = parser.parse_pdf(PDF_PATH)

print("\n=== Full Markdown ===")
print(result["markdown"])

print("\n=== Full Text ===")
print(result["text"])