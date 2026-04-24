"""Test configuration: make scripts/ + scripts/scrapers importable."""
import sys
import pathlib

# Make scripts/ + scripts/scrapers importable from tests
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scrapers"))
