"""
conftest.py – Make the project root importable so that
              `from parser import PDFParser` works inside tests/.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
