import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.automation.nota_fiscal.commons import NotaFiscalCommonsMixin


class CteComplementoNormalizationTest(unittest.TestCase):
    def setUp(self):
        self.commons = NotaFiscalCommonsMixin()

    def test_normalizes_year_plus_zero_sequence(self):
        cases = {
            "202600000001198": "1198",
            "2026000012345": "12345",
            "202601198": "202601198",
            "1198": "1198",
            "": "",
            None: "",
        }

        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(
                    self.commons._normalize_cte_complemento_search(raw),
                    expected,
                )


if __name__ == "__main__":
    unittest.main()
