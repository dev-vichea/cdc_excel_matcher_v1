"""Read supplier .xls/.xlsx and CDC .xlsx; never modify the source files."""
import io
import re
import unicodedata
from pathlib import Path


def _value(v):
    return str(v).strip() if v is not None else ""


def _number(v):
    try:
        return float(str(v).replace(",", ""))
    except (ValueError, TypeError):
        return None


def _identifier(v):
    """Keep spreadsheet numeric identifiers readable without a trailing .0."""
    if isinstance(v,float) and v.is_integer():
        return str(int(v))
    return _value(v)


def rows_from_workbook(data, filename):
    """Yield (sheet_name, [(excel_row_num, [cell values])])."""
    if filename.lower().endswith('.xls'):
        try:
            import xlrd
        except ImportError as exc:
            raise RuntimeError('Install requirements.txt: xlrd is required to read .xls') from exc
        book = xlrd.open_workbook(file_contents=data)
        for sheet in book.sheets():
            yield sheet.name, [(i + 1, sheet.row_values(i)) for i in range(sheet.nrows)]
    elif filename.lower().endswith('.xlsx'):
        from openpyxl import load_workbook
        book = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
        try:
            for sheet in book.worksheets:
                yield sheet.title, list(enumerate(sheet.values, start=1))
        finally:
            book.close()
    else:
        raise ValueError('Only .xls and .xlsx are supported')


def _format_date(val):
    """Normalize Excel float dates or date strings to YYYY-MM-DD."""
    if val is None:
        return ""
    if isinstance(val, (int, float)) and 30000 < val < 60000:
        import datetime
        try:
            d = datetime.date(1899, 12, 30) + datetime.timedelta(days=int(val))
            return d.strftime("%Y-%m-%d")
        except Exception:
            pass
    s = _value(val)
    # Check if matches YYYY.M.D or YYYY/M/D
    m = re.search(r'\b(20\d\d)[./-](0?[1-9]|1[0-2])[./-](0?[1-9]|[12]\d|3[01])\b', s)
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    return s


def extract_shipping(data, filename):
    items = []
    metadata = {
        'invoice_no': '', 'invoice_date': '', 'consignee': '', 'consignee_address': '',
        'supplier': '', 'supplier_address': '', 'origin': '', 'destination': '',
        'shipping_mode': 'BY SEA', 'country_of_origin': 'CHINA', 'category': '', 'sheet': ''
    }
    for sheet_name, rows in rows_from_workbook(data, filename):
        if not rows:
            continue
        if re.search(r'pack|^pl$', sheet_name, re.I) or any(
            'PACKING LIST' in ' '.join(_value(v).upper() for v in cells)
            for _, cells in rows[:10]
        ):
            continue
        meta = dict(metadata)
        meta['sheet'] = sheet_name

        # 1. Metadata scan in upper rows
        for rn, cells in rows[:35]:
            vals = [_value(v) for v in cells]
            line_upper = ' '.join(vals).upper()

            # Supplier detection
            if rn <= 4 and not meta['supplier']:
                for v in vals:
                    vu = v.upper()
                    if any(kw in vu for kw in ['LTD', 'LIMITED', 'INC', 'CORP', 'CO.,', 'COMPANY', '公司']) and len(v) > 3:
                        meta['supplier'] = v
                        # Supplier address often follows in row rn+1
                        if rn < len(rows):
                            sub_v = _value(rows[rn][1][0]) if len(rows[rn][1]) > 0 else ""
                            if sub_v and not any(kw in sub_v.upper() for kw in ['INVOICE', 'TO:', 'DATE', 'CONSIGNEE']):
                                meta['supplier_address'] = sub_v
                        break

            # Consignee detection
            for i, v in enumerate(vals):
                v_clean = v.strip().lower()
                # Invoice No
                if re.search(r'\binv(?:oice)?\s*(?:no|number|\.|\:)', v_clean):
                    found_no = next((_value(cells[k]) for k in range(i + 1, len(cells)) if _value(cells[k])), "")
                    if found_no and not meta['invoice_no']:
                        meta['invoice_no'] = found_no

                # Invoice Date
                if re.search(r'(?:date\s+of\s+invoice|invoice\s+date|^date\b)', v_clean):
                    found_d = next((cells[k] for k in range(i + 1, len(cells)) if _value(cells[k])), None)
                    if found_d is not None and not meta['invoice_date']:
                        meta['invoice_date'] = _format_date(found_d)

                # Consignee
                if any(kw in v_clean for kw in ['to:messers', 'to: messers', 'consignee', 'to:']) or v_clean in ['to', 'to:']:
                    found_co = next((_value(cells[k]) for k in range(i + 1, len(cells)) if _value(cells[k]) and not any(kw in _value(cells[k]).lower() for kw in ['invoice', 'date'])), "")
                    if found_co and not meta['consignee']:
                        meta['consignee'] = found_co
                        # Check subsequent row for address block
                        if rn < len(rows):
                            next_row_vals = [_value(cv) for cv in rows[rn][1]]
                            for nv in next_row_vals:
                                if len(nv) > 15 and any(akw in nv.upper() for kw, akw in [('', 'PHNOM PENH'), ('', 'CAMBODIA'), ('', 'ROAD'), ('', 'STREET'), ('', 'PHUM')]):
                                    meta['consignee_address'] = nv
                                    break

                # Route / Origin / Destination
                if v_clean in ['from', 'from:', '装船口岸']:
                    found_orig = next((_value(cells[k]) for k in range(i + 1, len(cells)) if _value(cells[k]) and _value(cells[k]) not in ['To', '目的地']), "")
                    if found_orig and not meta['origin']:
                        meta['origin'] = found_orig
                if v_clean in ['to', 'to:', 'destination', 'destination:', '目的地']:
                    found_dest = next((_value(cells[k]) for k in range(i + 1, len(cells)) if _value(cells[k])), "")
                    # Ensure destination is not a company name
                    if found_dest and not any(kw in found_dest.upper() for kw in ['LTD', 'LIMITED', 'INC', 'CORP', 'CO.,', 'COMPANY', 'MESSERS']):
                        meta['destination'] = found_dest

        # 2. Header detection for line items
        header_pos = None
        for i, (rn, cells) in enumerate(rows[:35]):
            line = ' '.join(_value(x).lower() for x in cells)
            has_desc = any(t in line for t in ['description', '品名', '货品名称', '货名', 'commodity', 'item'])
            has_qty_or_val = any(t in line for t in ['quantity', '数量', 'amount', '总值', '总价', 'price', '单价', 'h.s.code', 'hs code'])
            if has_desc and has_qty_or_val:
                header_pos = i
                break

        if header_pos is None:
            # Fallback: search for first row with 'description' or '品名'
            for i, (rn, cells) in enumerate(rows[:35]):
                line = ' '.join(_value(x).lower() for x in cells)
                if 'description' in line or '品名' in line or '货品名称' in line:
                    header_pos = i
                    break

        if header_pos is None:
            continue

        headings = [_value(c).lower() for c in rows[header_pos][1]]
        def index_for(tokens, default=None):
            return next((i for i, h in enumerate(headings) if any(t in h for t in tokens)), default)

        hs_col = index_for(['h.s.code', 'hs code', 'hs-code'])
        desc_col = index_for(['description', '品名', '货品名称', '货名'])
        qty_col = index_for(['quantity', '数量'])
        unit_col = index_for(['unit', '单位'])
        price_col = index_for(['unit price', '单价'])
        total_col = index_for(['subtotal', 'amount', '总价', '总值'])

        blank_count = 0
        for rn, cells in rows[header_pos + 1:]:
            vals = list(cells)
            vals_str = [_value(x) for x in cells]
            line_str = ' '.join(vals_str).upper()
            if any(kw in line_str for kw in ['TOTAL:', 'SAY: US DOLLARS', 'SAY:TOTAL', '==================']) and items:
                break

            # Strategy 1: Explicit column layout
            if desc_col is not None and qty_col is not None:
                def at(i):
                    return vals[i] if i is not None and i < len(vals) else None
                qty = _number(at(qty_col))
                chinese = _value(at(desc_col))
                english = ''
                if desc_col + 1 < qty_col:
                    english = ' '.join(_value(at(i)) for i in range(desc_col + 1, qty_col)).strip()

                if not re.search(r'[A-Za-z\u4e00-\u9fff]', chinese + english):
                    continue

                if qty is not None and qty > 0:
                    blank_count = 0
                    unit = _value(at(unit_col))
                    price = _number(at(price_col))
                    total = _number(at(total_col))
                    if total is None and price is not None:
                        total = round(qty * price, 2)
                    items.append({
                        'sheet': sheet_name, 'row': rn, 'hs_code': _identifier(at(hs_col)),
                        'chinese': chinese, 'english_provided': english, 'qty': qty, 'unit': unit,
                        'unit_price': price, 'total': total
                    })
                    continue

            # Strategy 2: Heuristic detection for merged/two-tier headers (like RE2612040)
            nums = [(c, _number(vals[c])) for c in range(len(vals)) if _number(vals[c]) is not None and _number(vals[c]) > 0]
            strs = [(c, _value(vals[c])) for c in range(len(vals)) if _value(vals[c])]

            desc_candidates = [(c, s) for c, s in strs if len(s) > 2 and re.search(r'[A-Za-z\u4e00-\u9fff]', s) and not any(kw in s.upper() for kw in ['TOTAL', 'STYLE', 'USD', '======', 'REMARK', 'COMPANY'])]
            if not desc_candidates or not nums:
                blank_count += 1
                if blank_count > 10 and items:
                    break
                continue

            d_col, d_text = desc_candidates[0]
            q, p, tot = None, None, None
            u = ''

            # Check math relations: n1 * n2 ~= n3
            found_math = False
            for i, (c1, n1) in enumerate(nums):
                for j, (c2, n2) in enumerate(nums):
                    if i == j: continue
                    for k, (c3, n3) in enumerate(nums):
                        if k in (i, j): continue
                        if abs(n1 * n2 - n3) < 0.05 or (n3 > 0 and abs(n1 * n2 - n3) / n3 < 0.001):
                            q = n1 if n1 >= n2 else n2
                            p = n2 if n1 >= n2 else n1
                            tot = n3
                            found_math = True
                            break
                    if found_math: break
                if found_math: break

            if not found_math:
                if len(nums) == 1:
                    q = nums[0][1]
                elif len(nums) == 2:
                    q = nums[0][1]; tot = nums[1][1]
                    p = round(tot / q, 4) if q else None
                elif len(nums) >= 3:
                    q = nums[0][1]; p = nums[1][1]; tot = nums[2][1]

            # Find unit
            for sc, stext in strs:
                if sc != d_col and len(stext) <= 10 and any(uk in stext.lower() for uk in ['kg', 'gross', 'yd', 'm', 'doz', 'dz', 'set', 'pcs', 'roll', 'pair']):
                    u = stext
                    break
            if not u and len(strs) > 1 and strs[1][0] != d_col:
                u = strs[1][1]

            if q is not None and q > 0 and d_text:
                blank_count = 0
                items.append({
                    'sheet': sheet_name, 'row': rn, 'hs_code': '',
                    'chinese': d_text, 'english_provided': '', 'qty': q, 'unit': u,
                    'unit_price': p, 'total': tot
                })

        if items:
            return meta, items
    return metadata, items


def extract_cdc(data, filename):
    company = ''; qip = ''; items = []
    for sheet_name, rows in rows_from_workbook(data, filename):
        if not rows:continue
        for rn,cells in rows[:12]:
            for cell in cells:
                v=_value(cell)
                if not company and ('CO., LTD' in v.upper() or 'CO. LTD' in v.upper()):
                    name=re.sub(r'^\s*(?:COMPANY\s*:|ក្រុមហ៊ុនៈ)\s*', '', v, flags=re.I)
                    # Some application forms append a Khmer translation after
                    # the registered English name. Keep the name through LTD.
                    match=re.search(r'.*?\bCO\.?,?\s*LTD\.?', name, flags=re.I)
                    company=match.group(0) if match else name
                if not qip:
                    m=re.search(r'QIP\s*[-#/]?\s*[\w/-]+',v,re.I)
                    if m:qip=m.group(0)
        # English application and cut-stock sheets share B/F/G item columns.
        # The cut-stock balance heading spans two rows; application forms have
        # no balance column, so remaining must stay unknown.
        columns = None
        for _, cells in rows[:20]:
            headings = [_value(v).upper() for v in cells]
            description = next((i for i, h in enumerate(headings)
                                if h in ('DESCRIPTION OF GOODS', 'DESCRIPTIONS OF GOODS')), None)
            if description is not None and 'UNIT' in headings and 'QUANTITY' in headings:
                balance = next((i for i, h in enumerate(headings) if h == 'ENDING'), None)
                columns = (description, headings.index('UNIT'), headings.index('QUANTITY'), balance)
                break
        # Original 2025 Khmer template: A=line, B=name, C=unit,
        # D=approved, Q=remaining. Avoid interpreting an unrelated workbook.
        if columns is None and any(
            len(cells) > 16 and 'នៅសល់' in _value(cells[16])
            and 'រាយមុខយថាប្រភេទទំនិញ' in _value(cells[1])
            for _, cells in rows[:20]
        ):
            columns = (1, 2, 3, 16)
        if columns is None:
            continue
        unit_price_col = None
        for _, cells in rows[:20]:
            h_upper = [_value(v).upper() for v in cells]
            for idx, h in enumerate(h_upper):
                if any(term in h for term in ('UNIT PRICE', 'UNIT_PRICE', 'U.PRICE', 'តម្លៃរាយ', '单价')) and 'TOTAL' not in h:
                    unit_price_col = idx
                    break
            if unit_price_col is not None:
                break
        name_col, unit_col, approved_col, remaining_col = columns
        for rn,cells in rows:
            if len(cells) <= max(name_col, unit_col, approved_col):continue
            name=_value(cells[name_col])
            unit=_value(cells[unit_col])
            approved=_number(cells[approved_col])
            if not name or approved is None or not unit:continue
            remaining=_number(cells[remaining_col]) if remaining_col is not None and len(cells)>remaining_col else None
            unit_price=_number(cells[unit_price_col]) if unit_price_col is not None and len(cells)>unit_price_col else None
            items.append({'sheet':sheet_name,'row':rn,'serial':_value(cells[0]),'description':name,
                         'unit':unit,'approved':approved,'remaining':remaining,'unit_price':unit_price})
        if items:break
    return {'company':company,'qip':qip,'sheet':sheet_name if items else ''},items
