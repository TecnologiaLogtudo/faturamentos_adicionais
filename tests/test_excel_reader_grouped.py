import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.services.excel_reader import ExcelReader


class ExcelReaderGroupedTreatmentTest(unittest.TestCase):
    def _create_workbook(self, path):
        base = pd.DataFrame(
            [
                ["Senha Ravex", "Tipo de custo", "Nota fiscal", "Transporte"],
                ["123", "Descarga", "NF001", "9001"],
                ["456", "Descarga", "NF002", "9002"],
            ]
        )
        zle = pd.DataFrame(
            {
                "Nº transporte": ["9001", "9002"],
                "Valor Frete": [10.5, 20.25],
                "Centro": ["BA01", "BA01"],
                "Código de imposto": ["", "IT"],
            }
        )
        with pd.ExcelWriter(path, engine="openpyxl") as writer:
            base.to_excel(writer, sheet_name="Base", index=False, header=False)
            zle.to_excel(writer, sheet_name="ZLE", index=False)

    def test_ba_pe_ce_use_grouped_treatment_and_cte_gerado_mapping(self):
        expected_headers = [
            "Senha Ravex",
            "Tipo de custo",
            "Nota fiscal",
            "Nº Transporte",
            "Valor Frete",
            "Tipo Cte",
            "Código de imposto",
            "CTe gerado",
        ]

        with tempfile.TemporaryDirectory() as tmp:
            input_path = Path(tmp) / "entrada.xlsx"
            self._create_workbook(input_path)

            for uf in ("Bahia", "Pernambuco", "Ceará"):
                reader = ExcelReader()
                payload = reader.read(str(input_path), uf=uf)
                mapping = reader.auto_map_columns()

                self.assertEqual(payload["headers"], expected_headers)
                self.assertTrue(Path(payload["file_info"]["full_path"]).exists())
                self.assertEqual(Path(payload["file_info"]["full_path"]).name, "Processado_Agrupado_entrada.xlsx")
                self.assertEqual(mapping["nota_fiscal"], 2)
                self.assertEqual(mapping["tipo_adc"], 1)
                self.assertEqual(mapping["valor_cte"], 4)
                self.assertEqual(mapping["senha_ravex"], 0)
                self.assertEqual(mapping["transporte"], 3)
                self.assertEqual(mapping["cte_output"], 7)


if __name__ == "__main__":
    unittest.main()
