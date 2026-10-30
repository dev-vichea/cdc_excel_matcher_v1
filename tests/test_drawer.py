import io
import unittest
from pathlib import Path
import pandas as pd
import openpyxl.utils

ROOT = Path(__file__).parent.parent


class TestDrawerPreview(unittest.TestCase):
    def test_preview_supplier_xls(self):
        xls_path = ROOT / 'examples' / 'shipping_TK164.xls'
        self.assertTrue(xls_path.exists())
        xl = pd.ExcelFile(io.BytesIO(xls_path.read_bytes()))
        self.assertIn('invoice', xl.sheet_names)
        self.assertIn('PackingList', xl.sheet_names)

        df = pd.read_excel(xl, sheet_name='invoice', header=None, dtype=str).fillna('')
        df.columns = [openpyxl.utils.get_column_letter(i + 1) for i in range(len(df.columns))]
        df.index = [i + 1 for i in range(len(df))]

        self.assertGreater(len(df), 20)
        self.assertIn('A', df.columns)
        self.assertIn('G', df.columns)
        self.assertEqual(df.index[0], 1)

    def test_preview_cdc_xlsx(self):
        xlsx_path = ROOT / 'examples' / 'cdc_master_2025.xlsx'
        self.assertTrue(xlsx_path.exists())
        xl = pd.ExcelFile(io.BytesIO(xlsx_path.read_bytes()))
        sheet = xl.sheet_names[0]

        df = pd.read_excel(xl, sheet_name=sheet, header=None, dtype=str).fillna('')
        df.columns = [openpyxl.utils.get_column_letter(i + 1) for i in range(len(df.columns))]
        df.index = [i + 1 for i in range(len(df))]

        self.assertGreater(len(df), 50)
        self.assertEqual(df.index[0], 1)
        self.assertIn('A', df.columns)


if __name__ == '__main__':
    unittest.main()
