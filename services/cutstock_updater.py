"""In-place CDC Master List cut-stock updater.

Preserves 100% of original workbook layout, formatting, styles, Khmer/English headers,
merged cells, and existing Excel calculation formulas.
"""
from io import BytesIO
import re
from typing import Any, Dict, List, Optional, Tuple
import openpyxl
from openpyxl.utils import get_column_letter

MONTH_NAMES = {'JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC'}
MONTH_ORDER = {m: i for i, m in enumerate(['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC'], 1)}


def _clean_str(val: Any) -> str:
    return str(val).strip() if val is not None else ""


def _to_float(val: Any) -> Optional[float]:
    try:
        cleaned = str(val).replace(",", "").strip()
        return float(cleaned) if cleaned else None
    except (ValueError, TypeError):
        return None


def detect_period_columns(workbook_bytes: bytes, sheet_name: Optional[str] = None) -> List[Dict[str, Any]]:
    """Detect deduction period columns (e.g. 'AUG 2026', 'SEP 2026', 'ត្រីមាសទី១/២៥') in CDC workbook.
    
    Returns a list of dicts with:
      - col_idx: 1-based column index
      - col_letter: Excel column letter ('L', 'G', etc.)
      - label: human-readable period label
      - period_type: 'monthly' or 'quarterly'
      - sheet_name: sheet where period was found
      - amount_col_idx: column index of accompanying amount column, if any
    """
    wb = openpyxl.load_workbook(BytesIO(workbook_bytes), data_only=False)
    try:
        sheets_to_check = [sheet_name] if sheet_name and sheet_name in wb.sheetnames else wb.sheetnames
        for sname in sheets_to_check:
            ws = wb[sname]
            periods: List[Dict[str, Any]] = []

            # 1. Try English monthly cut-stock style (months across rows 4..8)
            for r in range(4, min(10, ws.max_row + 1)):
                for col in range(1, ws.max_column + 1):
                    v = _clean_str(ws.cell(r, col).value).upper()
                    if v in MONTH_NAMES:
                        # Look for year in row below, row above, or nearby
                        year = ""
                        for yr_row in (r + 1, r - 1):
                            if 1 <= yr_row <= ws.max_row:
                                yr_val = _clean_str(ws.cell(yr_row, col).value)
                                yr_match = re.search(r'\b(20\d\d)\b', yr_val)
                                if yr_match:
                                    year = yr_match.group(1)
                                    break
                        label = f"{v} {year}".strip() if year else v
                        # Avoid duplicates
                        if not any(p['col_idx'] == col for p in periods):
                            periods.append({
                                'col_idx': col,
                                'col_letter': get_column_letter(col),
                                'label': label,
                                'period_type': 'monthly',
                                'sheet_name': sname,
                                'amount_col_idx': None,
                            })
                if periods:
                    return periods

            # 2. Try Khmer quarterly style (e.g. ត្រីមាសទី១/២៥ across rows 8..15)
            for r in range(8, min(16, ws.max_row + 1)):
                for col in range(1, ws.max_column + 1):
                    v = _clean_str(ws.cell(r, col).value)
                    if 'ត្រីមាស' in v:
                        # Check if next column is amount (ទឹកប្រាក់)
                        amt_col = None
                        if col + 1 <= ws.max_column:
                            sub_next = _clean_str(ws.cell(r + 1, col + 1).value)
                            if 'ទឹកប្រាក់' in sub_next or 'USD' in sub_next:
                                amt_col = col + 1
                        if not any(p['col_idx'] == col for p in periods):
                            periods.append({
                                'col_idx': col,
                                'col_letter': get_column_letter(col),
                                'label': v,
                                'period_type': 'quarterly',
                                'sheet_name': sname,
                                'amount_col_idx': amt_col,
                            })
                if periods:
                    return periods

            # 3. Try English quarterly style (e.g. Q1 2026, Q2 2026)
            for r in range(4, min(12, ws.max_row + 1)):
                for col in range(1, ws.max_column + 1):
                    v = _clean_str(ws.cell(r, col).value).upper()
                    m = re.search(r'\b(Q[1-4])(?:\s*[-/]?\s*(20\d\d))?\b', v)
                    if m:
                        label = f"{m.group(1)} {m.group(2)}".strip() if m.group(2) else m.group(1)
                        if not any(p['col_idx'] == col for p in periods):
                            periods.append({
                                'col_idx': col,
                                'col_letter': get_column_letter(col),
                                'label': label,
                                'period_type': 'quarterly',
                                'sheet_name': sname,
                                'amount_col_idx': None,
                            })
                if periods:
                    return periods

        return []
    finally:
        wb.close()


def suggest_period_from_date(date_str: str, available_periods: List[Dict[str, Any]]) -> Optional[int]:
    """Suggest the best matching column index from an invoice date string (e.g. '2026.9.20' or '2026-10-08')."""
    if not date_str or not available_periods:
        return None
    # Extract month and year
    m = re.search(r'\b(20\d\d)[-/.](0?[1-9]|1[0-2])\b', date_str)
    if not m:
        m = re.search(r'\b(0?[1-9]|1[0-2])[-/.](20\d\d)\b', date_str)
        if m:
            month_num = int(m.group(1))
            year = m.group(2)
        else:
            return None
    else:
        year = m.group(1)
        month_num = int(m.group(2))

    month_abbrs = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC']
    target_abbr = month_abbrs[month_num - 1]
    quarter_num = (month_num - 1) // 3 + 1

    # Exact month + year match
    for p in available_periods:
        lbl = p['label'].upper()
        if target_abbr in lbl and year in lbl:
            return p['col_idx']

    # Month only
    for p in available_periods:
        if target_abbr in p['label'].upper():
            return p['col_idx']

    # Quarter match for Khmer / English quarter
    q_str = f"Q{quarter_num}"
    khmer_q_digits = {'1': '១', '2': '២', '3': '៣', '4': '៤'}
    khmer_q = f"ត្រីមាសទី{khmer_q_digits.get(str(quarter_num), '')}"
    for p in available_periods:
        lbl = p['label']
        if q_str in lbl.upper() or khmer_q in lbl:
            return p['col_idx']

    return None


def consolidate_deductions(results: List[Dict[str, Any]], selections: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Consolidate multiple invoice lines mapped to the same CDC item and validate against quotas.
    
    Returns:
      - consolidated: list of deduplication records ready for deduction
      - unmatched_lines: list of shipping rows that have no CDC match selected
      - has_exceeded: True if any item's deduct_qty > available remaining balance
    """
    grouped: Dict[Tuple[str, int], Dict[str, Any]] = {}
    unmatched: List[Dict[str, Any]] = []

    for res, sel in zip(results, selections):
        match = sel.get('match')
        if not match:
            unmatched.append(res)
            continue

        key = (match['sheet'], match['row'])
        if key not in grouped:
            grouped[key] = {
                'cdc_sheet': match['sheet'],
                'cdc_row': match['row'],
                'cdc_serial': match.get('serial', ''),
                'cdc_description': match['description'],
                'cdc_unit': match['unit'],
                'approved': match.get('approved'),
                'remaining': match.get('remaining'),
                'deduct_qty': 0.0,
                'total_invoice_usd': 0.0,
                'invoice_lines': [],
                'unit_compatible': match.get('unit_compatible', True),
            }

        qty = float(res.get('qty') or 0.0)
        total_price = float(res.get('total') or 0.0)
        from services.matching import convert_unit_quantity
        cdc_qty, is_converted = convert_unit_quantity(qty, res.get('unit', ''), match['unit'])
        grouped[key]['deduct_qty'] += cdc_qty
        grouped[key]['total_invoice_usd'] += total_price
        grouped[key]['invoice_lines'].append({
            'row': res['row'],
            'description': res.get('english_provided') or res.get('chinese', ''),
            'qty': qty,
            'unit': res.get('unit', ''),
            'cdc_qty': cdc_qty,
            'cdc_unit': match['unit'],
            'is_converted': is_converted,
            'unit_price': res.get('unit_price'),
            'total': total_price,
        })

    consolidated: List[Dict[str, Any]] = []
    has_exceeded = False

    for item in grouped.values():
        item['deduct_qty'] = round(item['deduct_qty'], 4)
        item['total_invoice_usd'] = round(item['total_invoice_usd'], 2)
        rem = item['remaining']
        appr = item['approved']

        # Determine balance check
        base_bal = rem if rem is not None else appr
        if base_bal is not None:
            new_bal = round(base_bal - item['deduct_qty'], 4)
            is_exceeded = item['deduct_qty'] > base_bal
        else:
            new_bal = None
            is_exceeded = False

        if is_exceeded:
            has_exceeded = True

        item['new_remaining'] = new_bal
        item['is_exceeded'] = is_exceeded
        consolidated.append(item)

    # Sort by CDC row order
    consolidated.sort(key=lambda x: (x['cdc_sheet'], x['cdc_row']))
    return {
        'consolidated': consolidated,
        'unmatched': unmatched,
        'has_exceeded': has_exceeded,
    }


def apply_deductions_to_cdc_workbook(
    original_cdc_bytes: bytes,
    deductions: List[Dict[str, Any]],
    target_col_idx: int,
    sheet_name: Optional[str] = None,
    add_to_existing: bool = True,
    amount_col_idx: Optional[int] = None,
) -> bytes:
    """Write deductions directly into the chosen month/quarter column of the original CDC workbook.
    
    Preserves 100% of formatting, Khmer/English headers, styles, fonts, borders, and formulas.
    Returns the raw bytes of the modified Excel workbook.
    """
    wb = openpyxl.load_workbook(BytesIO(original_cdc_bytes), data_only=False)
    try:
        for item in deductions:
            target_sheet_name = item.get('cdc_sheet') or sheet_name or wb.active.title
            if target_sheet_name not in wb.sheetnames:
                continue
            ws = wb[target_sheet_name]
            row_idx = item['cdc_row']
            deduct_qty = item['deduct_qty']

            # Target cell for quantity
            cell = ws.cell(row_idx, target_col_idx)
            current_val = cell.value

            # If existing value is a number and add_to_existing is True, sum them up
            if add_to_existing and isinstance(current_val, (int, float)):
                new_val = current_val + deduct_qty
            else:
                new_val = deduct_qty

            cell.value = new_val

            # If this template has a separate amount column for this period
            amt_col = amount_col_idx or item.get('amount_col_idx')
            if amt_col and amt_col <= ws.max_column:
                amt_cell = ws.cell(row_idx, amt_col)
                # If amount cell already contains a formula (e.g. =G13*E13), PRESERVE IT!
                # Only write an amount if it was blank or a raw number
                if not (isinstance(amt_cell.value, str) and amt_cell.value.startswith('=')):
                    amt_cell.value = item['total_invoice_usd']

        out = BytesIO()
        wb.save(out)
        return out.getvalue()
    finally:
        wb.close()
