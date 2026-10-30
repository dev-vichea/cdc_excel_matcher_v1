"""Service for extracting transport metadata from Bill of Lading (B/L) PDFs.

Supports digital vector PDFs via PyMuPDF (fitz) with automatic OCR fallback
using Tesseract for scanned/image PDFs.
"""
import io
import os
import re
import shutil
import subprocess
from datetime import datetime
from typing import Dict, Any, Optional

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None


def extract_bill(pdf_bytes: bytes, filename: str = '') -> Dict[str, Any]:
    """Extract metadata from Bill of Lading (B/L) or Truck Waybill PDF."""
    meta: Dict[str, Any] = {
        'bl_no': '',
        'issue_date': '',
        'raw_date': '',
        'shipping_mode': '',
        'container_seal': '',
        'packages': None,
        'gross_weight': None,
        'volume': None,
        'shipper': '',
        'consignee': '',
        'origin': '',
        'destination': '',
        'carrier': '',
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

    # 4. Container & Seal / Truck Info
    meta['container_seal'] = _extract_container_seal(full_text, meta['bl_no'])

    # 5. Packages, Gross Weight, Volume (CBM)
    _extract_quantities(full_text, meta)

    # 6. Shipper, Consignee, Origin, Destination, Carrier
    _extract_parties(full_text, all_blocks, meta)

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
    # Check block layout: word next to 'Truck Bill Of Lading No:' or 'B/L No.'
    for i, b in enumerate(blocks):
        b_txt = b[4].strip()
        if re.search(r'(?:Truck\s+Bill\s+Of\s+Lading\s*No|B/?L\s*(?:NO\.?|NUMBER))', b_txt, re.I):
            # Check same block or next block
            m = re.search(r'(?:No\.?|NUMBER)[\s:]*([A-Z0-9_\-\/]+)', b_txt, re.I)
            if m and m.group(1).upper() not in ['REF', 'NO', 'NUMBER', 'OF', 'THE']:
                return m.group(1).strip()

    # Regex search across text
    patterns = [
        r'(?:Truck\s+Bill\s+Of\s+Lading\s*No|Bill\s+Of\s+Lading\s*No|B/?L\s*NO\.?)[\s:]*([A-Z0-9_\-\/]+)',
        r'\b(RCLY\d{6,}[A-Z0-9]*)\b',
        r'\b(SITP[A-Z0-9]{6,})\b',
        r'\b(YS\d{6,}[A-Z0-9\-]*)\b',
    ]
    for pat in patterns:
        m = re.search(pat, text, re.I)
        if m:
            val = m.group(1).strip()
            if val.upper() not in ['REF', 'NO', 'NUMBER', 'OF', 'THE', 'DATE']:
                return val

    # Fallback to general tracking / bill number format
    m_gen = re.search(r'\b([A-Z]{3,4}\d{8,}[A-Z0-9]*)\b', text)
    if m_gen:
        return m_gen.group(1).strip()
    return ''


def _extract_shipping_mode(text: str) -> str:
    """Detect shipping mode: BY TRUCK, BY SEA, or BY AIR."""
    if re.search(r'\b(?:BY\s+TRUCK|TRUCK\s+WAY|TRUCKING)\b', text, re.I):
        return 'BY TRUCK'
    if re.search(r'\b(?:BY\s+AIR|AIR\s+WAY)\b', text, re.I):
        return 'BY AIR'
    if re.search(r'\b(?:BY\s+SEA|OCEAN|VESSEL|CY[\/\-]CY)\b', text, re.I):
        return 'BY SEA'
    return 'BY SEA'


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
    pkg_m = re.search(r'(\d+)\s*(?:PACKAGES|PKGS|CTNS|COLLI|CARTONS|PIECES|PCS|ROLLS)', text, re.I)
    if pkg_m:
        try:
            meta['packages'] = int(pkg_m.group(1))
        except ValueError:
            pass

    gw_m = re.search(r'([\d,]+\.?\d*)\s*(?:KGS|KG|GROSS\s*WEIGHT)', text, re.I)
    if gw_m:
        try:
            meta['gross_weight'] = float(gw_m.group(1).replace(',', ''))
        except ValueError:
            pass

    cbm_m = re.search(r'([\d,]+\.?\d*)\s*(?:CBM|M3|MEASUREMENT)', text, re.I)
    if cbm_m:
        try:
            meta['volume'] = float(cbm_m.group(1).replace(',', ''))
        except ValueError:
            pass


def _extract_parties(text: str, blocks: list, meta: Dict[str, Any]) -> None:
    """Extract shipper, consignee, route, and carrier."""
    for i, b in enumerate(blocks):
        b_txt = b[4].strip()
        b_lower = b_txt.lower()
        if b_lower == 'shipper:' and i + 1 < len(blocks):
            lines = [l.strip() for l in blocks[i+1][4].strip().split('\n') if l.strip()]
            if lines:
                meta['shipper'] = lines[0]
        elif b_lower == 'consignee:' and i + 1 < len(blocks):
            lines = [l.strip() for l in blocks[i+1][4].strip().split('\n') if l.strip()]
            if lines:
                meta['consignee'] = lines[0]
        elif 'place of delivery' in b_lower and i + 1 < len(blocks):
            meta['destination'] = blocks[i+1][4].strip().split('\n')[0]
        elif 'place of loading' in b_lower and i + 1 < len(blocks):
            meta['origin'] = blocks[i+1][4].strip().split('\n')[0]
        elif any(w in b_lower for w in ['supply chain', 'lines', 'logistics', 'carrier']):
            if not meta['carrier'] and len(b_txt) < 80:
                meta['carrier'] = b_txt.split('\n')[0]

    # Fallback to regex if block extraction did not find shipper/consignee
    if not meta['shipper']:
        sm = re.search(r'Shipper\s*:?\s*\n?([A-Z0-9\s\.,&]+(?:\n[^\n]+)?)', text, re.I)
        if sm:
            meta['shipper'] = sm.group(1).strip().split('\n')[0]

    if not meta['consignee']:
        cm = re.search(r'Consignee\s*:?\s*\n?([A-Z0-9\s\.,&]+(?:\n[^\n]+)?)', text, re.I)
        if cm:
            meta['consignee'] = cm.group(1).strip().split('\n')[0]
