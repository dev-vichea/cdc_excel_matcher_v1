"""Read a supplier packing list and compare it with invoice lines."""
import math
import re
import unicodedata

from services.extraction import _identifier, _number, _value, rows_from_workbook


def _text(value):
    return ' '.join(unicodedata.normalize('NFKC', _value(value)).casefold().split())


def _hs(value):
    return re.sub(r'\.0+$', '', _text(value))


def _same_number(left, right):
    return left is not None and right is not None and math.isclose(left, right, rel_tol=0, abs_tol=0.01)


def extract_packing(data, filename):
    """Return packing metadata and item rows from a PackingList/PL sheet."""
    for sheet_name, rows in rows_from_workbook(data, filename):
        if not rows:
            continue
        is_packing = bool(re.search(r'pack|^pl$', sheet_name, re.I)) or any(
            'PACKING LIST' in ' '.join(_value(v).upper() for v in cells)
            for _, cells in rows[:10]
        )
        if not is_packing:
            continue
        meta = {'sheet': sheet_name, 'supplier': '', 'consignee': '', 'contract_no': '', 'printed_totals': {}}
        for rn, cells in rows[:15]:
            vals = [_value(v) for v in cells]
            if rn <= 4 and not meta['supplier']:
                meta['supplier'] = next((v for v in vals if any(kw in v.upper() for kw in ['LTD', 'LIMITED', 'INC', 'CORP', 'CO.', 'COMPANY'])), '')
            for col, v in enumerate(vals):
                lower = v.lower()
                if 'to:messers' in lower or lower.strip(' :') == 'consignee':
                    meta['consignee'] = next((x for x in vals[col + 1:] if x), meta['consignee'])
                elif rn <= 6 and lower.strip(' :') in ['to', 'to:']:
                    cand = next((x for x in vals[col + 1:] if x), '')
                    if any(kw in cand.upper() for kw in ['CO.', 'LTD', 'INC', 'CORP', 'LIMITED', 'COMPANY']):
                        meta['consignee'] = cand
                if 'contract no' in lower:
                    meta['contract_no'] = next((x for x in vals[col + 1:] if x), meta['contract_no'])

        # Header detection
        header_pos = None
        for index, (_, cells) in enumerate(rows[:35]):
            line = ' '.join(_value(v).lower() for v in cells)
            if ('description' in line or '货品名称' in line or '品名' in line) and (
                'quantity' in line or '数量' in line or 'weight' in line or '重量' in line or
                'packages' in line or 'g.w.' in line or '箱号' in line or 'case' in line
            ):
                header_pos = index
                break
        if header_pos is None:
            continue

        h_rows = [rows[header_pos][1]]
        data_offset = 1
        if header_pos + 1 < len(rows):
            sub_line = ' '.join(_value(v).lower() for v in rows[header_pos + 1][1])
            if any(t in sub_line for t in ['case', 'description', 'quantity', 'g.w', 'n.w', 'weight', 'kgs', 'm3', 'cbm']):
                h_rows.append(rows[header_pos + 1][1])
                data_offset = 2

        headings = []
        max_c = max(len(r) for r in h_rows)
        for c in range(max_c):
            col_tokens = ' '.join(_value(r[c]).lower() for r in h_rows if c < len(r) and _value(r[c]))
            headings.append(col_tokens)

        def col_find(*tokens):
            return next((i for i, h in enumerate(headings) if any(t in h for t in tokens)), None)

        desc_col = col_find('description', 'descriptions', '货品名称', '品名')
        qty_col = col_find('quantity', '数量')
        unit_col = col_find('unit', '单位')
        pkg_col = col_find('packages', 'package', '件数', '包数')
        case_col = col_find('case no', '箱号')
        gw_col = col_find('g.w', 'gross weight', '毛重')
        nw_col = col_find('n.w', 'net weight', '净重')
        vol_col = col_find('m3', 'cbm', 'measurement', 'means m3', '体积')
        hs_col = col_find('h.s.code', 'hs code', 'hs-code')

        items = []
        for rn, cells in rows[header_pos + data_offset:]:
            vals_str = [_value(c) for c in cells]
            line_str = ' '.join(vals_str).upper()

            calc_pkgs = None
            for ci in range(min(5, len(cells) - 2)):
                if _value(cells[ci + 1]) in ['~', '-', 'TO', 'to']:
                    c_start = _number(cells[ci])
                    c_end = _number(cells[ci + 2])
                    if c_start is not None and c_end is not None and c_end >= c_start:
                        calc_pkgs = c_end - c_start + 1
                        break

            desc = _value(cells[desc_col]) if desc_col is not None and desc_col < len(cells) else ''
            if not desc or not re.search(r'[A-Za-z\u4e00-\u9fff]', desc):
                for ci, c in enumerate(cells):
                    v = _value(c)
                    if len(v) > 2 and re.search(r'[A-Za-z\u4e00-\u9fff]', v) and not any(kw in v.upper() for kw in ['TOTAL', 'STYLE', 'USD', '======', 'CASE', 'TTL']):
                        desc = v; desc_col = ci; break

            qty = _number(cells[qty_col]) if qty_col is not None and qty_col < len(cells) else None
            qty_ci = qty_col
            if qty is None and desc_col is not None:
                for ci in range(desc_col + 1, len(cells)):
                    n = _number(cells[ci])
                    if n is not None and n > 0:
                        qty = n; qty_ci = ci; break

            # Check if this is the total row
            if items and (any(kw in line_str for kw in ['TTL:', 'TOTAL:', 'TOTAL', 'SAY:TOTAL']) or (qty is not None and qty > 0 and not desc)):
                pkgs_tot = None; gw_tot = None; nw_tot = None; vol_tot = None
                if pkg_col is not None and pkg_col < len(cells) and _number(cells[pkg_col]):
                    pkgs_tot = _number(cells[pkg_col])
                    gw_tot = _number(cells[gw_col]) if gw_col is not None and gw_col < len(cells) else None
                    nw_tot = _number(cells[nw_col]) if nw_col is not None and nw_col < len(cells) else None
                    vol_tot = _number(cells[vol_col]) if vol_col is not None and vol_col < len(cells) else None
                else:
                    nums = [_number(c) for c in cells if _number(c) is not None and _number(c) > 0]
                    if len(nums) >= 4:
                        pkgs_tot, gw_tot, nw_tot, vol_tot = nums[0], nums[1], nums[2], nums[3]
                    elif len(nums) >= 3:
                        pkgs_tot, gw_tot, nw_tot = nums[0], nums[1], nums[2]
                    elif len(nums) >= 1:
                        pkgs_tot = nums[0]

                meta['printed_totals'] = {
                    'qty': qty,
                    'packages': pkgs_tot,
                    'gross_weight': gw_tot,
                    'net_weight': nw_tot,
                    'volume': vol_tot
                }
                break

            if not desc or not re.search(r'[A-Za-z\u4e00-\u9fff]', desc) or desc.upper() in ['CASE NO.', 'DESCRIPTIONS', 'KGS', 'TOTAL']:
                continue

            if qty is None or qty <= 0:
                continue

            english = ''
            if desc_col is not None and qty_col is not None and desc_col + 1 < qty_col:
                english = ' '.join(_value(cells[i]) for i in range(desc_col + 1, qty_col)).strip()

            pkgs = calc_pkgs
            if pkgs is None and pkg_col is not None and pkg_col < len(cells):
                pkgs = _number(cells[pkg_col])
            if pkgs is None and case_col is not None and case_col < len(cells):
                pkgs = _number(cells[case_col])

            unit = _value(cells[unit_col]) if unit_col is not None and unit_col < len(cells) else ''
            if not unit and qty_ci is not None and qty_ci + 1 < len(cells):
                cand_u = _value(cells[qty_ci + 1])
                if len(cand_u) <= 10 and not _number(cand_u):
                    unit = cand_u

            gw = _number(cells[gw_col]) if gw_col is not None and gw_col < len(cells) else None
            nw = _number(cells[nw_col]) if nw_col is not None and nw_col < len(cells) else None
            vol = _number(cells[vol_col]) if vol_col is not None and vol_col < len(cells) else None

            # Heuristic for shifted columns
            nums_after = [(ci, _number(cells[ci])) for ci in range(desc_col + 1, len(cells)) if _number(cells[ci]) is not None and _number(cells[ci]) > 0 and ci != qty_ci]
            if gw is None and len(nums_after) >= 1:
                gw = nums_after[0][1]
            if nw is None and len(nums_after) >= 2:
                nw = nums_after[1][1]
            if vol is None and len(nums_after) >= 3:
                vol = nums_after[2][1]

            if gw is not None and nw is not None and nw > gw:
                gw, nw = nw, gw

            hs = _identifier(cells[hs_col]) if hs_col is not None and hs_col < len(cells) else ''
            items.append({
                'sheet': sheet_name, 'row': rn, 'hs_code': hs,
                'chinese': desc, 'english_provided': english,
                'qty': qty, 'unit': unit, 'packages': pkgs,
                'gross_weight': gw, 'net_weight': nw, 'volume': vol
            })

        if items:
            return meta, items
    return {'sheet': '', 'supplier': '', 'consignee': '', 'contract_no': '', 'printed_totals': {}}, []


def reconcile_invoice_packing(invoice_items, packing_items, invoice_meta=None, packing_meta=None):
    """Pair lines and return discrepancies. No missing values are assumed equal."""
    invoice_meta = invoice_meta or {}
    packing_meta = packing_meta or {}
    unused = set(range(len(packing_items)))
    pairs = []
    issues = []
    if not packing_items:
        issues.append('No packing-list lines detected.')
    for invoice in invoice_items:
        def rank(packing):
            chinese = _text(invoice['chinese']) == _text(packing['chinese'])
            hs = _hs(invoice['hs_code']) == _hs(packing['hs_code']) if (invoice.get('hs_code') and packing.get('hs_code')) else True
            qty = _same_number(invoice['qty'], packing['qty'])
            unit = _text(invoice['unit']) == _text(packing['unit'])
            if chinese and hs and qty and unit: return 5
            if chinese and hs and unit: return 4
            if chinese and qty: return 3
            if chinese: return 2
            if _text(invoice.get('english_provided')) and _text(invoice.get('english_provided')) == _text(packing.get('english_provided')) and qty: return 1
            if qty: return 1
            return 0
        choices = [(rank(packing_items[i]), i) for i in unused]
        best = max(choices, key=lambda choice: (choice[0],
                 -abs(invoice['qty'] - packing_items[choice[1]]['qty']), -choice[1]), default=(0, -1))
        packing = packing_items[best[1]] if best[0] > 0 else None
        if packing is not None:
            unused.remove(best[1])
        row_issues = []
        if packing is None:
            row_issues.append(f"Invoice row {invoice['row']}: no corresponding packing-list line.")
        else:
            for field, label, normalizer in [('chinese', 'Chinese description', _text),
                                            ('english_provided', 'English description', _text),
                                            ('unit', 'unit', _text)]:
                inv_val = invoice.get(field)
                pck_val = packing.get(field)
                if inv_val and pck_val and normalizer(inv_val) != normalizer(pck_val):
                    row_issues.append(f"Invoice row {invoice['row']} / packing row {packing['row']}: {label} differs.")
            if invoice.get('hs_code') and packing.get('hs_code') and _hs(invoice['hs_code']) != _hs(packing['hs_code']):
                row_issues.append(f"Invoice row {invoice['row']} / packing row {packing['row']}: HS code differs.")
            if not _same_number(invoice['qty'], packing['qty']):
                row_issues.append(f"Invoice row {invoice['row']} / packing row {packing['row']}: quantity differs ({invoice['qty']:g} vs {packing['qty']:g}).")
            missing = [label for field, label in [('packages', 'packages'), ('gross_weight', 'gross weight'),
                                               ('net_weight', 'net weight'), ('volume', 'volume')]
                     if packing.get(field) is None]
            if missing:
                row_issues.append(f"Packing row {packing['row']}: missing {', '.join(missing)}.")
        pairs.append({'invoice': invoice, 'packing': packing, 'issues': row_issues})
        issues.extend(row_issues)
    for i in sorted(unused):
        issues.append(f"Packing row {packing_items[i]['row']}: no corresponding invoice line.")
    if invoice_items and packing_items and not _same_number(
        sum(x['qty'] for x in invoice_items), sum(x['qty'] for x in packing_items)
    ):
        issues.append('Invoice and packing-list total item quantities differ.')
    for key, label in [('consignee', 'consignee'), ('supplier', 'supplier')]:
        left, right = invoice_meta.get(key), packing_meta.get(key)
        if left and right and _text(left) != _text(right):
            issues.append(f'Invoice and packing-list {label} names differ.')
    contract = packing_meta.get('contract_no')
    if contract and invoice_meta.get('invoice_no') and _text(contract) != _text(invoice_meta['invoice_no']):
        issues.append('Packing-list contract number differs from the invoice number.')
    return pairs, issues
