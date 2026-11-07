import unittest
from pathlib import Path
from services.bill_extractor import extract_bill, reconcile_bill_and_shipping, classify_invoice_items

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

    def test_reconcile_garment_accessories_3_plus_rule(self):
        """When 3 or more accessories exist, verify they match GARMENT ACCESSORIES on B/L."""
        bill_meta = {
            'bl_no': 'RCLY261030704',
            'shipping_mode': 'BY TRUCK',
            'shipper': 'WEALDONE LIMITED',
            'consignee': 'XIN CAI FU (CAMBODIA) CO., LTD.',
            'vat': 'L001-902303477',
            'packages': 390,
            'gross_weight': 9529.0,
            'volume': 52.8,
            'descriptions': ['KNITTED FABRIC AND GARMENT ACCESSORIES'],
            'raw_text': '390PACKAGES\nKNITTED FABRIC AND GARMENT ACCESSORIES\n9529.00KGS\n52.8CBM'
        }
        shipmeta = {
            'supplier': 'WEALDONE LIMITED',
            'consignee': 'XIN CAI FU (CAMBODIA) CO., LTD.',
            'shipping_mode': 'BY TRUCK',
            'vat': 'L001-902303477'
        }
        packingmeta = {
            'printed_totals': {'packages': 390, 'gross_weight': 9529.0, 'volume': 52.8}
        }
        invoice_items = [
            {'chinese': 'KNITTED FABRIC（78%polyester 14%viscose 8%elastane）', 'qty': 6406.0, 'unit': 'kg'},
            {'chinese': 'PLASTIC STOPPER', 'qty': 518.0, 'unit': 'Gross'},
            {'chinese': 'EYELET', 'qty': 1201.0, 'unit': 'Gross'},
            {'chinese': 'ELASTIC STRING', 'qty': 141600.0, 'unit': 'm'},
            {'chinese': 'RIBBON', 'qty': 5905.0, 'unit': 'Yd'},
            {'chinese': 'DRAWSTRING', 'qty': 284.0, 'unit': 'kg'},
            {'chinese': 'ELASTIC BAND', 'qty': 58724.0, 'unit': 'm'},
            {'chinese': 'MAIN LABEL', 'qty': 2113.0, 'unit': 'Doz'},
            {'chinese': 'CARE LABEL', 'qty': 2113.0, 'unit': 'Doz'},
            {'chinese': 'METAL ZIPPER', 'qty': 2120.0, 'unit': 'Doz'},
        ]

        recon = reconcile_bill_and_shipping(bill_meta, shipmeta, packingmeta, invoice_items)
        self.assertTrue(recon['is_fully_matched'])
        self.assertTrue(recon['acc_rule_applied'])
        self.assertEqual(recon['accessories_count'], 9)
        self.assertEqual(recon['fabrics_count'], 1)

    def test_reconcile_fabrics_only(self):
        """When only fabrics exist, verify no accessories rule is triggered and fabrics match."""
        bill_meta = {
            'bl_no': 'OOLU2341852380',
            'shipping_mode': 'BY SEA',
            'shipper': 'WEALDONE LIMITED',
            'consignee': 'XIN CAI FU (CAMBODIA) CO., LTD.',
            'vat': 'L001-902303477',
            'packages': 504,
            'gross_weight': 17024.9,
            'volume': 67.5,
            'descriptions': ['KNITTED FABRIC', 'WOVEN FABRIC', 'INTER LINING FABRIC'],
            'raw_text': '504 PACKAGE 17024.9 67.5 KNITTED FABRIC WOVEN FABRIC INTER LINING FABRIC'
        }
        shipmeta = {
            'supplier': 'WEALDONE LIMITED',
            'consignee': 'XIN CAI FU (CAMBODIA) CO., LTD.',
            'shipping_mode': 'BY SEA',
            'vat': 'L001-902303477'
        }
        packingmeta = {
            'printed_totals': {'packages': 504, 'gross_weight': 17024.9, 'volume': 67.5}
        }
        invoice_items = [
            {'chinese': 'WOVEN FABRIC（100%cotton）', 'qty': 4570.0, 'unit': 'kg'},
            {'chinese': 'WOVEN FABRIC（100%cotton）', 'qty': 5835.0, 'unit': 'kg'},
            {'chinese': 'KNITTED FABRIC（78%polyester 14%viscose 8%elastane）', 'qty': 5752.7, 'unit': 'kg'},
            {'chinese': 'INTER LINING FABRIC（100%polyester）', 'qty': 2168.0, 'unit': 'Yd'},
        ]

        recon = reconcile_bill_and_shipping(bill_meta, shipmeta, packingmeta, invoice_items)
        self.assertTrue(recon['is_fully_matched'])
        self.assertFalse(recon['acc_rule_applied'])
        self.assertEqual(recon['accessories_count'], 0)
        self.assertEqual(recon['fabrics_count'], 3)

    def test_reconcile_package_and_weight_mismatch(self):
        """Detect and flag mismatches in packages or gross weight."""
        bill_meta = {
            'bl_no': 'OOLU2341852380',
            'shipping_mode': 'BY SEA',
            'packages': 500,  # Mismatch: 500 vs 504
            'gross_weight': 17000.0,  # Mismatch
            'volume': 67.5,
            'descriptions': ['WOVEN FABRIC'],
            'raw_text': 'WOVEN FABRIC'
        }
        shipmeta = {'shipping_mode': 'BY SEA'}
        packingmeta = {'printed_totals': {'packages': 504, 'gross_weight': 17024.9, 'volume': 67.5}}
        invoice_items = [{'chinese': 'WOVEN FABRIC', 'qty': 100.0, 'unit': 'kg'}]

        recon = reconcile_bill_and_shipping(bill_meta, shipmeta, packingmeta, invoice_items)
        self.assertFalse(recon['is_fully_matched'])
        self.assertEqual(recon['overall_status'], 'MISMATCH')
        statuses = {c['item']: c['status'] for c in recon['checklist']}
        self.assertEqual(statuses['Total Packages'], 'MISMATCH')
        self.assertEqual(statuses['Gross Weight (KGS)'], 'MISMATCH')


if __name__ == '__main__':
    unittest.main()
