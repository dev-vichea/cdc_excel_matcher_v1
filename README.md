# Shipping workspace + CDC Excel matcher

A standalone **Python + Streamlit** prototype for import/export shipment tracking, CDC item matching, and monthly cut-stock in-place updates. The shipping workspace records companies, shipment details, document attachments, and dated events in local SQLite. The CDC matcher reads a supplier's Chinese `.xls`/`.xlsx` invoice and packing list, suggests CDC Master List matches, updates monthly cut-stock columns while preserving 100% of the original Excel layout and formulas, and exports independent draft Excel reports. Source workbooks are **never overwritten**.

## Import workflow UI demo

`ui_demo/` contains a separate HTML/CSS/JavaScript mockup for the proposed workflow: Imports register → Create import (document upload or manual entry; CDC or general) → saved import detail → item review in Items & CDC (or Items). The detail also has Invoice, Packing list, Permit application, Shipping docs, Customs, Transport, and Costs tabs. The permit panel shows an INV/PL Excel draft and a reviewed PDF option; these buttons are UI examples only.

Run it locally:

```bash
python3 -m http.server 8765 --directory ui_demo
```

Open `http://localhost:8765`. The three fictional starter imports include labeled sample invoice and packing item lines. Choose **Import supplier Excel** to upload a `.xls`/`.xlsx` workbook, including one with both `invoice` and `PackingList` sheets. The create flow checks register fields and saves a draft. In the saved import, **Overview → Review items** opens **Items & CDC** (or **Items** for general imports). Clicking a line opens a panel with invoice and packing values side by side; reviewed description, quantity, decision, and note are stored separately from the supplier values. Manual drafts can add lines there. The Invoice and Packing list tabs show structured source details and offer **View original**. The example at `examples/shipping_TK164.xls` exercises the upload path. The parser targets this supplier layout, so unfamiliar layouts can leave fields missing and flagged for review. Files, records, and item reviews stay in browser memory and disappear on refresh. CDC matching, permit export, SQLite saving, and submission remain demo controls.

The **CDC master list** page follows the company selected in the sidebar. Year tabs show that company's active list and a searchable table of every item; there is no cross-company version table. The upload action is secondary. It reads supported 2025 quarterly, 2026 application, and 2026 cut-stock workbooks, showing the detected company, QIP/CIB reference, and item count. An internal review requires the company to match the workbook and an approval document reference before a version can be marked verified. A CDC import links to an exact verified version; if none exists, staff can still save an intake draft while CDC candidates and permit preparation remain unavailable. The seeded Tonle 2025 and 2026 lists are fictional demo presets. Verification and balances are browser-only simulations, not official approval or stock deduction.

## Shipping workspace

Open the app and choose **Shipments** in the sidebar. The workspace starts with one XIN CAI FU import shipment, 26TKYM164, seeded from the copied 2026 import register. Its recorded ETAs are plans; the source register has no actual factory arrival date. The starter record links five local reference documents. The shipping database lives at `data/shipping.sqlite3`; new uploads are stored under `data/shipping_uploads/`. Both are excluded from Git.

Use **Create shipment** for any import or export, then record transport details, attach documents, and add dated events with a named source. The checklist indicates whether a document is attached, not whether it has been verified or submitted. The app does not submit customs documents, query a carrier or port, or deduct CDC stock.

Choose **CDC matcher** in the sidebar for the existing invoice/packing and CDC review tool.

## Installation (Windows / macOS)

Install Python 3.10+ and open a terminal in the unzipped project folder.

```bash
python -m venv .venv
```

Activate the environment:
- Windows PowerShell: `.venv\Scripts\Activate.ps1`
- macOS Terminal: `source .venv/bin/activate`

Then:

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

To use optional online translation (not necessary for the supplied invoice):

```bash
pip install deep-translator
```

Then enable **Try online Chinese translation** in the sidebar. This sends Chinese text to a third-party provider; leave it disabled for confidential shipping information.

## Run with supplied example documents

1. Upload `examples/shipping_TK164.xls` as Shipping Invoice.
2. Upload `examples/cdc_master_2025.xlsx` as CDC Master List.
3. Click **Extract & match items**.
4. Check the original Chinese descriptions, invoice English descriptions, quantities, units, ranked CDC candidates, and invoice/CDC company discrepancy.
5. Choose a candidate or **No match**, set review outcomes, and write notes.
6. Download **CDC_Matching_Review_26TKYM164.xlsx**.
7. In **Deduct & Update CDC Master Cut-Stock Excel**, choose the target month or quarter (e.g. `SEP 2026` or `ត្រីមាសទី១/២៥`). Review the consolidated items and quota balance table, then click **Download Updated CDC Master List (.xlsx)**. This keeps 100% of the original layout, styles, Khmer headers, and active Excel formulas intact while populating the exact monthly deduction.

When the supplier workbook includes a packing-list sheet, the app compares its item descriptions, HS codes, quantities, units, company, and printed totals with the invoice. With a company-matching CDC master list and no packing differences, the app also offers a two-sheet **permit-format INV + PL draft**. Enter a confirmed QIP/CIB reference, review the CDC candidates, and download the new draft. The included 2025 CDC example belongs to KING SG, so the permit-format download is unavailable for that mismatched example.

For a new Chinese shipping term, edit **English term for matching** and check the updated suggestions. After verifying its meaning, click **Save verified translation for future shipping files**. The exact Chinese term and your English correction are stored in `data/verified_translations.sqlite3` and reused on later uploads. Existing entries from `data/verified_translations.json` are copied into SQLite automatically. This saves translation work, not CDC candidate approval.

Expected invoice: four lines (three rack/trolley rows and one industrial sewing machine); **XIN CAI FU** invoice consignee vs **KING SG APPAREL** CDC company. These should **not** be treated as approved stock matches.

## Matching methods

1. Previously verified translations saved for exact Chinese shipping terms.
2. Offline Chinese vocabulary (`services/matching.py: TRANSLATIONS`).
3. Optional third-party translation for unknown Chinese words.
4. English label from the supplier invoice, used for ranking and as a fallback translation when needed.
5. RapidFuzz text similarity, with token overlap and descriptions ranked as candidate matches.
6. Manual reviewer selection and reviewer notes.

Text similarity **does not** establish CDC eligibility. This prototype does not validate models, technical specs, HS classification, company aliases, unit conversions, approved quantities, or legal eligibility. All matching suggestions are provisional.

`data/approved_mappings.json` starts empty; **do not populate it until mappings have been verified**, and only reuse verified mappings for the correct company and QIP. Version 1 does not automatically save reviewer choices.

## Output sheets

- **Updated CDC Master List (.xlsx):** in-place template update that injects imported quantities directly into the target month column (e.g. `SEP 2026` or `ត្រីមាសទី១/២៥`). Preserves 100% of the original workbook layout, Khmer/English headers, merged cells, fonts, styles, and active Excel formulas (`ENDING BALANCE` and `Balance Amount`).
- **Matching Review:** original source row, Chinese, supplier English, translated name, candidate selection, stock-related reference fields, reviewer note/status.
- **Top Candidates:** five text-ranked CDC suggestions for each shipping row.
- **Summary:** totals and explicit confirmation of zero CDC stock changes.
- **Permit-format INV / PL draft:** new two-sheet workbook with supplier invoice values, packing details, and any CDC references manually selected in the app. Missing QIP and pending CDC reviews are marked for review. This is not a permit approval.

## Limitations

- Supports the **2025 QIP728/2401342 CDC workbook** (description B, unit C, approved quantity D, balance Q), **2026 English application master list** (description B, unit F, quantity G, no balance), and **2026 cut-stock layout** (description B, unit F, quantity G, ending balance AC). Other templates may need different parsers.
- Invoice amounts may be calculated as quantity × price when a subtotal is blank.
- CDC available balances may be formulas; read-only `data_only=True` can return blank if Excel has not calculated cached values.
- Translation dictionary coverage is limited; online translation is optional and not guaranteed. Verified translations are reused only for the exact Chinese text and can be corrected by saving a new English term.
- Saved translations use local SQLite; CDC selections remain session-only and require review on new uploads.
- Packing extraction currently supports the supplied `PackingList` layout and similar heading-based sheets. Other layouts may need a parser update.
- No document OCR, Google Drive, permit submission, stock deduction, or original workbook editing.
- `xlrd` is needed for old `.xls` (Excel 97–2003) format.

## Tests

```bash
python -m unittest discover -s tests -v
```

## Shipping workflow reference files

Selected XIN CAI FU import, CDC, customs reporting, and forwarder quotation documents are copied into `reference/shipping_work/`. See its `README.md` for the manifest and source issues. These real business files are excluded by `.gitignore` and should remain local.
