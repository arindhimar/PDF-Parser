"""
conftest.py – Make the project root importable so that
              `from schema import CandidateProfile` works inside tests/.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
