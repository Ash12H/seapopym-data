import pytest
import pandas as pd
import sys
from pathlib import Path

# Fix import path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.append(str(PROJECT_ROOT / "src"))

from core.units import UnitManager


def test_convert_column():
    df = pd.DataFrame({"temp": [10, 20, 30]})
    # Mock behavior depending on actual implementation,
    # but here assuming 'degC' to 'K' or similar if implemented,
    # or just checking the function structure.
    # Actually, let's test something that should work if Pint is correctly set up.

    # In my implementation, I used:
    # quantity = ureg.Quantity(..., from_unit)
    # converted = quantity.to(to_unit)

    # Let's test m to km
    df["dist"] = [1000, 2000, 3000]
    df_new = UnitManager.convert_column(df, "dist", "m", "km")

    assert df_new["dist"].iloc[0] == 1.0
    assert df_new["dist"].iloc[1] == 2.0
    assert df_new["dist"].iloc[2] == 3.0
