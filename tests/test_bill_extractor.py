import unittest
from pathlib import Path
from services.bill_extractor import extract_bill

ROOT = Path(__file__).parent.parent


class TestBillExtractor(unittest.TestCase):
    def setUp(self):
        self.transport_dir = ROOT / 'reference' / 'shipping_work' / '02_import_TK164' / 'transport'

    def test_extract_truck_bill_wealdone(self):
        pdf_path = self.transport_dir / '汇孚390件提单AOTAI FAUXFUR.pdf'
        if not pdf_path.exists():
            self.skipTest('Sample bill PDF not found')

        res = extract_bill(pdf_path.read_bytes(), pdf_path.name)
        self.assertTrue(res['has_bill'])
        self.assertEqual(res['issue_date'], '29-Oct-2026')
        self.assertEqual(res['bl_no'], 'RCLY261030704')
        self.assertEqual(res['shipping_mode'], 'BY TRUCK')
        self.assertEqual(res['packages'], 390)
        self.assertEqual(res['gross_weight'], 9529.0)
        self.assertEqual(res['volume'], 52.8)
        self.assertIn('WEALDONE', res['shipper'])
        self.assertIn('XIN CAI FU', res['consignee'])
        self.assertIn('1X45 HQ', res['container_seal'])

    def test_extract_sitc_bill(self):
        pdf_path = self.transport_dir / 'SITPSHSVA11652-SKH26IM10062.pdf'
        if not pdf_path.exists():
            self.skipTest('SITC bill PDF not found')

        res = extract_bill(pdf_path.read_bytes(), pdf_path.name)
        self.assertTrue(res['has_bill'])
        self.assertEqual(res['issue_date'], '09-Oct-2026')
        self.assertEqual(res['bl_no'], 'SITPSHSVA11652')
        self.assertEqual(res['shipping_mode'], 'BY SEA')

    def test_extract_empty_or_invalid(self):
        res = extract_bill(b'', 'empty.pdf')
        self.assertFalse(res['has_bill'])
        self.assertEqual(res['issue_date'], '')


if __name__ == '__main__':
    unittest.main()
