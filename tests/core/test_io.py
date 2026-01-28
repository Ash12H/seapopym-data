import pytest
import pandas as pd
import sys
from pathlib import Path
import tempfile

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.append(str(PROJECT_ROOT / "src"))

from core.io import DataLoader


def test_load_csv():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as tmp:
        tmp.write("col1,col2\n1,2\n3,4")
        tmp_path = tmp.name

    try:
        df = DataLoader.load_csv(tmp_path)
        assert len(df) == 2
        assert "col1" in df.columns
        assert df["col1"].iloc[0] == 1
    finally:
        Path(tmp_path).unlink()
