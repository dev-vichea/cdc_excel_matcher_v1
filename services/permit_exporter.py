"""Create a new, review-only INV/PL workbook from checked source documents."""
from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter


NAVY='17365D'
PALE='EAF1F8'
AMBER='FFF2CC'
RED='9C2D19'
LINE=Side(style='thin',color='B7C7D6')


def _header(sheet,title,metadata,cdc_info,qip_reference,last_column,packing_issues,review_count):
    end=get_column_letter(last_column)
    sheet.merge_cells(f'A1:{end}1')
    sheet['A1']=title
    sheet['A1'].font=Font(size=16,bold=True,color='FFFFFF')
    sheet['A1'].fill=PatternFill('solid',fgColor=NAVY)
    sheet['A1'].alignment=Alignment(horizontal='center',vertical='center')
    sheet.row_dimensions[1].height=30
    sheet.merge_cells(f'A2:{end}2')
    sheet['A2']='DRAFT — verify CDC references and shipment details'
    sheet['A2'].font=Font(bold=True,color=RED)
    sheet['A2'].fill=PatternFill('solid',fgColor=AMBER)
    sheet['A2'].alignment=Alignment(horizontal='center',vertical='center')
    sheet.row_dimensions[2].height=25
    labels=[('Exporter',metadata.get('supplier','')),
            ('Consignee',metadata.get('consignee','')),
            ('Invoice no.',metadata.get('invoice_no','')),
            ('Invoice date',metadata.get('invoice_date','')),
            ('QIP / CIB',qip_reference or 'TO CONFIRM'),
            ('Route',f"{metadata.get('origin','')} → {metadata.get('destination','')}")]
    for row,(label,value) in enumerate(labels,start=3):
        sheet.cell(row,1,label).font=Font(bold=True,color=NAVY)
        sheet.merge_cells(start_row=row,start_column=2,end_row=row,end_column=last_column)
        sheet.cell(row,2,value or 'TO CONFIRM').alignment=Alignment(wrap_text=True,vertical='center')
        sheet.row_dimensions[row].height=28 if row in (3,4,8) else 23
    sheet.merge_cells(f'A9:{end}9')
    company_mismatch=bool(metadata.get('consignee') and cdc_info.get('company')
                          and _company_key(metadata['consignee'])!=_company_key(cdc_info['company']))
    flags=[]
    if not qip_reference:flags.append('QIP/CIB reference missing')
    if company_mismatch:flags.append('CDC company differs from consignee')
    if packing_issues:flags.append(f'{len(packing_issues)} invoice/packing issue(s)')
    if review_count:flags.append(f'{review_count} CDC line(s) not reviewed')
    sheet['A9']='REVIEW: '+('; '.join(flags) if flags else 'Check all details before submission')
    sheet['A9'].font=Font(bold=True,color=RED)
    sheet['A9'].fill=PatternFill('solid',fgColor=AMBER)
    sheet['A9'].alignment=Alignment(wrap_text=True,vertical='center')
    sheet.row_dimensions[9].height=32
    sheet.sheet_view.showGridLines=False
    sheet.freeze_panes='A12'
    sheet.print_options.horizontalCentered=True
    sheet.sheet_properties.pageSetUpPr.fitToPage=True
    sheet.page_setup.fitToWidth=1
    sheet.page_setup.fitToHeight=0
    sheet.page_setup.orientation='landscape'


def _company_key(value):
    import re
    return re.sub(r'[^a-z0-9]','',str(value).lower())


def _table(sheet,headings,widths):
    for col,(heading,width) in enumerate(zip(headings,widths),start=1):
        cell=sheet.cell(11,col,heading)
        cell.fill=PatternFill('solid',fgColor=NAVY)
        cell.font=Font(color='FFFFFF',bold=True)
        cell.alignment=Alignment(wrap_text=True,vertical='center')
        sheet.column_dimensions[get_column_letter(col)].width=width
    sheet.row_dimensions[11].height=34


def _write_line(sheet,row,values,numeric_columns=()):
    for col,value in enumerate(values,start=1):
        cell=sheet.cell(row,col,value)
        cell.border=Border(bottom=LINE)
        cell.alignment=Alignment(vertical='top',wrap_text=col==2)
        if col in numeric_columns and isinstance(value,(int,float)):
            cell.number_format='#,##0.00;[Red](#,##0.00)'
        if row%2==0:
            cell.fill=PatternFill('solid',fgColor=PALE)
    sheet.row_dimensions[row].height=31


def _cdc_sort_key(item_tuple):
    res, sel, pair = item_tuple
    match = sel.get('match')
    if match:
        s = str(match.get('serial') or match.get('row') or '')
        s_clean = s.lstrip('#').strip()
        try:
            return (0, float(s_clean), s_clean)
        except (ValueError, TypeError):
            return (1, 0.0, s_clean)
    return (2, 0.0, str(res.get('row', '')))


def export_permit_draft(shipmeta,cdcmeta,results,selections,packing_items,pairs,packing_issues,qip_reference=''):
    """Return an independent, two-sheet draft. No source workbook is changed."""
    if len(results)!=len(selections) or len(results)!=len(pairs):
        raise ValueError('Every invoice line needs a review and packing comparison')
    if any(result.get('unit_price') is None or result.get('total') is None for result in results):
        raise ValueError('Invoice prices and amounts are required for every permit-draft line')
    workbook=Workbook()
    invoice=workbook.active
    invoice.title='INV'
    packing=workbook.create_sheet('PL')
    qip_reference=(qip_reference or '').strip()
    pending=sum(s.get('match') is None or s.get('decision')!='Reviewed candidate (not approved)'
                for s in selections)
    _header(invoice,'INVOICE — CDC APPLICATION DRAFT',shipmeta,cdcmeta,qip_reference,7,
            packing_issues,pending)
    _header(packing,'PACKING LIST — CDC APPLICATION DRAFT',shipmeta,cdcmeta,qip_reference,8,
            packing_issues,pending)
    _table(invoice,['CDC #','Description (reviewed)','HS code','Quantity','Unit',
                    'Unit price USD','Amount USD'],[14,42,18,13,11,18,18])
    _table(packing,['Packages','Description (reviewed)','Quantity','Unit',
                    'Net kg','Gross kg','Volume m³','CDC #'],[14,42,13,11,16,16,16,14])
    match_by_packing={}
    for index,(result,selection,pair) in enumerate(zip(results,selections,pairs)):
        match=selection.get('match')
        serial=('#'+str(match['serial'])) if match and match.get('serial') else ''
        description=match['description'].upper() if match and match.get('description') else (result.get('english_provided') or result.get('chinese', '')).upper()
        outcome=selection.get('decision','Pending review')
        
        from services.matching import convert_unit_quantity
        raw_qty = result.get('qty', 0.0)
        raw_unit = result.get('unit', '')
        if match and match.get('unit'):
            unit = match['unit']
            qty, is_conv = convert_unit_quantity(raw_qty, raw_unit, unit)
        else:
            unit = raw_unit
            qty = raw_qty
            is_conv = False
        if match and match.get('unit_price') is not None:
            price = float(match['unit_price'])
        elif is_conv and qty:
            price = round(result['total'] / qty, 4)
        else:
            price = result['unit_price']
        
        line_amount = round(qty * price, 2)
        row=12+index
        _write_line(invoice,row,[serial,description,result['hs_code'],qty,
                                 unit,price,line_amount],
                    (4,6,7))
        if pair['packing'] is not None:
            key=(pair['packing']['sheet'],pair['packing']['row'])
            match_by_packing[key]=(serial,description,outcome)
    invoice_total=12+len(results)
    invoice.cell(invoice_total,2,'TOTAL').font=Font(bold=True,color=NAVY)
    invoice.cell(invoice_total,4,sum(r['qty'] for r in results))
    invoice.cell(invoice_total,7,round(sum(r['total'] or 0 for r in results),2))
    for col in (4,7):invoice.cell(invoice_total,col).number_format='#,##0.00'
    for index,item in enumerate(packing_items):
        serial,description,outcome=match_by_packing.get(
            (item['sheet'],item['row']),('',item['english_provided'] or item['chinese'],'UNMATCHED'))
        _write_line(packing,12+index,[item['packages'],description,item['qty'],
                                      item['unit'],item['net_weight'],item['gross_weight'],
                                      item['volume'],serial],(1,3,5,6,7))
    packing_total=12+len(packing_items)
    packing.cell(packing_total,2,'TOTAL').font=Font(bold=True,color=NAVY)
    for col,key in ((1,'packages'),(3,'qty'),(5,'net_weight'),(6,'gross_weight'),(7,'volume')):
        values=[item.get(key) for item in packing_items]
        if all(value is not None for value in values):
            packing.cell(packing_total,col,round(sum(values),2)).number_format='#,##0.00'
    for sheet,last_row,last_col in ((invoice,invoice_total,7),(packing,packing_total,8)):
        for cell in sheet[last_row][:last_col]:
            cell.fill=PatternFill('solid',fgColor=PALE)
            cell.font=Font(bold=True,color=NAVY)
            cell.border=Border(top=Side(style='medium',color=NAVY))
        sheet.auto_filter.ref=f'A11:{get_column_letter(last_col)}{last_row-1}'
        sheet.print_area=f'A1:{get_column_letter(last_col)}{last_row}'
        sheet.print_title_rows='1:11'
    output=BytesIO()
    workbook.save(output)
    return output.getvalue()


def generate_permit_document(
    shipmeta, cdcmeta, results, selections, packing_items, pairs,
    packing_issues=None, qip_reference='', template_bytes=None,
    bill_meta=None
):
    """Generate official CDC Permit Application INV/PL Excel document.
    
    Uses 1-26TKYM164.xlsx template format as default or user-provided template_bytes.
    Preserves exact font (Times New Roman), layout, formulas, and headers.
    """
    import openpyxl
    from pathlib import Path
    from openpyxl.styles import Font, Alignment

    default_template_path = Path(__file__).parent / 'templates' / 'permit_template_default.xlsx'
    if not default_template_path.exists():
        default_template_path = Path(__file__).parent.parent / 'reference' / 'shipping_work' / '02_import_TK164' / 'permit_application' / '1-26TKYM164.xlsx'

    if template_bytes:
        wb = openpyxl.load_workbook(BytesIO(template_bytes))
    else:
        wb = openpyxl.load_workbook(default_template_path)

    def _find_sheet(workbook, candidates):
        for name in workbook.sheetnames:
            for cand in candidates:
                if cand.lower() == name.strip().lower():
                    return workbook[name]
        for name in workbook.sheetnames:
            for cand in candidates:
                if cand.lower() in name.strip().lower():
                    return workbook[name]
        return None

    inv = _find_sheet(wb, ['INV', 'INVOICE', 'INV PERMIT', 'INVOICE PERMIT']) or wb.worksheets[0]
    pl = _find_sheet(wb, ['PL', 'PACKING LIST', 'PACKING', 'PKL']) or (wb.worksheets[1] if len(wb.worksheets) > 1 else None)

    def safe_set_cell(sheet, row, col, val):
        if sheet is None:
            return
        cell = sheet.cell(row, col)
        if type(cell).__name__ != 'MergedCell':
            cell.value = val

    # 1. Shipper Header
    try:
        from services.settings_store import get_settings
        user_prefs = get_settings()
    except Exception:
        user_prefs = {}
    if shipmeta.get('supplier'):
        safe_set_cell(inv, 1, 1, shipmeta['supplier'])
        safe_set_cell(pl, 1, 1, shipmeta['supplier'])
    if shipmeta.get('supplier_address'):
        addr_lines = [l.strip() for l in shipmeta['supplier_address'].split('\n') if l.strip()]
        if addr_lines:
            safe_set_cell(inv, 2, 1, addr_lines[0])
            safe_set_cell(pl, 2, 1, addr_lines[0])
            if len(addr_lines) > 1:
                safe_set_cell(inv, 3, 1, addr_lines[1])
                safe_set_cell(pl, 3, 1, addr_lines[1])

    # 2. Invoice Details & Date Resolution
    if shipmeta.get('invoice_no'):
        safe_set_cell(inv, 8, 2, shipmeta['invoice_no'])
        safe_set_cell(pl, 8, 2, shipmeta['invoice_no'])

    from datetime import datetime
    # Date Priority: 1. Bill of Lading Date, 2. Supplier Invoice Date, 3. Current Date
    doc_date = None
    if bill_meta and bill_meta.get('issue_date'):
        doc_date = bill_meta['issue_date']
    elif shipmeta.get('invoice_date'):
        raw_inv_date = shipmeta['invoice_date']
        for fmt in ('%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y', '%Y/%m/%d', '%d-%b-%Y'):
            try:
                doc_date = datetime.strptime(str(raw_inv_date).strip(), fmt).strftime('%d-%b-%Y')
                break
            except Exception:
                pass
    if not doc_date:
        doc_date = datetime.now().strftime('%d-%b-%Y')

    safe_set_cell(inv, 8, 7, doc_date)
    inv.cell(8, 7).number_format = '@'
    if pl:
        safe_set_cell(pl, 8, 8, doc_date)
        pl.cell(8, 8).number_format = '@'

    # Shipping Mode & Route (Bill of lading takes priority if provided)
    mode = (bill_meta.get('shipping_mode') if bill_meta else None) or shipmeta.get('shipping_mode') or user_prefs.get('shipping_mode') or 'BY TRUCK'
    safe_set_cell(inv, 9, 2, mode)
    safe_set_cell(pl, 9, 2, mode)

    import re
    orig = (bill_meta.get('origin') if bill_meta else None) or shipmeta.get('origin') or user_prefs.get('origin') or 'JIANGSU, CHINA'
    dest = (bill_meta.get('destination') if bill_meta else None) or shipmeta.get('destination') or user_prefs.get('destination') or 'PHNOM PENH, CAMBODIA'
    orig = re.sub(r',\s*', ', ', str(orig).strip()).upper()
    dest = re.sub(r',\s*', ', ', str(dest).strip()).upper()
    route_str = f'{orig} TO {dest}, KINGDOM OF CAMBODIA.' if 'CAMBODIA' not in dest else f'{orig} TO {dest}'
    safe_set_cell(inv, 10, 2, route_str)
    safe_set_cell(pl, 10, 2, route_str)

    origin_country = shipmeta.get('country_of_origin') or 'CHINA'
    safe_set_cell(inv, 11, 2, origin_country)
    safe_set_cell(pl, 11, 2, origin_country)

    # 3. Consignee
    co = shipmeta.get('consignee') or cdcmeta.get('company') or user_prefs.get('company_name')
    if co:
        safe_set_cell(inv, 12, 2, co)
        safe_set_cell(pl, 12, 2, co)
    if shipmeta.get('consignee_address'):
        raw_lines = [l.strip() for l in shipmeta['consignee_address'].split('\n') if l.strip()]
        c_lines = []
        for l in raw_lines:
            if len(l) > 42 and ',' in l:
                parts = [p.strip() for p in l.split(',') if p.strip()]
                cur = ''
                for p in parts:
                    cand = (cur + ', ' + p).strip(', ')
                    if len(cand) <= 45:
                        cur = cand
                    else:
                        if cur:
                            c_lines.append(cur + ',')
                        cur = p
                if cur:
                    c_lines.append(cur + (',' if l.endswith(',') else ''))
            else:
                c_lines.append(l)

        for idx, line in enumerate(c_lines[:4]):
            safe_set_cell(inv, 13 + idx, 2, line)
            safe_set_cell(pl, 13 + idx, 2, line)

        vat_val = inv.cell(17, 2).value or user_prefs.get('vat_number') or 'VAT No : LO01-902303477'
        safe_set_cell(inv, 17, 2, vat_val)
        if pl:
            safe_set_cell(pl, 17, 2, vat_val)

    # 4. QIP Reference & CDC Approval
    qip = (qip_reference or cdcmeta.get('qip') or user_prefs.get('qip_reference') or '211/26').strip()
    clean_qip = qip.split('(')[0].replace('No.', '').replace('QIP', '').strip('# :')
    if not inv['J9'].value or 'KEEPNH' in str(inv['J9'].value):
        inv['J9'] = f'No. {qip}'

    # 5. Category Header
    has_raw = any(
        any(w in (r.get('chinese', '') + ' ' + (r.get('english_provided') or '')).lower()
            for w in ['fabric', 'elastic', 'zipper', 'label', 'string', 'stopper', 'ribbon', 'yarn', 'cloth'])
        for r in results
    )
    category = 'II - RAW MATERIALS AND ACCESSORIES' if has_raw else 'I - MACHINERY AND EQUIPMENT'

    def safe_set_cell(sheet, row, col, val):
        cell = sheet.cell(row, col)
        if type(cell).__name__ != 'MergedCell':
            cell.value = val

    def _detect_template_layout(sheet, default_start=23, default_total=39):
        start_r = None
        tot_r = None
        for r in range(15, 30):
            line_txt = ' '.join(str(sheet.cell(r, c).value or '') for c in (1, 2, 3)).upper()
            if any(kw in line_txt for kw in ['RAW MATERIALS', 'MACHINERY', 'EQUIPMENT', 'ACCESSORIES']):
                start_r = r + 1
                break
        if start_r is None:
            for r in range(15, 30):
                line_txt = ' '.join(str(sheet.cell(r, c).value or '') for c in (1, 2, 3)).upper()
                if any(kw in line_txt for kw in ['DESCRIPTION', 'PACKAGES NO', 'MARKS & NOS', 'ITEM NO']):
                    start_r = r + 1
                    break
        if start_r is None:
            start_r = default_start

        for r in range(start_r + 1, min(sheet.max_row + 5, 80)):
            for c in range(1, 10):
                val = str(sheet.cell(r, c).value or '').upper()
                if 'SUM(' in val or val == 'TOTAL':
                    tot_r = r
                    return start_r, tot_r
        if tot_r is None:
            tot_r = default_total
        return start_r, tot_r

    start_row_inv, orig_total_row_inv = _detect_template_layout(inv, 24, 40)
    safe_set_cell(inv, start_row_inv - 1, 1, clean_qip)
    safe_set_cell(inv, start_row_inv - 1, 2, category)

    if pl:
        start_row_pl, orig_total_row_pl = _detect_template_layout(pl, 23, 39)
        safe_set_cell(pl, start_row_pl - 1, 2, category)
    else:
        start_row_pl, orig_total_row_pl = 23, 39

    N = len(results)
    capacity_inv = orig_total_row_inv - start_row_inv
    if N > capacity_inv:
        inv.insert_rows(orig_total_row_inv - 1, amount=N - capacity_inv)
        total_row_inv = orig_total_row_inv + (N - capacity_inv)
    else:
        total_row_inv = orig_total_row_inv
        for r in range(start_row_inv + N, orig_total_row_inv):
            for c in range(1, 16):
                safe_set_cell(inv, r, c, None)

    if pl:
        capacity_pl = orig_total_row_pl - start_row_pl
        if N > capacity_pl:
            pl.insert_rows(orig_total_row_pl - 1, amount=N - capacity_pl)
            total_row_pl = orig_total_row_pl + (N - capacity_pl)
        else:
            total_row_pl = orig_total_row_pl
            for r in range(start_row_pl + N, orig_total_row_pl):
                for c in range(1, 16):
                    safe_set_cell(pl, r, c, None)
    else:
        total_row_pl = 39

    font_item = Font(name='Times New Roman', size=12, bold=False)
    font_bold = Font(name='Times New Roman', size=12, bold=True)
    align_left = Alignment(horizontal='left', vertical='center')
    align_right = Alignment(horizontal='right', vertical='center')
    align_center = Alignment(horizontal='center', vertical='center')

    sorted_items = sorted(zip(results, selections, pairs), key=_cdc_sort_key)
    for idx, (res, sel, pair) in enumerate(sorted_items):
        r_inv = start_row_inv + idx
        match = sel.get('match')
        # 1. CDC ID / Item #
        cdc_num = match.get('serial') or (match['row'] if match else (idx + 1))
        if isinstance(cdc_num, str) and cdc_num.startswith('#'):
            cdc_num = cdc_num[1:]
        try:
            if float(cdc_num).is_integer():
                cdc_num = int(float(cdc_num))
        except (ValueError, TypeError):
            pass

        # 2. Description: MUST use the name of the CDC (in uppercase to match permit format)
        if match and match.get('description'):
            desc = match['description'].upper()
        else:
            desc = (res.get('english_provided') or res.get('chinese', '')).upper()

        # 3. Unit & Quantity: MUST use the CDC unit and converted integer quantity
        from services.matching import convert_unit_quantity
        raw_qty = res.get('qty', 0.0)
        raw_unit = res.get('unit', '')
        if match and match.get('unit'):
            unit = match['unit']
            qty, is_converted = convert_unit_quantity(raw_qty, raw_unit, unit)
        else:
            unit = raw_unit
            qty = raw_qty
            is_converted = False

        # 4. Unit price: MUST match CDC Master List if matched, otherwise calculate/fallback
        total_usd = res.get('total')
        if match and match.get('unit_price') is not None:
            price = float(match['unit_price'])
        elif is_converted and qty > 0 and total_usd:
            price = round(total_usd / qty, 4)
            if round(round(total_usd / qty, 2) * qty, 2) == round(total_usd, 2):
                price = round(total_usd / qty, 2)
        else:
            price = float(res.get('unit_price') or 0.0)

        # INV sheet line
        inv.cell(r_inv, 1, cdc_num).alignment = align_center
        inv.cell(r_inv, 1).font = font_item
        inv.cell(r_inv, 2, desc).alignment = align_left
        inv.cell(r_inv, 2).font = font_item
        inv.cell(r_inv, 4, qty).alignment = align_right
        inv.cell(r_inv, 4).font = font_item
        inv.cell(r_inv, 4).number_format = '#,##0.00' if not float(qty).is_integer() else '#,##0'
        inv.cell(r_inv, 5, unit).alignment = align_left
        inv.cell(r_inv, 5).font = font_item
        inv.cell(r_inv, 6, price).alignment = align_right
        inv.cell(r_inv, 6).font = font_item
        inv.cell(r_inv, 6).number_format = '#,##0.00'
        inv.cell(r_inv, 7, f'=D{r_inv}*F{r_inv}').alignment = align_right
        inv.cell(r_inv, 7).font = font_item
        inv.cell(r_inv, 7).number_format = '#,##0.00'

        # PL sheet line
        if pl:
            r_pl = start_row_pl + idx
            pck = pair.get('packing')
            pkgs = pck.get('packages') if pck else (qty if str(unit).lower() in ['set', 'pcs'] else 1)
            nw = pck.get('net_weight') if pck else None
            gw = pck.get('gross_weight') if pck else None

            pl.cell(r_pl, 1, pkgs).alignment = align_center
            pl.cell(r_pl, 1).font = font_bold
            pl.cell(r_pl, 2, desc).alignment = align_left
            pl.cell(r_pl, 2).font = font_item
            pl.cell(r_pl, 5, qty).alignment = align_right
            pl.cell(r_pl, 5).font = font_item
            pl.cell(r_pl, 5).number_format = '#,##0.00' if not float(qty).is_integer() else '#,##0'
            pl.cell(r_pl, 6, unit).alignment = align_left
            pl.cell(r_pl, 6).font = font_item
            if nw is not None:
                pl.cell(r_pl, 7, nw).alignment = align_right
                pl.cell(r_pl, 7).font = font_item
                pl.cell(r_pl, 7).number_format = '#,##0.00'
            if gw is not None:
                pl.cell(r_pl, 8, gw).alignment = align_right
                pl.cell(r_pl, 8).font = font_item
                pl.cell(r_pl, 8).number_format = '#,##0.00'

    last_r_inv = start_row_inv + N - 1
    # Total row formulas
    inv.cell(total_row_inv, 7, f'=SUM(G{start_row_inv}:G{last_r_inv})').number_format = '#,##0.00'
    if pl:
        last_r_pl = start_row_pl + N - 1
        pl.cell(total_row_pl, 1, f'=SUM(A{start_row_pl}:A{last_r_pl})')
        pl.cell(total_row_pl, 7, f'=SUM(G{start_row_pl}:G{last_r_pl})').number_format = '#,##0.00'
        pl.cell(total_row_pl, 8, f'=SUM(H{start_row_pl}:H{last_r_pl})').number_format = '#,##0.00'

    # Signature row & Container
    sig_row_inv = total_row_inv + 3
    company_name = inv['A1'].value or 'COMPANY'
    safe_set_cell(inv, sig_row_inv, 5, company_name)
    if pl:
        sig_row_pl = total_row_pl + 3
        safe_set_cell(pl, sig_row_pl, 6, company_name)

        # Container / Seal on PL (use bill container if found, else clear dummy template string)
        cntr = (bill_meta.get('container_seal') if bill_meta else None) or shipmeta.get('container') or ''
        if cntr:
            safe_set_cell(pl, sig_row_pl, 2, cntr)
        elif pl.cell(sig_row_pl, 2).value and 'FFAU7241358' in str(pl.cell(sig_row_pl, 2).value):
            safe_set_cell(pl, sig_row_pl, 2, None)

        # Clear template dummy difference checks below total if present
        for r_check in (total_row_pl + 1, total_row_pl + 2):
            if r_check < sig_row_pl:
                safe_set_cell(pl, r_check, 7, None)
                safe_set_cell(pl, r_check, 8, None)

        # Resolve all cross-sheet references on PL to real editable values (no raw formulas)
        inv_names = {inv.title.lower(), 'inv', 'invoice'}
        for row in pl.iter_rows():
            for cell in row:
                if type(cell).__name__ != 'MergedCell' and isinstance(cell.value, str) and cell.value.startswith('='):
                    val_str = cell.value.lstrip('=+').strip()
                    if '!' in val_str:
                        parts = val_str.split('!')
                        if len(parts) == 2:
                            s_name = parts[0].strip().strip("'").lower()
                            ref = parts[1].strip()
                            if s_name in inv_names:
                                try:
                                    cell.value = inv[ref].value
                                except Exception:
                                    pass

    out = BytesIO()
    wb.save(out)
    return out.getvalue()
