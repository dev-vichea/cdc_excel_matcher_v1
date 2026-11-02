import io
import unittest
from pathlib import Path
import openpyxl

from services.extraction import extract_shipping, extract_cdc
from services.packing import extract_packing, reconcile_invoice_packing
from services.matching import build_results, load_mappings
from services.translation_memory import load_verified_translations
from services.permit_exporter import generate_permit_document
from services.cutstock_updater import (
    detect_period_columns,
    suggest_period_from_date,
    consolidate_deductions,
    apply_deductions_to_cdc_workbook,
)

ROOT = Path(__file__).parent.parent


class TestPermitGeneration(unittest.TestCase):
    def setUp(self):
        self.re26_path = ROOT / 'reference' / 'shipping_work' / '02_import_TK164' / 'supplier_originals' / 'RE2612040-SHIPPING DOCS-28-OCT.xls'
        self.cdc_path = ROOT / 'reference' / 'shipping_work' / '03_cdc_master_and_approval' / 'needs_verification' / 'XIN CAI FU-CDC Master List-2026-CUT STOCK ( QIP # 211-26  ).xlsx'

    def test_re2612040_full_pipeline(self):
        if not self.re26_path.exists() or not self.cdc_path.exists():
            self.skipTest('Reference files not found')

        ship_bytes = self.re26_path.read_bytes()
        cdc_bytes = self.cdc_path.read_bytes()

        # 1. Extraction
        smeta, sitems = extract_shipping(ship_bytes, self.re26_path.name)
        pmeta, pitems = extract_packing(ship_bytes, self.re26_path.name)
        cmeta, citems = extract_cdc(cdc_bytes, self.cdc_path.name)

        self.assertEqual(len(sitems), 10)
        self.assertEqual(len(pitems), 10)
        self.assertEqual(smeta['invoice_no'], 'RE2612040')
        self.assertEqual(smeta['invoice_date'], '2026-10-28')
        self.assertIn('WEALDONE', smeta['supplier'])
        self.assertIn('XIN CAI FU', smeta['consignee'])

        # 2. Packing reconciliation
        pairs, issues = reconcile_invoice_packing(sitems, pitems, smeta, pmeta)
        self.assertEqual(issues, [])
        self.assertEqual(sum(p['packing']['packages'] for p in pairs), 390.0)

        # 3. Matching
        mappings = load_mappings(ROOT / 'data' / 'approved_mappings.json')
        trans = load_verified_translations(ROOT / 'data' / 'verified_translations.sqlite3')
        results = build_results(sitems, citems, mappings, online=False, glossary=trans)
        self.assertEqual(len(results), 10)

        selections = []
        for r in results:
            cand = r['candidates'][0] if r['candidates'] else None
            selections.append({'match': cand, 'decision': 'Approved', 'notes': ''})

        # Verify all 10 matched
        matched = [s['match'] for s in selections if s['match']]
        self.assertEqual(len(matched), 10)

        # 4. Generate Permit Application Document (1-26TKYM164 format)
        # 4a. With Bill of Lading metadata
        from services.bill_extractor import extract_bill
        bill_path = ROOT / 'reference' / 'shipping_work' / '02_import_TK164' / 'transport' / '汇孚390件提单AOTAI FAUXFUR.pdf'
        bill_meta = extract_bill(bill_path.read_bytes(), bill_path.name) if bill_path.exists() else {}

        permit_bytes = generate_permit_document(
            smeta, cmeta, results, selections, pitems, pairs, issues, '211/26',
            bill_meta=bill_meta, auto_discount_kg=False
        )
        wb_permit = openpyxl.load_workbook(io.BytesIO(permit_bytes))
        self.assertIn('INV', wb_permit.sheetnames)
        self.assertIn('PL', wb_permit.sheetnames)

        inv = wb_permit['INV']
        pl = wb_permit['PL']

        self.assertEqual(inv['A1'].value, 'WEALDONE LIMITED')
        self.assertEqual(inv['B8'].value, 'RE2612040')
        # Bill date takes priority over current date!
        self.assertEqual(inv['G8'].value, '29-Oct-2026')
        self.assertEqual(inv['B9'].value, 'BY TRUCK')
        self.assertEqual(inv['B10'].value, 'JIANGSU, CHINA TO PHNOM PENH, CAMBODIA')
        self.assertEqual(pl['B10'].value, 'JIANGSU, CHINA TO PHNOM PENH, CAMBODIA')

        # Check Consignee address split across rows 13 and 14
        self.assertEqual(inv.cell(12, 2).value, 'XIN CAI FU (CAMBODIA) CO., LTD.')
        self.assertEqual(inv.cell(13, 2).value, 'PHUM DOMNAK TROYEOUNG, SANGKAT CHOM CHAO II,')
        self.assertEqual(inv.cell(14, 2).value, 'KHAN POR SEN CHEY PHNOM PENH,')
        self.assertEqual(inv.cell(15, 2).value, 'KINGDOM OF CAMBODIA.')
        self.assertEqual(inv.cell(16, 2).value, 'SHIPPING PERSON:')
        self.assertEqual(inv.cell(17, 2).value, 'VAT No : LO01-902303477')

        self.assertEqual(pl.cell(12, 2).value, 'XIN CAI FU (CAMBODIA) CO., LTD.')
        self.assertEqual(pl.cell(13, 2).value, 'PHUM DOMNAK TROYEOUNG, SANGKAT CHOM CHAO II,')
        self.assertEqual(pl.cell(14, 2).value, 'KHAN POR SEN CHEY PHNOM PENH,')
        self.assertEqual(pl.cell(15, 2).value, 'KINGDOM OF CAMBODIA.')
        self.assertEqual(pl.cell(16, 2).value, 'SHIPPING PERSON:')
        self.assertEqual(pl.cell(17, 2).value, 'VAT No : LO01-902303477')

        self.assertEqual(inv['A23'].value, '211/26')
        self.assertEqual(inv['B23'].value, 'II - RAW MATERIALS AND ACCESSORIES')

        # Check items and formulas (sorted smallest to largest by CDC No: 4, 13, 14, 17, 26, 28, 29, 31, 61, 86)
        # On INV: Items start at row 24
        self.assertEqual(inv.cell(24, 1).value, 4)  # Row 24 is CDC #4: Knitted fabric
        self.assertEqual(inv.cell(24, 2).value, 'KNITTED FABRIC')
        self.assertEqual(inv.cell(24, 4).value, 6406)
        self.assertEqual(inv.cell(24, 5).value, 'Kg')
        self.assertEqual(inv.cell(24, 5).alignment.horizontal, 'left')
        self.assertEqual(inv.cell(24, 6).value, 4.5)  # Matches CDC Master List unit price
        self.assertEqual(inv.cell(24, 7).value, '=D24*F24')

        self.assertEqual(pl['B8'].value, 'RE2612040')  # No raw =INV!B8 formula!
        self.assertEqual(pl['H8'].value, '29-Oct-2026')
        self.assertEqual(pl.cell(43, 2).value, '1X45 HQ PART OF CFS/CFS')

        # On PL: Items start at row 24 (row 23 is Category header)
        self.assertEqual(pl.cell(24, 1).value, 284)  # Row 24 is Knitted fabric (284 pkgs)
        self.assertEqual(pl.cell(24, 2).value, 'KNITTED FABRIC')

        self.assertEqual(inv.cell(25, 1).value, 13) # Row 25 is CDC #13: Ribbon
        self.assertEqual(inv.cell(25, 2).value, 'RIBBON')
        self.assertEqual(pl.cell(25, 1).value, 1)   # Ribbon has 1 pkg on PL (row 25)
        self.assertEqual(pl.cell(25, 2).value, 'RIBBON')
        self.assertEqual(pl.cell(25, 6).alignment.horizontal, 'left')

        # Row 29 on INV and PL is CDC #28: Elastic band (converted qty: 407 Gross, 36 pkgs)
        self.assertEqual(inv.cell(29, 1).value, 28)
        self.assertEqual(inv.cell(29, 2).value, 'ELASTIC BAND')
        self.assertEqual(inv.cell(29, 4).value, 407)
        self.assertEqual(inv.cell(29, 5).value, 'Gross')
        self.assertEqual(inv.cell(29, 6).value, 3.0)  # Matches CDC Master List unit price ($3.00, not invoice-derived $8.66)
        self.assertEqual(inv.cell(29, 7).value, '=D29*F29')

        self.assertEqual(pl.cell(29, 1).value, 36)
        self.assertEqual(pl.cell(29, 2).value, 'ELASTIC BAND')
        self.assertEqual(pl.cell(29, 5).value, 407)
        self.assertEqual(pl.cell(29, 6).value, 'Gross')

        self.assertEqual(inv.cell(33, 1).value, 86) # Row 33 is CDC #86: Elastic string
        self.assertEqual(inv.cell(40, 7).value, '=SUM(G24:G33)')
        self.assertEqual(inv.cell(43, 5).value, 'WEALDONE LIMITED')

        self.assertEqual(pl.cell(40, 1).value, '=SUM(A24:A33)')
        self.assertEqual(pl.cell(43, 6).value, 'WEALDONE LIMITED')

        # 5. Cut-Stock Deduction
        periods = detect_period_columns(cdc_bytes)
        sug_col = suggest_period_from_date(smeta['invoice_date'], periods)
        self.assertEqual(sug_col, 14)  # OCT 2026 is col 14 (N)

        consolidation = consolidate_deductions(results, selections)
        self.assertEqual(len(consolidation['consolidated']), 10)
        self.assertFalse(consolidation['has_exceeded'])

        # Verify Elastic band deduction is 407 Gross (not 58724 meters)
        elastic_cons = next(c for c in consolidation['consolidated'] if str(c['cdc_serial']) in ('28', 28))
        self.assertEqual(elastic_cons['deduct_qty'], 407.0)
        self.assertEqual(elastic_cons['cdc_unit'], 'Gross')

        deducted_bytes = apply_deductions_to_cdc_workbook(
            cdc_bytes,
            consolidation['consolidated'],
            target_col_idx=sug_col,
            sheet_name='Sheet1',
            add_to_existing=True
        )
        self.assertGreater(len(deducted_bytes), 1000)

        # Check deducted value in cell N104
        wb_deducted = openpyxl.load_workbook(io.BytesIO(deducted_bytes), data_only=True)
        ws_d = wb_deducted['Sheet1']
        self.assertEqual(ws_d.cell(104, 14).value, 6406.0)

    def test_permit_generation_same_cdc_consolidation(self):
        """Verify that items with the same CDC No (same CDC master entry) are combined into a single permit row with summed quantity."""
        from services.permit_exporter import consolidate_permit_items, generate_permit_document

        cdc_match_1 = {
            'serial': '1',
            'row': 10,
            'sheet': 'Sheet1',
            'description': 'Woven fabric',
            'unit': 'Kg',
            'unit_price': 3.50,
            'unit_compatible': True,
        }
        cdc_match_5 = {
            'serial': '5',
            'row': 15,
            'sheet': 'Sheet1',
            'description': 'Inter lining fabric',
            'unit': 'Yd',
            'unit_price': 0.25,
            'unit_compatible': True,
        }

        results = [
            {'row': 1, 'chinese': '全棉梭织布', 'english_provided': 'WOVEN FABRIC (100%cotton)', 'qty': 12724.0, 'unit': 'kg', 'unit_price': 3.50, 'total': 44534.0, 'hs_code': '5208'},
            {'row': 2, 'chinese': '涤棉梭织布', 'english_provided': 'WOVEN FABRIC (67%polyester 33%cotton)', 'qty': 12046.0, 'unit': 'kg', 'unit_price': 3.50, 'total': 42161.0, 'hs_code': '5513'},
            {'row': 3, 'chinese': '粘合衬布', 'english_provided': 'INTER LINING FABRIC (100%polyester)', 'qty': 1679.8, 'unit': 'Yd', 'unit_price': 0.25, 'total': 419.95, 'hs_code': '5903'},
        ]
        selections = [
            {'match': cdc_match_1, 'decision': 'Approved', 'notes': ''},
            {'match': cdc_match_1, 'decision': 'Approved', 'notes': ''},
            {'match': cdc_match_5, 'decision': 'Approved', 'notes': ''},
        ]
        pairs = [
            {'invoice': results[0], 'packing': {'sheet': 'PL', 'row': 1, 'packages': 260, 'net_weight': 12724.0, 'gross_weight': 12800.0}},
            {'invoice': results[1], 'packing': {'sheet': 'PL', 'row': 2, 'packages': 263, 'net_weight': 12046.0, 'gross_weight': 12128.0}},
            {'invoice': results[2], 'packing': {'sheet': 'PL', 'row': 3, 'packages': 8, 'net_weight': 185.0, 'gross_weight': 189.0}},
        ]

        # 1. Test consolidate_permit_items with auto_discount_kg=True (1 kg per package tare deduction)
        consolidated = consolidate_permit_items(results, selections, pairs, auto_discount_kg=True)
        self.assertEqual(len(consolidated), 2)

        # First consolidated item is CDC #1:
        # Original: qty=24,770, pkgs=523, nw=24,770.00, gw=24,928.00
        # Auto-discount for unit Kg: -523 kg tare (1 kg per package)
        # Result: qty=24,247, nw=24,247.00
        self.assertEqual(consolidated[0]['cdc_num'], 1)
        self.assertEqual(consolidated[0]['desc'], 'WOVEN FABRIC')
        self.assertEqual(consolidated[0]['qty'], 24247)  # 24,770 - 523
        self.assertEqual(consolidated[0]['unit'], 'Kg')
        self.assertEqual(consolidated[0]['price'], 3.50)
        self.assertEqual(consolidated[0]['pkgs'], 523)  # 260 + 263
        self.assertEqual(consolidated[0]['nw'], 24247.00)  # 24,770.00 - 523
        self.assertEqual(consolidated[0]['gw'], 24928.00)  # Gross weight untouched
        self.assertEqual(consolidated[0]['items_count'], 2)
        self.assertTrue(consolidated[0]['is_kg_discounted'])

        # Second consolidated item is CDC #5 (unit Yd):
        # Unit is not Kg, so no discount is deducted!
        self.assertEqual(consolidated[1]['cdc_num'], 5)
        self.assertEqual(consolidated[1]['desc'], 'INTER LINING FABRIC')
        self.assertEqual(consolidated[1]['qty'], 1679.8)
        self.assertEqual(consolidated[1]['unit'], 'Yd')
        self.assertEqual(consolidated[1]['price'], 0.25)
        self.assertEqual(consolidated[1]['pkgs'], 8)
        self.assertEqual(consolidated[1]['nw'], 185.0)
        self.assertEqual(consolidated[1]['gw'], 189.0)
        self.assertEqual(consolidated[1]['items_count'], 1)
        self.assertFalse(consolidated[1]['is_kg_discounted'])

        # 2. Test generate_permit_document Excel export (with auto_discount_kg=True)
        shipmeta = {
            'invoice_no': 'TEST-INV-001',
            'supplier': 'SUPPLIER CO., LTD.',
            'consignee': 'XIN CAI FU (CAMBODIA) CO., LTD.',
            'invoice_date': '2026-11-02',
        }
        cdcmeta = {'company': 'XIN CAI FU', 'qip': '211/26', 'sheet': 'Sheet1'}

        permit_bytes = generate_permit_document(
            shipmeta, cdcmeta, results, selections,
            [p['packing'] for p in pairs], pairs, [], '211/26',
            auto_discount_kg=True
        )
        wb = openpyxl.load_workbook(io.BytesIO(permit_bytes))
        inv = wb['INV']
        pl = wb['PL']

        # Items on INV start at row 24
        # Row 24: CDC #1 combined & discounted
        self.assertEqual(inv.cell(24, 1).value, 1)
        self.assertEqual(inv.cell(24, 2).value, 'WOVEN FABRIC')
        self.assertEqual(inv.cell(24, 4).value, 24247)  # 24,770 - 523
        self.assertEqual(inv.cell(24, 5).value, 'Kg')
        self.assertEqual(inv.cell(24, 6).value, 3.50)
        self.assertEqual(inv.cell(24, 7).value, '=D24*F24')

        # Row 25: CDC #5
        self.assertEqual(inv.cell(25, 1).value, 5)
        self.assertEqual(inv.cell(25, 2).value, 'INTER LINING FABRIC')
        self.assertEqual(inv.cell(25, 4).value, 1679.8)
        self.assertEqual(inv.cell(25, 5).value, 'Yd')
        self.assertEqual(inv.cell(25, 6).value, 0.25)
        self.assertEqual(inv.cell(25, 7).value, '=D25*F25')

        # Row 26: cleared
        self.assertIsNone(inv.cell(26, 1).value)
        self.assertIsNone(inv.cell(26, 2).value)

        # Total row formula sums row 24 to 25
        self.assertEqual(inv.cell(40, 7).value, '=SUM(G24:G25)')

        # PL sheet:
        # Row 24: CDC #1 combined packages and discounted net weight
        self.assertEqual(pl.cell(24, 1).value, 523)  # 260 + 263 packages
        self.assertEqual(pl.cell(24, 2).value, 'WOVEN FABRIC')
        self.assertEqual(pl.cell(24, 5).value, 24247)  # discounted quantity in PL
        self.assertEqual(pl.cell(24, 6).value, 'Kg')
        self.assertEqual(pl.cell(24, 7).value, 24247.0)  # 24,770 - 523 discounted NW
        self.assertEqual(pl.cell(24, 8).value, 24928.0)  # untouched GW

        # Row 25: CDC #5
        self.assertEqual(pl.cell(25, 1).value, 8)
        self.assertEqual(pl.cell(25, 2).value, 'INTER LINING FABRIC')
        self.assertEqual(pl.cell(25, 5).value, 1679.8)
        self.assertEqual(pl.cell(25, 6).value, 'Yd')
        self.assertEqual(pl.cell(25, 7).value, 185.0)
        self.assertEqual(pl.cell(25, 8).value, 189.0)

        # Row 26: cleared
        self.assertIsNone(pl.cell(26, 1).value)

        # PL total row formulas sum row 24 to 25
        self.assertEqual(pl.cell(40, 1).value, '=SUM(A24:A25)')
        self.assertEqual(pl.cell(40, 7).value, '=SUM(G24:G25)')
        self.assertEqual(pl.cell(40, 8).value, '=SUM(H24:H25)')


if __name__ == '__main__':
    unittest.main()
