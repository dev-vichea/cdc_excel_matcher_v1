"""CDC Import Clearance & Cut-Stock Manager.
Streamlit dashboard for Cambodia customs duty exemption & CDC monthly cut-stock tracking.
Features Kantumruy Pro font and bilingual support (English & ភាសាខ្មែរ).
"""
from pathlib import Path
import re
import io
import openpyxl.utils
import pandas as pd
import streamlit as st

from services.extraction import extract_shipping, extract_cdc
from services.packing import extract_packing, reconcile_invoice_packing
from services.matching import build_results, load_mappings, normalize, convert_unit_quantity
from services.translation_memory import (
    load_verified_translations,
    save_verified_translation,
    migrate_json_translations,
)
from services.exporter import export_report
from services.bill_extractor import extract_bill
from services.permit_exporter import generate_permit_document, export_permit_draft
from services.cutstock_updater import (
    detect_period_columns,
    suggest_period_from_date,
    consolidate_deductions,
    apply_deductions_to_cdc_workbook,
)
from services.i18n import t, get_font_css
from shipping_ui import render as render_shipping_workspace

ROOT = Path(__file__).parent
MAPPINGS_PATH = ROOT / 'data' / 'approved_mappings.json'
TRANSLATIONS_PATH = ROOT / 'data' / 'verified_translations.sqlite3'
LEGACY_TRANSLATIONS_PATH = ROOT / 'data' / 'verified_translations.json'
migrate_json_translations(LEGACY_TRANSLATIONS_PATH, TRANSLATIONS_PATH)

st.set_page_config(
    page_title='CDC Import & Cut-Stock Manager',
    page_icon='📦',
    layout='wide',
    initial_sidebar_state='expanded',
)

# Embedded Kantumruy Pro font
_font_face = get_font_css()

_custom_css = """
    /* Protect Streamlit Material Symbols / Icon fonts */
    [data-testid="stIconMaterial"], 
    .material-symbols-rounded, 
    .material-icons,
    [class*="material-symbols"],
    [data-testid*="Icon"],
    span[translate="no"],
    [data-testid="stFileUploader"] button span:first-child {
        font-family: "Material Symbols Rounded", "Material Icons" !important;
        font-feature-settings: "liga" 1 !important;
    }

    /* Base Typography */
    html, body, .stApp,
    p, label, input, textarea, select,
    .stMarkdown, .stMarkdown *,
    [data-testid="stWidgetLabel"], [data-testid="stWidgetLabel"] *,
    [data-testid="stMetricLabel"],
    [data-testid="stExpander"] summary, [data-testid="stExpander"] summary div,
    .stAlert * {
        font-family: 'Kantumruy Pro', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
        font-weight: 400;
    }

    h1 {
        font-family: 'Kantumruy Pro', sans-serif !important;
        font-size: 24px !important;
        font-weight: 600 !important;
        letter-spacing: -0.01em;
        margin-bottom: 4px !important;
    }

    h2, h3, h4, strong, b {
        font-family: 'Kantumruy Pro', sans-serif !important;
        font-weight: 600 !important;
    }

    div[data-testid="stMetricValue"] {
        font-family: 'Kantumruy Pro', sans-serif !important;
        font-size: 22px !important;
        font-weight: 600 !important;
        color: #0f172a !important;
    }

    /* Tab Navigation */
    .stTabs [data-baseweb="tab-list"] {
        gap: 16px;
        border-bottom: 1px solid #e2e8f0;
        padding-bottom: 0px;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 8px 6px 10px 6px !important;
        font-weight: 400 !important;
        background-color: transparent !important;
        border: none !important;
        border-radius: 0 !important;
        color: #64748b !important;
    }
    .stTabs [aria-selected="true"] {
        background-color: transparent !important;
        color: #1e40af !important;
        font-weight: 600 !important;
    }
    .stTabs [data-baseweb="tab-highlight"] {
        background-color: #1e40af !important;
        height: 3px !important;
        border-radius: 3px 3px 0 0 !important;
    }

    /* Action Buttons */
    button, [data-baseweb="button"] {
        font-family: 'Kantumruy Pro', sans-serif !important;
        font-weight: 600 !important;
    }
    button[kind="primary"],
    button[data-testid="baseButton-primary"],
    [data-testid="stDownloadButton"] button[kind="primary"],
    .stButton button[kind="primary"] {
        background-color: #1e40af !important;
        border-color: #1e40af !important;
        color: #ffffff !important;
        box-shadow: 0 1px 3px 0 rgba(30, 64, 175, 0.2) !important;
    }
    button[kind="primary"]:hover,
    button[data-testid="baseButton-primary"]:hover,
    [data-testid="stDownloadButton"] button[kind="primary"]:hover,
    .stButton button[kind="primary"]:hover {
        background-color: #1e3a8a !important;
        border-color: #1e3a8a !important;
        color: #ffffff !important;
    }

    /* Metric Cards */
    div[data-testid="stMetric"] {
        background-color: #f8fafc;
        border: 1px solid #e2e8f0;
        padding: 10px 16px;
        border-radius: 8px;
    }
    div[data-testid="stMetricLabel"] {
        font-size: 13px !important;
        color: #64748b !important;
    }

    /* Download Card Highlights */
    .download-card {
        border: 1px solid #cbd5e1;
        border-radius: 10px;
        padding: 16px;
        background: #f8fafc;
    }
"""

st.markdown(f"<style>\n{_font_face}\n{_custom_css}\n</style>", unsafe_allow_html=True)


def render_raw_sheet_tab(file_bytes: bytes, filename: str, key_prefix: str, lang: str):
    """Render a high-fidelity Excel sheet viewer with exact 1-indexed rows and A..Z column letters."""
    if not file_bytes:
        st.info(t('no_file_uploaded', lang))
        return
    try:
        xl = pd.ExcelFile(io.BytesIO(file_bytes))
        sheets = xl.sheet_names
        if not sheets:
            st.warning("No sheets found in file.")
            return

        col_sel, col_info, col_dl = st.columns([3, 3, 2])
        with col_sel:
            selected_sheet = st.selectbox(
                f"📑 {t('select_sheet', lang)}",
                options=sheets,
                key=f"{key_prefix}_sheet_sel"
            )

        df = pd.read_excel(xl, sheet_name=selected_sheet, header=None, dtype=str).fillna('')
        df.columns = [openpyxl.utils.get_column_letter(i + 1) for i in range(len(df.columns))]
        df.index = [i + 1 for i in range(len(df))]

        with col_info:
            st.caption(f"📁 **{filename}**")
            st.caption(t('sheet_info', lang, sheet=selected_sheet, rows=len(df), cols=len(df.columns)))

        with col_dl:
            st.write("")
            st.download_button(
                label=t('download_raw_btn', lang),
                data=file_bytes,
                file_name=filename,
                key=f"{key_prefix}_dl_raw",
                width="stretch"
            )

        st.dataframe(df, width="stretch", height=420)
    except Exception as exc:
        st.error(f"Error loading Excel sheet: {exc}")


@st.dialog("📑 " + t('drawer_title', 'en') + " | " + t('drawer_title', 'km'), width="large")
def show_original_excel_dialog(job: dict, lang: str):
    """Drawer dialog showing raw original supplier import Excel, CDC Master List, and optional Bill PDF."""
    st.caption(t('drawer_desc', lang))

    tab_titles = [t('tab_orig_inv', lang), t('tab_orig_cdc', lang)]
    has_bill = bool(job and job.get('bill_bytes'))
    if has_bill:
        tab_titles.append(t('tab_orig_bill', lang))

    tabs = st.tabs(tab_titles)

    with tabs[0]:
        ship_bytes = job.get('ship_bytes') if job else None
        ship_name = job.get('ship_filename', 'Supplier_Invoice.xlsx') if job else 'Supplier_Invoice.xlsx'
        render_raw_sheet_tab(ship_bytes, ship_name, key_prefix='drawer_inv', lang=lang)

    with tabs[1]:
        cdc_bytes = job.get('cdc_bytes') if job else None
        cdc_name = job.get('cdc_filename', 'CDC_Master.xlsx') if job else 'CDC_Master.xlsx'
        render_raw_sheet_tab(cdc_bytes, cdc_name, key_prefix='drawer_cdc', lang=lang)

    if has_bill and len(tabs) > 2:
        with tabs[2]:
            bill_meta = job.get('bill_meta') or {}
            st.caption(f"📁 **{job.get('bill_filename', 'Bill_of_Lading.pdf')}**")
            b_c1, b_c2, b_c3 = st.columns(3)
            b_c1.markdown(f"**{t('bill_no', lang)}:** `{bill_meta.get('bl_no') or '—'}`")
            b_c2.markdown(f"**{t('bill_date', lang)}:** `{bill_meta.get('issue_date') or '—'}`")
            b_c3.markdown(f"**Mode:** `{bill_meta.get('shipping_mode') or '—'}`")
            if bill_meta.get('container_seal'):
                st.caption(f"**Container / Trailer:** `{bill_meta['container_seal']}`")
            if bill_meta.get('carrier'):
                st.caption(f"**Carrier:** `{bill_meta['carrier']}`")

            st.download_button(
                label="📥 " + t('download_raw_btn', lang) + " (PDF)",
                data=job['bill_bytes'],
                file_name=job.get('bill_filename', 'Bill_of_Lading.pdf'),
                key="drawer_dl_bill",
                width="stretch"
            )
            with st.expander("Extracted Bill Text & OCR", expanded=False):
                st.text(bill_meta.get('raw_text', 'No text extracted.'))


# Language Selector in Sidebar
lang_choice = st.sidebar.selectbox('🌐 Language / ភាសា', ['English', 'ភាសាខ្មែរ (Khmer)'], index=0 if st.session_state.get('lang', 'en') == 'en' else 1)
lang = 'km' if 'ខ្មែរ' in lang_choice else 'en'
st.session_state['lang'] = lang

workspace_options = [t('ws_matcher', lang), t('ws_shipments', lang)]
workspace = st.sidebar.radio(t('workspace_view', lang), workspace_options)
if workspace == t('ws_shipments', lang):
    render_shipping_workspace(ROOT)
    st.stop()


def process_uploaded_files(
    ship_bytes: bytes, ship_name: str,
    cdc_bytes: bytes, cdc_name: str,
    bill_bytes: bytes = None, bill_name: str = '',
    template_bytes: bytes = None,
    template_name: str = ''
):
    """Extract shipping, CDC, and optional bill files, match lines, and store state."""
    shipmeta, shipitems = extract_shipping(ship_bytes, ship_name)
    packingmeta, packingitems = extract_packing(ship_bytes, ship_name)
    pairs, packing_issues = reconcile_invoice_packing(shipitems, packingitems, shipmeta, packingmeta)
    cdcmeta, cdcitems = extract_cdc(cdc_bytes, cdc_name)

    bill_meta = extract_bill(bill_bytes, bill_name) if bill_bytes else {}

    if not shipitems:
        st.error('No invoice lines found in uploaded supplier file. Check sheet headers.')
        return False
    if not cdcitems:
        st.error('No CDC quota items detected in uploaded master list.')
        return False

    glossary = load_verified_translations(TRANSLATIONS_PATH)
    res = build_results(shipitems, cdcitems, load_mappings(MAPPINGS_PATH), online=False, glossary=glossary)
    serial = st.session_state.get('job_serial', 0) + 1
    st.session_state['job_serial'] = serial
    st.session_state['job'] = {
        'shipmeta': shipmeta, 'cdcmeta': cdcmeta, 'cdcitems': cdcitems,
        'packingmeta': packingmeta, 'packingitems': packingitems,
        'packing_pairs': pairs, 'packing_issues': packing_issues,
        'base_results': res, 'serial': serial,
        'cdc_bytes': cdc_bytes, 'cdc_filename': cdc_name,
        'ship_bytes': ship_bytes, 'ship_filename': ship_name,
        'bill_bytes': bill_bytes, 'bill_filename': bill_name,
        'bill_meta': bill_meta,
        'template_bytes': template_bytes,
        'template_filename': template_name,
    }
    return True


# Main App Title
st.title(t('app_title', lang))
st.caption(t('app_subtitle', lang))

active_job = st.session_state.get('job')

# ==========================================================
# STEP 1: UPLOAD 2 FILES + OPTIONAL BILL (OR LOAD SAMPLES)
# ==========================================================
with st.container(border=True):
    col_u1, col_u2, col_u3 = st.columns(3)
    with col_u1:
        st.markdown(f"**{t('upload_inv', lang)}**")
        shipfile = st.file_uploader(
            "Upload Supplier Excel",
            type=['xls', 'xlsx'],
            key='ship_uploader',
            label_visibility='collapsed'
        )
    with col_u2:
        st.markdown(f"**{t('upload_cdc', lang)}**")
        cdcfile = st.file_uploader(
            "Upload CDC Master",
            type=['xlsx'],
            key='cdc_uploader',
            label_visibility='collapsed'
        )
    with col_u3:
        st.markdown(f"**{t('upload_bill', lang)}**")
        billfile = st.file_uploader(
            "Upload Bill of Lading (PDF)",
            type=['pdf'],
            key='bill_uploader',
            label_visibility='collapsed'
        )

    # Optional Custom Permit Template Expander
    active_tpl_name = active_job.get('template_filename') if active_job else None
    tpl_status = f"🎨 Active: {active_tpl_name}" if active_tpl_name else "🎨 Active: Default (1-26TKYM164.xlsx)"
    with st.expander(f"{t('custom_template_title', lang)} ({tpl_status})", expanded=bool(active_tpl_name)):
        st.caption(t('custom_template_desc', lang))
        custom_tpl = st.file_uploader(
            "Custom Permit Template (.xlsx)",
            type=['xlsx'],
            key='tpl_uploader',
            label_visibility='collapsed'
        )
        if custom_tpl and active_job:
            if active_job.get('template_bytes') != custom_tpl.getvalue():
                active_job['template_bytes'] = custom_tpl.getvalue()
                active_job['template_filename'] = custom_tpl.name
                st.session_state['job'] = active_job
                st.rerun()

        if active_job and active_job.get('template_bytes'):
            if st.button("↺ Reset to Default Template", key="reset_tpl_btn"):
                active_job['template_bytes'] = None
                active_job.pop('template_filename', None)
                st.session_state['job'] = active_job
                st.rerun()

    btn_process = st.button(
        t('extract_btn', lang),
        type='primary',
        width="stretch",
        disabled=not(shipfile and cdcfile)
    )

    if btn_process and shipfile and cdcfile:
        tpl_bytes = custom_tpl.getvalue() if custom_tpl else None
        tpl_name = custom_tpl.name if custom_tpl else ''
        b_bytes = billfile.getvalue() if billfile else None
        b_name = billfile.name if billfile else ''
        if process_uploaded_files(
            shipfile.getvalue(), shipfile.name,
            cdcfile.getvalue(), cdcfile.name,
            b_bytes, b_name,
            tpl_bytes, tpl_name
        ):
            st.rerun()

# If no job is active, show quick intro and stop
if not active_job:
    st.info(t('onboarding_guide', lang))
    st.stop()

# ==========================================================
# STEP 2 & 3: ACTIVE JOB DASHBOARD & 2-FILE GENERATION
# ==========================================================
job = active_job
shipmeta, cdcmeta = job['shipmeta'], job['cdcmeta']
base_results = job['base_results']
serial = job['serial']

# Handle text overrides/corrections
overrides = {}
for index, r in enumerate(base_results):
    edited = st.session_state.get(f'translation_{serial}_{index}')
    if isinstance(edited, str) and edited.strip() and edited.strip() != r['query']:
        overrides[(r['sheet'], r['row'])] = edited.strip()
if overrides:
    changed = [r for r in base_results if (r['sheet'], r['row']) in overrides]
    revised = build_results(changed, job['cdcitems'], load_mappings(MAPPINGS_PATH), overrides=overrides)
    by_row = {(r['sheet'], r['row']): r for r in revised}
    results = [by_row.get((r['sheet'], r['row']), r) for r in base_results]
else:
    results = base_results

# User candidate selections
selections = []
for index, r in enumerate(results):
    saved_pick = st.session_state.get(f'pick_{serial}_{index}')
    candidates = r['candidates']
    if saved_pick is not None:
        chosen = saved_pick
    elif candidates:
        chosen = (candidates[0]['sheet'], candidates[0]['row'])
    else:
        chosen = None

    selected = next((x for x in candidates if (x['sheet'], x['row']) == chosen), None)
    dec = st.session_state.get(f'dec_{serial}_{index}', 'Approved' if selected else 'Unmatched')
    note = st.session_state.get(f'note_{serial}_{index}', '')
    selections.append({'match': selected, 'decision': dec, 'notes': note})

# Executive Metrics
totals = job['packingmeta'].get('printed_totals', {})
pkg_count = totals.get('packages') or sum(item.get('packages') or 0 for item in job['packingitems'])
gw_count = totals.get('gross_weight') or sum(item.get('gross_weight') or 0 for item in job['packingitems'])
total_val_usd = sum(r.get('total') or 0.0 for r in results)
matched_count = sum(bool(s.get('match')) for s in selections)

k1, k2, k3, k4 = st.columns(4)
k1.metric(t('kpi_lines', lang), f"{len(results)} items", f"${total_val_usd:,.2f} USD")
k2.metric(t('kpi_packing', lang), f"{pkg_count:g} pkgs", f"{gw_count:,.1f} kg GW")
k3.metric(t('kpi_matches', lang), f"{matched_count} of {len(results)} matched", t('kpi_high_conf', lang))
cat_label = 'II - RAW MATERIALS' if any(w in (shipmeta.get('category','') + ' '.join(r['chinese'] for r in results)).lower() for w in ['fabric', 'elastic', 'zipper', 'label', 'string', 'stopper', 'ribbon']) else 'I - MACHINERY'
k4.metric("Exemption Category", cat_label, "100% Formulas Protected")

# Verification & Active Files Bar
from datetime import datetime

bill_meta = job.get('bill_meta') or {}

# Date Priority: 1. Bill of Lading Date, 2. Supplier Invoice Date, 3. Current Date
permit_date_str = None
if bill_meta.get('issue_date'):
    permit_date_str = bill_meta['issue_date']
elif shipmeta.get('invoice_date'):
    raw_inv_date = shipmeta['invoice_date']
    for fmt in ('%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y', '%Y/%m/%d', '%d-%b-%Y'):
        try:
            permit_date_str = datetime.strptime(str(raw_inv_date).strip(), fmt).strftime('%d-%b-%Y')
            break
        except Exception:
            pass
if not permit_date_str:
    permit_date_str = datetime.now().strftime('%d-%b-%Y')

with st.container():
    c_info1, c_info2, c_act = st.columns([4, 4, 2], vertical_alignment="center")
    with c_info1:
        st.markdown(f"**{t('inv_consignee', lang)}:** `{shipmeta.get('consignee') or 'Unknown'}`  \n**{t('inv_no', lang)}:** `{shipmeta.get('invoice_no') or 'Unknown'}` ({permit_date_str})")
    with c_info2:
        bl_text = f"  \n**{t('bill_no', lang)}:** `{bill_meta['bl_no']}` ({bill_meta.get('shipping_mode', 'BY TRUCK')})" if bill_meta.get('bl_no') else ""
        st.markdown(f"**Shipper:** `{shipmeta.get('supplier') or 'Unknown'}`  \n**QIP / CIB:** `{cdcmeta.get('qip') or '211/26'}`{bl_text}")
    with c_act:
        if st.button(t('view_original_btn', lang), width="stretch"):
            show_original_excel_dialog(job, lang)

st.markdown('<div style="height: 8px;"></div>', unsafe_allow_html=True)

periods = detect_period_columns(job['cdc_bytes'], sheet_name=cdcmeta.get('sheet'))
consolidation = consolidate_deductions(results, selections)
clean_inv = re.sub(r'[^a-zA-Z0-9]', '_', shipmeta.get('invoice_no') or 'invoice')
qip_input = cdcmeta.get('qip') or '211/26'

permit_bytes = generate_permit_document(
    shipmeta, cdcmeta, results, selections,
    job['packingitems'], job['packing_pairs'],
    job['packing_issues'], qip_reference=qip_input,
    template_bytes=job.get('template_bytes'),
    bill_meta=bill_meta
)

if periods:
    period_labels = [p['label'] for p in periods]
    suggested_idx = suggest_period_from_date(shipmeta.get('invoice_date', ''), periods)
    default_index = next((i for i, p in enumerate(periods) if p['col_idx'] == suggested_idx), 0)
    saved_period_label = st.session_state.get(f'period_pick_{serial}')
    if saved_period_label and any(p['label'] == saved_period_label for p in periods):
        selected_period = next(p for p in periods if p['label'] == saved_period_label)
        selected_period_label = saved_period_label
    else:
        selected_period = periods[default_index]
        selected_period_label = selected_period['label']

    add_existing = st.session_state.get(f'sum_existing_{serial}', True)
    clean_company = re.sub(r'[^a-zA-Z0-9]', '_', cdcmeta.get('company') or shipmeta.get('consignee') or 'company')
    clean_period = re.sub(r'[^a-zA-Z0-9]', '_', selected_period['label'])

    updated_master_bytes = apply_deductions_to_cdc_workbook(
        job['cdc_bytes'],
        consolidation['consolidated'],
        target_col_idx=selected_period['col_idx'],
        sheet_name=selected_period.get('sheet_name'),
        add_to_existing=add_existing,
        amount_col_idx=selected_period.get('amount_col_idx')
    )
else:
    period_labels = []
    default_index = 0
    selected_period_label = ''
    add_existing = True
    clean_company = ''
    clean_period = ''
    updated_master_bytes = None

st.markdown('<div style="height: 12px;"></div>', unsafe_allow_html=True)

def format_quantity(val):
    if val is None:
        return '—'
    try:
        f = float(val)
        return f"{int(f):,}" if f.is_integer() else f"{f:,.2f}".rstrip('0').rstrip('.')
    except (ValueError, TypeError):
        return str(val)

def _get_item_cdc_sort_key(item_tuple):
    if len(item_tuple) == 3:
        res, sel, pair = item_tuple
    else:
        index, res = item_tuple
        sel = selections[index]
    match = sel.get('match')
    if match:
        s = str(match.get('serial') or match.get('row') or '')
        s_clean = s.lstrip('#').strip()
        try:
            return (0, float(s_clean), s_clean)
        except (ValueError, TypeError):
            return (1, 0.0, s_clean)
    return (2, 0.0, str(res.get('row', '')))

has_raw = any(
    any(w in (r.get('chinese', '') + ' ' + (r.get('english_provided') or '')).lower()
        for w in ['fabric', 'elastic', 'zipper', 'label', 'string', 'stopper', 'ribbon', 'yarn', 'cloth'])
    for r in results
)
inv_category = 'II - RAW MATERIALS AND ACCESSORIES' if has_raw else 'I - MACHINERY AND EQUIPMENT'

# ==========================================================
# DETAILS & REVIEW TABS
# ==========================================================
tab_items, tab_permit_inv, tab_permit_pl, tab_cutstock, tab_audit = st.tabs([
    t('tab_matching', lang),
    t('tab_permit_inv', lang),
    t('tab_permit_pl', lang),
    t('tab_cutstock', lang),
    t('tab_audit', lang)
])

# TAB 1: ITEM MATCHING & REVIEW
with tab_items:
    col_m1, col_m2 = st.columns([3, 1], vertical_alignment="center")
    col_m1.caption(t('matching_hint', lang))
    if col_m2.button(t('accept_all_btn', lang), width="stretch"):
        for index, r in enumerate(results):
            if r['candidates']:
                st.session_state[f'pick_{serial}_{index}'] = (r['candidates'][0]['sheet'], r['candidates'][0]['row'])
                st.session_state[f'dec_{serial}_{index}'] = 'Approved'
        st.rerun()

    overview_table = []
    has_any_converted = False
    for index, r in sorted(enumerate(results), key=_get_item_cdc_sort_key):
        sel = selections[index]
        match = sel.get('match')
        raw_qty = r.get('qty')
        raw_unit = r.get('unit', '')

        if match and match.get('unit'):
            cdc_unit = match['unit']
            cdc_qty, is_converted = convert_unit_quantity(raw_qty, raw_unit, cdc_unit)
        else:
            cdc_unit = '—'
            cdc_qty = raw_qty
            is_converted = False

        if is_converted:
            has_any_converted = True
            status_text = t('status_converted', lang)
        else:
            status_text = t('status_match', lang) if match else t('status_unmatched', lang)

        if match:
            raw_s = str(match.get('serial') or match['row'])
            cdc_no = raw_s.lstrip('#').strip()
        else:
            cdc_no = '—'
        orig_desc = r['chinese'] or r['english_provided'] or '—'
        cdc_desc = match['description'] if match else 'No Match'

        overview_table.append({
            t('th_cdc_no', lang): cdc_no,
            t('th_orig_desc', lang): orig_desc,
            t('th_cdc_desc', lang): cdc_desc,
            t('th_qty', lang): format_quantity(cdc_qty),
            t('th_orig_unit', lang): raw_unit or '—',
            t('th_cdc_unit', lang): cdc_unit,
            t('th_price', lang): f"${r['unit_price']:,.2f}" if r.get('unit_price') is not None else '—',
            t('th_status', lang): status_text,
        })
    st.dataframe(pd.DataFrame(overview_table), hide_index=True, width="stretch")

    if has_any_converted:
        st.info("Unit conversion applied: For items where the invoice unit is meters (m) and the CDC quota is Gross, quantity is calculated as integer division `qty // 144` (e.g. 58,724 m / 144 = 407 Gross).")

    with st.expander("🔍 Adjust Item Candidates & Translation Memory", expanded=False):
        for index, r in enumerate(results):
            c_d1, c_d2 = st.columns([1, 1])
            with c_d1:
                st.write(f"**Line {r['row']}:** {r['chinese'] or r['english_provided']}")
                edited = st.text_input(t('en_term_matching', lang), value=base_results[index]['query'], key=f'translation_{serial}_{index}')
                if st.button(t('save_tr_btn', lang), key=f'save_tr_{serial}_{index}'):
                    try:
                        save_verified_translation(TRANSLATIONS_PATH, r['chinese'], edited)
                        st.success(t('tr_saved_success', lang))
                    except Exception as e:
                        st.error(f'Could not save: {e}')
            with c_d2:
                candidates = r['candidates']
                candidate_ids = [None] + [(x['sheet'], x['row']) for x in candidates]
                option_names = {None: '— No match'}
                option_names.update({(x['sheet'], x['row']): f"#{x.get('serial', x['row'])}: {x['description']} ({x['unit']}) · {x['score']}%" for x in candidates})
                current_pick = (selections[index]['match']['sheet'], selections[index]['match']['row']) if selections[index].get('match') else None
                default_idx = candidate_ids.index(current_pick) if current_pick in candidate_ids else 0
                chosen = st.selectbox(t('choose_cdc_cand', lang), options=candidate_ids, index=default_idx,
                                      format_func=lambda key: option_names[key], key=f'pick_{serial}_{index}')

# TAB 2: NEW INVOICE PERMIT PREVIEW
with tab_permit_inv:
    st.markdown(f"#### {t('permit_inv_title', lang)}")
    st.caption(t('permit_inv_desc', lang))

    with st.container():
        c_i1, c_i2, c_i3 = st.columns(3)
        c_i1.caption(f"**Shipper:** {shipmeta.get('supplier') or '—'}")
        c_i2.caption(f"**Invoice No:** `{shipmeta.get('invoice_no') or '—'}` ({permit_date_str})")
        tpl_badge = f"`{job.get('template_filename')}` (Custom)" if job.get('template_bytes') else "Default (`1-26TKYM164.xlsx`)"
        c_i3.caption(f"**Template:** {tpl_badge}")

    permit_inv_rows = []
    total_inv_amount = 0.0
    sorted_permit_items = sorted(zip(results, selections, job['packing_pairs']), key=_get_item_cdc_sort_key)
    for idx, (res, sel, pair) in enumerate(sorted_permit_items):
        match = sel.get('match')
        cdc_num = match.get('serial') or (match['row'] if match else (idx + 1))
        if isinstance(cdc_num, str) and cdc_num.startswith('#'):
            cdc_num = cdc_num[1:]
        try:
            if float(cdc_num).is_integer():
                cdc_num = int(float(cdc_num))
        except (ValueError, TypeError):
            pass

        desc = match['description'].upper() if match and match.get('description') else (res.get('english_provided') or res.get('chinese', '')).upper()

        raw_qty = res.get('qty', 0.0)
        raw_unit = res.get('unit', '')
        if match and match.get('unit'):
            unit = match['unit']
            qty, is_converted = convert_unit_quantity(raw_qty, raw_unit, unit)
        else:
            unit = raw_unit
            qty = raw_qty
            is_converted = False

        total_usd = float(res.get('total') or 0.0)
        if is_converted and qty > 0 and total_usd:
            price = round(total_usd / qty, 4)
            if round(round(total_usd / qty, 2) * qty, 2) == round(total_usd, 2):
                price = round(total_usd / qty, 2)
        else:
            price = float(res.get('unit_price') or 0.0)

        line_amount = round(qty * price, 2) if is_converted else total_usd
        total_inv_amount += line_amount

        permit_inv_rows.append({
            t('th_item_no', lang): cdc_num,
            t('th_permit_desc', lang): desc,
            t('th_permit_qty', lang): format_quantity(qty),
            t('th_permit_unit', lang): unit,
            t('th_unit_price_usd', lang): f"${price:,.2f}" if price is not None else '—',
            t('th_amount_usd', lang): f"${line_amount:,.2f}",
        })

    st.dataframe(pd.DataFrame(permit_inv_rows), hide_index=True, width="stretch")
    st.caption(f"Total Declared Value: **${total_inv_amount:,.2f} USD** | All items use official CDC uppercase descriptions and CDC units.")


# TAB 3: NEW PACKING LIST PERMIT PREVIEW
with tab_permit_pl:
    st.markdown(f"#### {t('permit_pl_title', lang)}")
    st.caption(t('permit_pl_desc', lang))

    if job['packing_issues']:
        for issue in job['packing_issues']:
            st.error(f"Issue: {issue}")
    else:
        st.caption(f"✓ Verification: {len(results)} items agree with packing list ({pkg_count:g} pkgs, {gw_count:,.1f} kg GW).")

    permit_pl_rows = []
    tot_pkgs = 0
    tot_nw = 0.0
    tot_gw = 0.0

    sorted_permit_items = sorted(zip(results, selections, job['packing_pairs']), key=_get_item_cdc_sort_key)
    for idx, (res, sel, pair) in enumerate(sorted_permit_items):
        match = sel.get('match')
        desc = match['description'].upper() if match and match.get('description') else (res.get('english_provided') or res.get('chinese', '')).upper()

        raw_qty = res.get('qty', 0.0)
        raw_unit = res.get('unit', '')
        if match and match.get('unit'):
            unit = match['unit']
            qty, is_converted = convert_unit_quantity(raw_qty, raw_unit, unit)
        else:
            unit = raw_unit
            qty = raw_qty

        pck = pair.get('packing')
        pkgs = pck.get('packages') if pck else (qty if str(unit).lower() in ['set', 'pcs'] else 1)
        nw = pck.get('net_weight') if pck else None
        gw = pck.get('gross_weight') if pck else None

        if pkgs: tot_pkgs += pkgs
        if nw: tot_nw += nw
        if gw: tot_gw += gw

        permit_pl_rows.append({
            t('th_packages', lang): format_quantity(pkgs),
            t('th_permit_desc', lang): desc,
            t('th_permit_qty', lang): format_quantity(qty),
            t('th_permit_unit', lang): unit,
            t('th_net_weight', lang): f"{nw:,.1f}" if nw is not None else '—',
            t('th_gross_weight', lang): f"{gw:,.1f}" if gw is not None else '—',
        })

    st.dataframe(pd.DataFrame(permit_pl_rows), hide_index=True, width="stretch")
    st.caption(f"Total Packages: **{tot_pkgs:g} pkgs** | Total Net Weight: **{tot_nw:,.1f} kg** | Total Gross Weight: **{tot_gw:,.1f} kg**")

# TAB 4: CUT-STOCK BREAKDOWN
with tab_cutstock:
    st.markdown(f"#### {t('cons_items_title', lang)}")
    if periods:
        col_p_sel, col_p_chk = st.columns([3, 2], vertical_alignment="bottom")
        with col_p_sel:
            new_p = st.selectbox(
                t('target_period', lang),
                options=period_labels,
                index=period_labels.index(selected_period_label) if selected_period_label in period_labels else default_index,
                key=f'period_pick_{serial}'
            )
            if new_p != selected_period_label:
                st.rerun()
        with col_p_chk:
            new_add = st.checkbox(
                t('sum_existing', lang),
                value=add_existing,
                help=t('sum_existing_help', lang),
                key=f'sum_existing_{serial}'
            )
            if new_add != add_existing:
                st.rerun()

    cons_rows = []
    for item in consolidation['consolidated']:
        status_icon = t('status_exceeded', lang) if item['is_exceeded'] else t('status_ok', lang)
        cons_rows.append({
            t('th_cdc_row', lang): f"#{item['cdc_serial'] or item['cdc_row']}",
            t('th_cdc_desc', lang): item['cdc_description'],
            t('th_cdc_unit', lang): item['cdc_unit'],
            t('th_approved', lang): f"{item['approved']:,.0f}" if item['approved'] else '—',
            t('th_prev_rem', lang): f"{item['remaining']:,.0f}" if item['remaining'] is not None else '—',
            t('th_deduct_qty', lang): f"{item['deduct_qty']:,.0f}",
            t('th_new_rem', lang): f"{item['new_remaining']:,.0f}" if item['new_remaining'] is not None else '—',
            t('th_status', lang): status_icon,
            t('th_usd', lang): f"${item['total_invoice_usd']:,.2f}",
        })
    if cons_rows:
        st.dataframe(pd.DataFrame(cons_rows), hide_index=True, width="stretch")
    if consolidation['has_exceeded']:
        st.error(t('exceeded_warning', lang))

# TAB 5: AUDIT REPORT & RAW INSPECTION
with tab_audit:
    c_aud1, c_aud2 = st.columns(2)
    with c_aud1:
        st.markdown(f"#### {t('doc2_title', lang)}")
        st.caption(t('doc2_desc', lang))
        audit_bytes = export_report(shipmeta, cdcmeta, results, selections)
        st.download_button(
            t('doc2_btn', lang),
            data=audit_bytes,
            file_name=f"CDC_Matching_Audit_{clean_inv}.xlsx",
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            width="stretch"
        )
    with c_aud2:
        st.markdown("#### 🔍 Original Spreadsheet Drawer")
        st.caption("Inspect raw Excel sheets with 1-indexed rows and A..Z column headers.")
        if st.button("Open Spreadsheet Viewer", width="stretch"):
            show_original_excel_dialog(job, lang)

# ==========================================================
# BOTTOM ACTION: 2 DOWNLOAD BUTTONS (NO EXTRA TEXT)
# ==========================================================
st.markdown('<div style="height: 16px;"></div>', unsafe_allow_html=True)
col_dl1, col_dl2 = st.columns(2)
with col_dl1:
    st.download_button(
        label=t('permit_download_btn', lang),
        data=permit_bytes,
        file_name=f"Permit_Application_{clean_inv}.xlsx",
        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        type='primary',
        width="stretch",
        key=f'dl_permit_btn_{serial}',
    )
with col_dl2:
    if periods and updated_master_bytes:
        st.download_button(
            label=t('cutstock_download_btn', lang, period=selected_period_label),
            data=updated_master_bytes,
            file_name=f"CDC_Master_Deducted_{clean_company}_{clean_period}_{clean_inv}.xlsx",
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            type='primary',
            width="stretch",
            key=f'dl_cutstock_btn_{serial}',
        )
