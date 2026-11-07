"""Service for extracting transport metadata from Bill of Lading (B/L) PDFs.

Supports digital vector PDFs via PyMuPDF (fitz) with automatic OCR fallback
using Tesseract for scanned/image PDFs. Supports English Truck Waybills,
Ocean Bills of Lading, and Chinese Draft B/L confirmation formats.
"""
import io
import math
import os
import re
import shutil
import subprocess
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple

try:
    import pymupdf as fitz
except ImportError:
    try:
        import fitz
    except ImportError:
        fitz = None

ACCESSORY_KEYWORDS = [
    'LABEL', 'CARE LABEL', 'MAIN LABEL', 'SIZE LABEL', 'WOVEN LABEL', 'TAG', 'HANG TAG', 'HANGTAG',
    'WAIST TAG', 'PRICE TAG', 'ZIPPER', 'METAL ZIPPER', 'NYLON ZIPPER', 'PLASTIC ZIPPER', 'BUTTON',
    'SNAP', 'SNAP BUTTON', 'ELASTIC', 'ELASTIC BAND', 'ELASTIC STRING', 'ELASTIC WEBBING', 'RIBBON',
    'DRAWSTRING', 'DRAW CORD', 'STOPPER', 'PLASTIC STOPPER', 'METAL STOPPER', 'EYELET', 'THREAD',
    'SEWING THREAD', 'TAPE', 'SEAM TAPE', 'VELCRO', 'HOOK', 'LOOP', 'BUCKLE', 'RIVET', 'PULLER',
    'CORD', 'PATCH', 'PIN', 'BADGE', 'POLYBAG', 'HANGER'
]

FABRIC_KEYWORDS = [
    'KNITTED FABRIC', 'WOVEN FABRIC', 'INTER LINING FABRIC', 'INTERLINING FABRIC', 'INTER LINING',
    'INTERLINING', 'FABRIC', 'FLEECE', 'DENIM', 'JERSEY', 'TWILL', 'RIB FABRIC', 'MESH FABRIC'
]


def extract_bill(pdf_bytes: bytes, filename: str = '') -> Dict[str, Any]:
    """Extract metadata from Bill of Lading (B/L) or Truck Waybill PDF."""
    meta: Dict[str, Any] = {
        'bl_no': '',
        'issue_date': '',
        'raw_date': '',
        'shipping_mode': 'BY SEA',
        'container_seal': '',
        'container': '',
        'seal': '',
        'packages': None,
        'gross_weight': None,
        'volume': None,
        'shipper': '',
        'shipper_address': '',
        'consignee': '',
        'consignee_address': '',
        'vat': '',
        'origin': '',
        'destination': '',
        'carrier': '',
        'vessel': '',
        'voyage': '',
        'descriptions': [],
        'raw_text': '',
        'ocr_used': False,
        'filename': filename,
        'has_bill': False,
    }

    if not pdf_bytes or not fitz:
        return meta

    try:
        doc = fitz.open(stream=pdf_bytes, filetype='pdf')
    except Exception as exc:
        meta['error'] = str(exc)
        return meta

    full_text = ''
    all_blocks = []
    for page in doc:
        full_text += page.get_text() + '\n'
        for b in page.get_text('blocks'):
            all_blocks.append(b)

    # If digital text is empty or too short (< 50 chars), attempt OCR fallback
    if len(full_text.strip()) < 50:
        tess_bin = shutil.which('tesseract') or '/opt/homebrew/bin/tesseract'
        if os.path.exists(tess_bin):
            ocr_text = ''
            for page in doc:
                try:
                    pix = page.get_pixmap(dpi=150)
                    proc = subprocess.run(
                        [tess_bin, 'stdin', 'stdout', '-l', 'eng+chi_sim'],
                        input=pix.tobytes('png'),
                        capture_output=True,
                        check=True,
                        timeout=20
                    )
                    ocr_text += proc.stdout.decode('utf-8', errors='ignore') + '\n'
                except Exception:
                    pass
            if len(ocr_text.strip()) > len(full_text.strip()):
                full_text = ocr_text
                meta['ocr_used'] = True

    meta['raw_text'] = full_text.strip()
    if not meta['raw_text']:
        return meta

    meta['has_bill'] = True

    # 1. Date of Issue / Shipped on Board Date
    meta['issue_date'], meta['raw_date'] = _extract_bill_date(full_text)

    # 2. B/L Number / Waybill Number
    meta['bl_no'] = _extract_bl_number(full_text, all_blocks)

    # 3. Shipping Mode (BY TRUCK / BY SEA / BY AIR)
    meta['shipping_mode'] = _extract_shipping_mode(full_text)

    # 4. Chinese Draft B/L Table (Container, Seal, Packages, GW, Volume)
    _extract_chinese_draft_table(all_blocks, meta)

    # 5. Fallback/Standard Quantities & Container/Seal
    if meta['packages'] is None or meta['gross_weight'] is None or meta['volume'] is None:
        _extract_quantities(full_text, meta)

    if not meta['container_seal']:
        meta['container_seal'] = _extract_container_seal(full_text, meta['bl_no'])

    # 6. Shipper, Consignee, Origin, Destination, Carrier, Vessel, Voyage
    _extract_parties(full_text, all_blocks, meta)

    # 7. Goods descriptions on B/L
    meta['descriptions'] = _extract_goods_descriptions(full_text, all_blocks)

    return meta


def _extract_bill_date(text: str) -> tuple[str, str]:
    """Extract and standardize B/L date into DD-Mon-YYYY format."""
    patterns = [
        # Explicit labels: Date of Issue, Place and Date of Issue, Shipped on board dated
        r'(?:Place\s+and\s+Date\s+of\s+Issue|Date\s+of\s+Issue|SHIPPED\s+ON\s+BOARD\s+DATED|Issue\s+Date|B/?L\s*Date|Date\s*:)[\s\S]{0,40}?(\d{1,2}[-/\.]\d{1,2}[-/\.]\d{4})',
        r'(?:Place\s+and\s+Date\s+of\s+Issue|Date\s+of\s+Issue|SHIPPED\s+ON\s+BOARD\s+DATED|Issue\s+Date|B/?L\s*Date)[\s\S]{0,40}?([A-Za-z]{3,9}[-\s]\d{1,2}[-\s]\d{4})',
        r'(?:Place\s+and\s+Date\s+of\s+Issue|Date\s+of\s+Issue|SHIPPED\s+ON\s+BOARD\s+DATED|Issue\s+Date|B/?L\s*Date)[\s\S]{0,40}?(\d{4}[-/\.]\d{1,2}[-/\.]\d{1,2})',
        r'\b(\d{1,2}[-/\.]\d{1,2}[-/\.]\d{4})\b',
        r'\b([A-Za-z]{3}[-\s]\d{1,2}[-\s]\d{4})\b',
        r'\b(\d{4}[-/\.]\d{1,2}[-/\.]\d{1,2})\b',
    ]

    for pat in patterns:
        for m in re.finditer(pat, text, re.I):
            raw_d = m.group(1).strip()
            for fmt in (
                '%d-%m-%Y', '%d/%m/%Y', '%d.%m.%Y',
                '%Y-%m-%d', '%Y/%m/%d', '%Y.%m.%d',
                '%b-%d-%Y', '%b %d %Y', '%b-%d-%y',
                '%d-%b-%Y', '%d %b %Y',
                '%m/%d/%Y', '%m-%d-%Y'
            ):
                try:
                    dt = datetime.strptime(raw_d, fmt)
                    if 2000 <= dt.year <= 2035:
                        return dt.strftime('%d-%b-%Y'), raw_d
                except Exception:
                    pass
    return '', ''


def _extract_bl_number(text: str, blocks: list) -> str:
    """Extract B/L number or Truck Waybill number."""
    # 1. Chinese Draft B/L: 提单号码：\nOOLU2341852380 or CPL0534707
    m_chi = re.search(r'提单号码[：:]\s*\n?\s*([A-Za-z0-9_\-\/]+)', text)
    if m_chi:
        val = m_chi.group(1).strip()
        if val.upper() not in ['提单类型', 'SW', 'ORIGINAL', 'DRAFT', 'REF']:
            return val

    # 2. Check block layout: word next to 'Truck Bill Of Lading No:' or 'B/L No.'
    for i, b in enumerate(blocks):
        b_txt = b[4].strip()
        if re.search(r'(?:Truck\s+Bill\s+Of\s+Lading\s*No|B/?L\s*(?:NO\.?|NUMBER))', b_txt, re.I):
            m = re.search(r'(?:No\.?|NUMBER)[\s:]*([A-Z0-9_\-\/\+]+)', b_txt, re.I)
            if m and m.group(1).upper() not in ['REF', 'NO', 'NUMBER', 'OF', 'THE']:
                return m.group(1).strip()
            # If empty in current block, check next block
            if i + 1 < len(blocks):
                nb = blocks[i+1][4].strip()
                if re.match(r'^[A-Z0-9_\-\/\+]{6,}$', nb) and nb.upper() not in ['REF', 'NO', 'NUMBER', 'CARRIER', 'PREPAID']:
                    return nb

    # 3. Regex patterns across text
    patterns = [
        r'(?:Truck\s+Bill\s+Of\s+Lading\s*No|Bill\s+Of\s+Lading\s*No|B/?L\s*NO\.?)[\s:]*([A-Z0-9_\-\/\+]+)',
        r'\b(RCLY\d{6,}(?:\+RCLY\d+)?)\b',
        r'\b(OOLU\d{8,}[A-Z0-9]*)\b',
        r'\b(CPL\d{6,}[A-Z0-9]*)\b',
        r'\b(SITP[A-Z0-9]{6,})\b',
        r'\b(YS\d{6,}[A-Z0-9\-]*)\b',
    ]
    for pat in patterns:
        m = re.search(pat, text, re.I)
        if m:
            val = m.group(1).strip()
            if val.upper() not in ['REF', 'NO', 'NUMBER', 'OF', 'THE', 'DATE']:
                return val

    # 4. Fallback to general tracking / bill number format
    m_gen = re.search(r'\b([A-Z]{3,4}\d{8,}[A-Z0-9]*)\b', text)
    if m_gen:
        return m_gen.group(1).strip()
    return ''


def _extract_shipping_mode(text: str) -> str:
    """Detect shipping mode: BY TRUCK, BY SEA, or BY AIR."""
    if re.search(r'\b(?:BY\s+TRUCK|TRUCK\s+WAY|TRUCKING|TYPE\s+OF\s+SHIPMENT\s*\n?\s*BY\s+TRUCK)\b', text, re.I):
        return 'BY TRUCK'
    if re.search(r'\b(?:BY\s+AIR|AIR\s+WAY|AIR\s+FREIGHT)\b', text, re.I):
        return 'BY AIR'
    if re.search(r'(?:船名|航次|起运港口|卸货港|目的港|CY[\/\-]CY|VESSEL|OCEAN|1\*40HQ|1\*20GP|OOLU|SITP|SIHANOUKVILLE|BY\s+SEA)', text, re.I):
        return 'BY SEA'
    return 'BY SEA'


def _extract_chinese_draft_table(blocks: list, meta: Dict[str, Any]) -> None:
    """Extract packages, gross weight, volume, container, seal from Chinese Draft table."""
    for i, b in enumerate(blocks):
        b_txt = b[4].strip()
        if '件数' in b_txt and ('毛重' in b_txt or '体积' in b_txt) and i + 1 < len(blocks):
            val_txt = blocks[i+1][4].strip()
            # Val_txt contains container, seal, package count, weight, volume
            m_pkg = re.search(r'(\d+)\s*\n?\s*(?:PACKAGE|PKGS|件|CARTONS)', val_txt, re.I)
            if m_pkg:
                meta['packages'] = int(m_pkg.group(1))

                # Number(s) after PACKAGE -> gross weight, volume
                after_pkg = val_txt[m_pkg.end():].strip().split('\n')
                nums = []
                for token in after_pkg:
                    clean_tok = token.replace(',', '').strip()
                    try:
                        nums.append(float(clean_tok))
                    except ValueError:
                        pass
                if len(nums) >= 1 and meta['gross_weight'] is None:
                    meta['gross_weight'] = nums[0]
                if len(nums) >= 2 and meta['volume'] is None:
                    meta['volume'] = nums[1]

                # Lines before PACKAGE -> Container, Seal
                before_pkg = [l.strip() for l in val_txt[:m_pkg.start()].strip().split('\n') if l.strip()]
                if len(before_pkg) >= 2:
                    meta['container'] = before_pkg[0]
                    meta['seal'] = before_pkg[1]
                    meta['container_seal'] = f"{before_pkg[0]} / {before_pkg[1]}"
                elif len(before_pkg) == 1:
                    meta['container'] = before_pkg[0]
                    meta['container_seal'] = before_pkg[0]
            break


def _extract_container_seal(text: str, bl_no: str) -> str:
    """Extract container / seal number or trailer info."""
    patterns = [
        r'(\d+X\d+\s*HQ[^\n\r]*)',
        r'(PART\s+OF\s+\d+[\*X]\d+[A-Z0-9\s\/]*)',
        r'([A-Z]{4}\d{7}[\s\/]*[A-Z0-9]+)',
        r'\b([A-Z]{4}\d{7})\b',
    ]
    for pat in patterns:
        m = re.search(pat, text, re.I)
        if m:
            val = m.group(1).strip()
            if val != bl_no and val.upper() not in ['CHINA', 'CAMBODIA', 'VIETNAM']:
                return val
    return ''


def _extract_quantities(text: str, meta: Dict[str, Any]) -> None:
    """Extract packages, gross weight, and volume."""
    pkg_m = re.search(r'(\d+)\s*(?:PACKAGES|PKGS|CTNS|COLLI|CARTONS|PIECES|PCS|ROLLS|PACKAGE)\b', text, re.I)
    if pkg_m and meta['packages'] is None:
        try:
            meta['packages'] = int(pkg_m.group(1))
        except ValueError:
            pass

    gw_m = re.search(r'([\d,]+\.?\d*)\s*(?:KGS|KG|GROSS\s*WEIGHT)\b', text, re.I)
    if gw_m and meta['gross_weight'] is None:
        try:
            meta['gross_weight'] = float(gw_m.group(1).replace(',', ''))
        except ValueError:
            pass

    cbm_m = re.search(r'([\d,]+\.?\d*)\s*(?:CBM|M3|MEASUREMENT)\b', text, re.I)
    if cbm_m and meta['volume'] is None:
        try:
            meta['volume'] = float(cbm_m.group(1).replace(',', ''))
        except ValueError:
            pass


def _extract_parties(text: str, blocks: list, meta: Dict[str, Any]) -> None:
    """Extract shipper, consignee, route, and carrier for both Chinese and English B/Ls."""
    # 1. Chinese Draft B/L scan
    for i, b in enumerate(blocks):
        b_txt = b[4].strip()

        # Vessel / Voyage
        if '船名' in b_txt:
            lines = [l.strip() for l in b_txt.split('\n') if l.strip()]
            for li, l in enumerate(lines):
                if '船名' in l and li + 1 < len(lines):
                    meta['vessel'] = lines[li+1]
                if '航次' in l and li + 1 < len(lines):
                    meta['voyage'] = lines[li+1]

        # Shipper
        if '发货人' in b_txt and i + 1 < len(blocks):
            next_b = blocks[i+1][4].strip()
            lines = [l.strip() for l in next_b.split('\n') if l.strip() and '不显示' not in l]
            if lines and not meta['shipper']:
                meta['shipper'] = lines[0]
                meta['shipper_address'] = '\n'.join(lines[1:])

        # Consignee
        if '收货人' in b_txt:
            cnee_lines = []
            for j in range(i + 1, min(i + 9, len(blocks))):
                nb_txt = blocks[j][4].strip()
                if any(kw in nb_txt for kw in ['通知人', '起运港口', '卸货港', '箱型', '唛头', '品名']):
                    break
                for l in nb_txt.split('\n'):
                    l = l.strip()
                    if l and not any(kw in l for kw in ['通知人', '起运港口', '箱型']):
                        cnee_lines.append(l)
            if cnee_lines and not meta['consignee']:
                meta['consignee'] = cnee_lines[0]
                meta['consignee_address'] = '\n'.join(cnee_lines)
                m_vat = re.search(r'VAT[:\s]*([A-Za-z0-9\-]+)', '\n'.join(cnee_lines))
                if m_vat:
                    meta['vat'] = m_vat.group(1).strip()

        # Origin / Destination
        if '起运港口' in b_txt:
            m_orig = re.search(r'起运港口[：:]\s*\n?\s*([^\n\r]+)', b_txt)
            if m_orig:
                meta['origin'] = m_orig.group(1).strip()
        if '目的港' in b_txt:
            m_dest = re.search(r'目的港[：:]\s*\n?\s*([^\n\r]+)', b_txt)
            if m_dest:
                meta['destination'] = m_dest.group(1).strip()

    # 2. English / Truck Waybill block scan
    for i, b in enumerate(blocks):
        b_txt = b[4].strip()
        b_lower = b_txt.lower()
        if b_lower == 'shipper:' and i + 1 < len(blocks):
            lines = [l.strip() for l in blocks[i+1][4].strip().split('\n') if l.strip()]
            if lines and not meta['shipper']:
                meta['shipper'] = lines[0]
                meta['shipper_address'] = '\n'.join(lines[1:])
        elif b_lower == 'consignee:' and i + 1 < len(blocks):
            lines = [l.strip() for l in blocks[i+1][4].strip().split('\n') if l.strip()]
            if lines and not meta['consignee']:
                meta['consignee'] = lines[0]
                meta['consignee_address'] = '\n'.join(lines[1:])
                m_vat = re.search(r'VAT[:\s]*([A-Za-z0-9\-]+)', '\n'.join(lines))
                if m_vat:
                    meta['vat'] = m_vat.group(1).strip()
        elif 'place of delivery' in b_lower and i + 1 < len(blocks):
            if not meta['destination']:
                meta['destination'] = blocks[i+1][4].strip().split('\n')[0]
        elif 'place of loading' in b_lower and i + 1 < len(blocks):
            if not meta['origin']:
                meta['origin'] = blocks[i+1][4].strip().split('\n')[0]
        elif any(w in b_lower for w in ['supply chain', 'lines', 'logistics', 'carrier']):
            if not meta['carrier'] and len(b_txt) < 80:
                meta['carrier'] = b_txt.split('\n')[0]

    # 3. Fallback regex for shipper/consignee
    if not meta['shipper']:
        sm = re.search(r'Shipper\s*:?\s*\n?([A-Z0-9\s\.,&]+(?:\n[^\n]+)?)', text, re.I)
        if sm:
            meta['shipper'] = sm.group(1).strip().split('\n')[0]

    if not meta['consignee']:
        cm = re.search(r'Consignee\s*:?\s*\n?([A-Z0-9\s\.,&]+(?:\n[^\n]+)?)', text, re.I)
        if cm:
            meta['consignee'] = cm.group(1).strip().split('\n')[0]

    if not meta['vat']:
        m_vat = re.search(r'VAT[:\s]*([A-Za-z0-9\-]+)', text, re.I)
        if m_vat:
            meta['vat'] = m_vat.group(1).strip()


def _extract_goods_descriptions(text: str, blocks: list) -> List[str]:
    """Extract declared goods descriptions from B/L text and blocks."""
    descs = []

    # 1. Truck Waybill description between packages and weight
    m_tw = re.search(r'\d+\s*(?:PACKAGES|PKGS)[\s\n\r]+([A-Z0-9\s\n\r&,\-\(\)\/\.]+?)[\s\n\r]+[\d,]+\.?\d*\s*KGS', text, re.I)
    if m_tw:
        raw_desc = m_tw.group(1).strip()
        for line in raw_desc.split('\n'):
            line_clean = line.strip().upper()
            if line_clean and len(line_clean) > 2 and not any(kw in line_clean for kw in ['TOTAL', 'PARTICULARS', 'CONTAINER', 'REMARK']):
                if line_clean not in descs:
                    descs.append(line_clean)

    # 2. Chinese Draft B/L goods section
    known_goods = [
        'KNITTED FABRIC', 'WOVEN FABRIC', 'INTER LINING FABRIC', 'INTERLINING FABRIC',
        'GARMENT ACCESSORIES', 'ACCESSORIES'
    ]
    for b in blocks:
        b_txt = b[4].strip()
        for line in b_txt.split('\n'):
            line_u = line.strip().upper()
            for kg in known_goods:
                if kg in line_u and line_u not in descs:
                    # Ignore headers and boilerplate
                    if not any(kw in line_u for kw in ['COMPANY', 'REMARK', 'MADE IN', 'STYLE', 'QUANTITY', 'WEIGHT:', 'BAG NO']):
                        descs.append(line_u)

    # 3. Direct regex scan if still empty
    if not descs:
        for kg in known_goods:
            if re.search(r'\b' + re.escape(kg) + r'\b', text, re.I):
                if kg not in descs:
                    descs.append(kg)

    return descs


def classify_invoice_items(items: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Classify invoice lines into fabrics, accessories, and other materials."""
    fabrics, accessories, others = [], [], []
    for it in items:
        name = (it.get('chinese') or it.get('english_provided') or '').strip()
        clean = re.sub(r'[（\(][^）\)]*[）\)]', '', name).strip().upper()
        if not clean:
            continue
        is_acc = any(re.search(r'\b' + re.escape(kw) + r'\b', clean) for kw in ACCESSORY_KEYWORDS) or \
                 any(kw in clean for kw in ['STOPPER', 'EYELET', 'ZIPPER', 'LABEL', 'RIBBON', 'DRAWSTRING', 'ELASTIC', 'TAG', 'BUTTON'])
        is_fab = any(kw in clean for kw in FABRIC_KEYWORDS)

        entry = {
            'raw': name,
            'clean': clean,
            'qty': it.get('qty'),
            'unit': it.get('unit'),
            'total': it.get('total')
        }
        if is_acc and not is_fab:
            accessories.append(entry)
        elif is_fab:
            fabrics.append(entry)
        elif is_acc:
            accessories.append(entry)
        else:
            others.append(entry)
    return fabrics, accessories, others


def reconcile_bill_and_shipping(
    bill_meta: Dict[str, Any],
    shipmeta: Dict[str, Any],
    packingmeta: Dict[str, Any],
    invoice_items: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Reconcile B/L transport document against Invoice and Packing List.

    Verifies:
      1. Mode of transport (BY SEA / BY TRUCK)
      2. Consignee name, bill address, and VAT registration number
      3. Shipper / supplier name and address
      4. Total package count
      5. Gross weight (kg)
      6. Volume (CBM)
      7. Goods Description: checks fabric names and applies the 3+ accessories rule:
         If 3 or more kinds/lines of accessories are on the invoice/PL, they are
         declared collectively as 'GARMENT ACCESSORIES' on the B/L!
    """
    checklist = []

    # 1. Mode of Transport
    b_mode = (bill_meta.get('shipping_mode') or '').strip().upper()
    i_mode = (shipmeta.get('shipping_mode') or '').strip().upper()
    mode_val = b_mode or i_mode or 'BY SEA'
    mode_match = (not b_mode) or (not i_mode) or (b_mode == i_mode) or ('TRUCK' in b_mode and 'TRUCK' in i_mode) or ('SEA' in b_mode and 'SEA' in i_mode)
    checklist.append({
        'item': 'Shipping Mode',
        'bill_value': b_mode or '—',
        'inv_value': i_mode or '—',
        'status': 'MATCH' if mode_match else 'WARNING',
        'note': f"Confirmed mode: {mode_val}" if mode_match else f"B/L specifies {b_mode}, invoice notes {i_mode}"
    })

    # 2. Consignee & Bill Address & VAT
    b_cnee = bill_meta.get('consignee', '').strip()
    i_cnee = shipmeta.get('consignee', '').strip()
    b_cnee_clean = re.sub(r'[^A-Za-z0-9]', '', b_cnee.upper())
    i_cnee_clean = re.sub(r'[^A-Za-z0-9]', '', i_cnee.upper())
    cnee_match = bool(b_cnee_clean and i_cnee_clean and (b_cnee_clean in i_cnee_clean or i_cnee_clean in b_cnee_clean))

    # VAT check
    b_vat = bill_meta.get('vat', '').strip()
    if not b_vat:
        m_bvat = re.search(r'VAT[:\s]*([A-Za-z0-9\-]+)', bill_meta.get('raw_text', ''), re.I)
        if m_bvat:
            b_vat = m_bvat.group(1).strip()
    i_vat = shipmeta.get('vat', '').strip()
    if not i_vat:
        m_ivat = re.search(r'VAT[:\s]*([A-Za-z0-9\-]+)', shipmeta.get('consignee_address', ''), re.I)
        if m_ivat:
            i_vat = m_ivat.group(1).strip()

    vat_match = (b_vat and i_vat and b_vat == i_vat) or (not b_vat and not i_vat) or (b_vat and not i_vat)
    addr_match = cnee_match and (vat_match or not b_vat)
    checklist.append({
        'item': 'Consignee & Bill Address',
        'bill_value': f"{b_cnee} (VAT: {b_vat})" if b_vat else b_cnee or '—',
        'inv_value': f"{i_cnee} (VAT: {i_vat})" if i_vat else i_cnee or '—',
        'status': 'MATCH' if addr_match else 'WARNING',
        'note': f"VAT Verified: {b_vat or i_vat}" if (b_vat and b_vat == i_vat) else ("Company name verified" if cnee_match else "Verify consignee address")
    })

    # 3. Shipper / Supplier
    b_shipper = bill_meta.get('shipper', '').strip()
    i_shipper = shipmeta.get('supplier', '').strip()
    b_ship_clean = re.sub(r'[^A-Za-z0-9]', '', b_shipper.upper())
    i_ship_clean = re.sub(r'[^A-Za-z0-9]', '', i_shipper.upper())
    shipper_match = bool(b_ship_clean and i_ship_clean and (b_ship_clean in i_ship_clean or i_ship_clean in b_ship_clean))
    checklist.append({
        'item': 'Shipper / Supplier',
        'bill_value': b_shipper or '—',
        'inv_value': i_shipper or '—',
        'status': 'MATCH' if shipper_match else 'WARNING',
        'note': "Shipper matched exactly" if shipper_match else "Shipper declared"
    })

    # 4. Total Packages
    b_pkgs = bill_meta.get('packages')
    p_totals = packingmeta.get('printed_totals', {})
    i_pkgs = p_totals.get('packages')
    if b_pkgs is not None and i_pkgs is not None:
        pkg_diff = abs(float(b_pkgs) - float(i_pkgs))
        pkg_match = pkg_diff < 0.01
        checklist.append({
            'item': 'Total Packages',
            'bill_value': f"{int(b_pkgs):,} PKGS",
            'inv_value': f"{int(i_pkgs):,} PKGS",
            'status': 'MATCH' if pkg_match else 'MISMATCH',
            'note': f"Exact match ({int(b_pkgs)} packages)" if pkg_match else f"Difference: {pkg_diff:g} PKGS"
        })
    elif b_pkgs is not None:
        checklist.append({
            'item': 'Total Packages',
            'bill_value': f"{int(b_pkgs):,} PKGS",
            'inv_value': '—',
            'status': 'MATCH',
            'note': f"B/L states {int(b_pkgs)} PKGS"
        })

    # 5. Gross Weight (KGS)
    b_gw = bill_meta.get('gross_weight')
    i_gw = p_totals.get('gross_weight')
    if b_gw is not None and i_gw is not None:
        gw_diff = abs(float(b_gw) - float(i_gw))
        gw_match = gw_diff <= 0.5
        checklist.append({
            'item': 'Gross Weight (KGS)',
            'bill_value': f"{float(b_gw):,.2f} kg",
            'inv_value': f"{float(i_gw):,.2f} kg",
            'status': 'MATCH' if gw_match else 'MISMATCH',
            'note': f"Exact weight match ({float(b_gw):,.2f} kg)" if gw_match else f"Weight diff: {gw_diff:.2f} kg"
        })
    elif b_gw is not None:
        checklist.append({
            'item': 'Gross Weight (KGS)',
            'bill_value': f"{float(b_gw):,.2f} kg",
            'inv_value': '—',
            'status': 'MATCH',
            'note': f"B/L states {float(b_gw):,.2f} kg"
        })

    # 6. Volume (CBM)
    b_vol = bill_meta.get('volume')
    i_vol = p_totals.get('volume')
    if b_vol is not None and i_vol is not None:
        vol_diff = abs(float(b_vol) - float(i_vol))
        vol_match = vol_diff <= 0.1
        checklist.append({
            'item': 'Volume (CBM)',
            'bill_value': f"{float(b_vol):,.2f} CBM",
            'inv_value': f"{float(i_vol):,.2f} CBM",
            'status': 'MATCH' if vol_match else 'MISMATCH',
            'note': f"Volume matched ({float(b_vol):,.2f} CBM)" if vol_match else f"Volume diff: {vol_diff:.2f} CBM"
        })
    elif b_vol is not None:
        checklist.append({
            'item': 'Volume (CBM)',
            'bill_value': f"{float(b_vol):,.2f} CBM",
            'inv_value': '—',
            'status': 'MATCH',
            'note': f"B/L states {float(b_vol):,.2f} CBM"
        })

    # 7. Goods Description & 3+ Accessories Rule
    fabrics, accessories, others = classify_invoice_items(invoice_items)
    bill_descs = bill_meta.get('descriptions') or []
    bill_full = (bill_meta.get('raw_text', '') + ' ' + ' '.join(bill_descs)).upper()

    unique_acc = sorted(set(a['clean'] for a in accessories))
    unique_fab = sorted(set(f['clean'] for f in fabrics))

    has_garment_acc = ('GARMENT ACCESSORIES' in bill_full) or ('ACCESSORIES' in bill_full)
    acc_rule_applied = len(accessories) >= 3 or len(unique_acc) >= 3

    desc_status = 'MATCH'
    desc_notes = []

    if acc_rule_applied:
        if has_garment_acc:
            desc_notes.append(f"3+ Accessories Rule Applied: {len(accessories)} accessories ({', '.join(unique_acc[:4])}...) declared collectively as 'GARMENT ACCESSORIES' on B/L")
        else:
            desc_status = 'WARNING'
            desc_notes.append(f"3+ Accessories Rule: {len(accessories)} accessories on invoice, but 'GARMENT ACCESSORIES' not clearly found on B/L")
    elif len(accessories) > 0:
        desc_notes.append(f"{len(accessories)} accessory item(s): {', '.join(unique_acc)}")
    else:
        desc_notes.append("No accessories on invoice (fabrics only)")

    # Fabric check
    matched_fabs = []
    missing_fabs = []
    for fab in unique_fab:
        f_tokens = [tok for tok in ['KNITTED FABRIC', 'WOVEN FABRIC', 'INTER LINING FABRIC', 'INTERLINING FABRIC', 'FABRIC'] if tok in fab]
        f_match = any(tok in bill_full for tok in f_tokens) or (fab in bill_full)
        if f_match:
            matched_fabs.append(fab)
        else:
            missing_fabs.append(fab)

    if missing_fabs:
        desc_status = 'WARNING'
        desc_notes.append(f"Missing fabric(s) on B/L: {', '.join(missing_fabs)}")
    elif matched_fabs:
        desc_notes.append(f"Fabrics matched: {', '.join(matched_fabs)}")

    b_desc_display = ', '.join(bill_descs) if bill_descs else ('GARMENT ACCESSORIES' if has_garment_acc else 'See B/L description')
    i_desc_display = []
    if unique_fab:
        i_desc_display.append(f"{len(unique_fab)} Fabrics ({', '.join(unique_fab)})")
    if acc_rule_applied:
        i_desc_display.append(f"{len(accessories)} Accessories → 'GARMENT ACCESSORIES'")
    elif unique_acc:
        i_desc_display.append(f"{len(accessories)} Accessories")

    checklist.append({
        'item': 'Goods Description (3+ Rule)',
        'bill_value': b_desc_display,
        'inv_value': ' + '.join(i_desc_display) or 'General Goods',
        'status': desc_status,
        'note': ' | '.join(desc_notes)
    })

    all_ok = all(c['status'] == 'MATCH' for c in checklist)
    has_mismatch = any(c['status'] == 'MISMATCH' for c in checklist)
    overall_status = 'MATCH' if all_ok else ('MISMATCH' if has_mismatch else 'WARNING')

    return {
        'overall_status': overall_status,
        'is_fully_matched': all_ok,
        'checklist': checklist,
        'mode': mode_val,
        'fabrics_count': len(unique_fab),
        'accessories_count': len(accessories),
        'acc_rule_applied': acc_rule_applied,
        'has_garment_acc_on_bill': has_garment_acc,
    }
