"""Import matcher & permit preparation page.

Handles supplier invoice extraction, CDC matching, permit preview (INV/PL),
in-place cut-stock deduction, and official Excel exports.
"""

from datetime import datetime
import io
from pathlib import Path
import re

import openpyxl.utils
import pandas as pd
import streamlit as st

from services.bill_extractor import extract_bill, reconcile_bill_and_shipping
from services.cutstock_updater import (
    apply_deductions_to_cdc_workbook,
    consolidate_deductions,
    detect_period_columns,
    suggest_period_from_date,
)
from services.exporter import export_report
from services.extraction import extract_cdc, extract_shipping
from services.i18n import t
from services.matching import (
    build_results,
    convert_unit_quantity,
    load_mappings,
    normalize,
)
from services.packing import extract_packing, reconcile_invoice_packing
from services.permit_exporter import (
    consolidate_permit_items,
    export_permit_draft,
    generate_permit_document,
)
from services.settings_store import (
    get_default_cdc_bytes,
    get_default_cdc_path,
    get_default_template_bytes,
    get_default_template_path,
    get_settings,
)
from services.translation_memory import (
    load_verified_translations,
    migrate_json_translations,
    save_verified_translation,
)

ROOT = Path(__file__).resolve().parent.parent
MAPPINGS_PATH = ROOT / "data" / "approved_mappings.json"
TRANSLATIONS_PATH = ROOT / "data" / "verified_translations.sqlite3"
LEGACY_TRANSLATIONS_PATH = ROOT / "data" / "verified_translations.json"
migrate_json_translations(LEGACY_TRANSLATIONS_PATH, TRANSLATIONS_PATH)

lang = st.session_state.get("lang", "en")


def render_raw_sheet_tab(file_bytes: bytes, filename: str, key_prefix: str, lang_code: str):
    """Render a high-fidelity Excel sheet viewer with exact 1-indexed rows and A..Z column letters."""
    if not file_bytes:
        st.info(t("no_file_uploaded", lang_code))
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
                f":material/tab: {t('select_sheet', lang_code)}",
                options=sheets,
                key=f"{key_prefix}_sheet_sel",
            )

        df = pd.read_excel(xl, sheet_name=selected_sheet, header=None, dtype=str).fillna("")
        df.columns = [openpyxl.utils.get_column_letter(i + 1) for i in range(len(df.columns))]
        df.index = [i + 1 for i in range(len(df))]

        with col_info:
            st.caption(f":material/description: **{filename}**")
            st.caption(t("sheet_info", lang_code, sheet=selected_sheet, rows=len(df), cols=len(df.columns)))

        with col_dl:
            st.write("")
            st.download_button(
                label=t("download_raw_btn", lang_code),
                data=file_bytes,
                file_name=filename,
                key=f"{key_prefix}_dl_raw",
                width="stretch",
            )

        st.dataframe(df, width="stretch", height=420)
    except Exception as exc:
        st.error(f"Error loading Excel sheet: {exc}")


@st.dialog(t("drawer_title", "en") + " | " + t("drawer_title", "km"), width="large")
def show_original_excel_dialog(job_data: dict, lang_code: str):
    """Drawer dialog showing raw original supplier import Excel, CDC Master List, and optional Bill PDF."""
    st.caption(t("drawer_desc", lang_code))

    tab_titles = [t("tab_orig_inv", lang_code), t("tab_orig_cdc", lang_code)]
    has_bill = bool(job_data and job_data.get("bill_bytes"))
    if has_bill:
        tab_titles.append(t("tab_orig_bill", lang_code))

    tabs = st.tabs(tab_titles)

    with tabs[0]:
        ship_bytes = job_data.get("ship_bytes") if job_data else None
        ship_name = job_data.get("ship_filename", "Supplier_Invoice.xlsx") if job_data else "Supplier_Invoice.xlsx"
        render_raw_sheet_tab(ship_bytes, ship_name, key_prefix="drawer_inv", lang_code=lang_code)

    with tabs[1]:
        cdc_bytes = job_data.get("cdc_bytes") if job_data else None
        cdc_name = job_data.get("cdc_filename", "CDC_Master.xlsx") if job_data else "CDC_Master.xlsx"
        render_raw_sheet_tab(cdc_bytes, cdc_name, key_prefix="drawer_cdc", lang_code=lang_code)

    if has_bill and len(tabs) > 2:
        with tabs[2]:
            b_meta = job_data.get("bill_meta") or {}
            st.caption(f":material/picture_as_pdf: **{job_data.get('bill_filename', 'Bill_of_Lading.pdf')}**")
            b_c1, b_c2, b_c3 = st.columns(3)
            b_c1.markdown(f"**{t('bill_no', lang_code)}:** `{b_meta.get('bl_no') or '—'}`")
            b_c2.markdown(f"**{t('bill_date', lang_code)}:** `{b_meta.get('issue_date') or '—'}`")
            b_c3.markdown(f"**Mode:** `{b_meta.get('shipping_mode') or '—'}`")
            if b_meta.get("container_seal"):
                st.caption(f"**Container / Trailer:** `{b_meta['container_seal']}`")
            if b_meta.get("carrier"):
                st.caption(f"**Carrier:** `{b_meta['carrier']}`")

            st.download_button(
                label=t("download_raw_btn", lang_code) + " (PDF)",
                data=job_data["bill_bytes"],
                file_name=job_data.get("bill_filename", "Bill_of_Lading.pdf"),
                key="drawer_dl_bill",
                width="stretch",
            )
            with st.expander("Extracted Bill Text & OCR", expanded=False):
                st.text(b_meta.get("raw_text", "No text extracted."))


def process_uploaded_files(
    ship_bytes: bytes,
    ship_name: str,
    cdc_bytes: bytes,
    cdc_name: str,
    bill_bytes: bytes = None,
    bill_name: str = "",
    template_bytes: bytes = None,
    template_name: str = "",
):
    """Extract shipping, CDC, and optional bill files, match lines, and store state."""
    shipmeta, shipitems = extract_shipping(ship_bytes, ship_name)
    packingmeta, packingitems = extract_packing(ship_bytes, ship_name)
    pairs, packing_issues = reconcile_invoice_packing(shipitems, packingitems, shipmeta, packingmeta)
    cdcmeta, cdcitems = extract_cdc(cdc_bytes, cdc_name)

    bill_meta = extract_bill(bill_bytes, bill_name) if bill_bytes else {}

    if not shipitems:
        st.error("No invoice lines found in uploaded supplier file. Check sheet headers.")
        return False
    if not cdcitems:
        st.error("No CDC quota items detected in uploaded master list.")
        return False

    glossary = load_verified_translations(TRANSLATIONS_PATH)
    res = build_results(shipitems, cdcitems, load_mappings(MAPPINGS_PATH), online=False, glossary=glossary)
    serial = st.session_state.get("job_serial", 0) + 1
    st.session_state["job_serial"] = serial
    st.session_state["job"] = {
        "shipmeta": shipmeta,
        "cdcmeta": cdcmeta,
        "cdcitems": cdcitems,
        "packingmeta": packingmeta,
        "packingitems": packingitems,
        "packing_pairs": pairs,
        "packing_issues": packing_issues,
        "base_results": res,
        "serial": serial,
        "cdc_bytes": cdc_bytes,
        "cdc_filename": cdc_name,
        "ship_bytes": ship_bytes,
        "ship_filename": ship_name,
        "bill_bytes": bill_bytes,
        "bill_filename": bill_name,
        "bill_meta": bill_meta,
        "template_bytes": template_bytes,
        "template_filename": template_name,
    }
    return True


active_job = st.session_state.get("job")
current_settings = get_settings()

default_cdc_path = get_default_cdc_path()
has_default_cdc = default_cdc_path.is_file()
default_cdc_name = current_settings.get("cdc_filename") or default_cdc_path.name

default_tpl_path = get_default_template_path()
has_default_tpl = default_tpl_path.is_file()
default_tpl_name = current_settings.get("template_filename") or default_tpl_path.name

# ── Step 1: Upload section ────────────────────────────────────
with st.container(border=True):
    col_u1, col_u2, col_u3 = st.columns(3)
    with col_u1:
        st.markdown(f"**{t('upload_inv', lang)}**")
        shipfile = st.file_uploader(
            "Upload Supplier Excel",
            type=["xls", "xlsx"],
            key="ship_uploader",
            label_visibility="collapsed",
        )
        if not shipfile:
            st.caption("Upload your supplier invoice here to start matching.")
        else:
            st.caption(f":material/check_circle: Selected: `{shipfile.name}`")
    with col_u2:
        c_title_c1, c_title_c2 = st.columns([2, 1], vertical_alignment="center")
        with c_title_c1:
            st.markdown(f"**{t('upload_cdc', lang)}**")
        with c_title_c2:
            if has_default_cdc:
                st.markdown(":green-badge[:material/check_circle: Auto-Loaded]")

        cdcfile = st.file_uploader(
            "Upload CDC Master",
            type=["xlsx"],
            key="cdc_uploader",
            label_visibility="collapsed",
            help="Default master list is auto-loaded from local machine. Upload here only to override.",
        )
        if not cdcfile and has_default_cdc:
            st.caption(f":material/check_circle: Auto-loaded: `{default_cdc_name}`")
        elif cdcfile:
            st.caption(f":material/warning: Override: `{cdcfile.name}`")

    with col_u3:
        st.markdown(f"**{t('upload_bill', lang)}**")
        billfile = st.file_uploader(
            "Upload Bill of Lading (PDF)",
            type=["pdf"],
            key="bill_uploader",
            label_visibility="collapsed",
        )
        if not billfile:
            st.caption("Optional: B/L or transport document.")
        else:
            st.caption(f":material/check_circle: Selected: `{billfile.name}`")
            if active_job and (active_job.get("bill_bytes") != billfile.getvalue() or not active_job.get("bill_meta")):
                active_job["bill_bytes"] = billfile.getvalue()
                active_job["bill_filename"] = billfile.name
                active_job["bill_meta"] = extract_bill(billfile.getvalue(), billfile.name)
                st.session_state["job"] = active_job
                st.rerun()

    # Optional Custom Permit Template Expander
    active_tpl_name = active_job.get("template_filename") if active_job else default_tpl_name
    tpl_badge = "Auto-Loaded" if has_default_tpl else "Default"
    with st.expander(f":material/style: {t('custom_template_title', lang)} (:green[{tpl_badge}]: `{active_tpl_name}`)", expanded=False):
        st.caption(f"Active template: `{active_tpl_name}`. Upload below only to temporarily override for this session.")
        custom_tpl = st.file_uploader(
            "Custom Permit Template (.xlsx)",
            type=["xlsx"],
            key="tpl_uploader",
            label_visibility="collapsed",
        )
        if custom_tpl and active_job:
            if active_job.get("template_bytes") != custom_tpl.getvalue():
                active_job["template_bytes"] = custom_tpl.getvalue()
                active_job["template_filename"] = custom_tpl.name
                st.session_state["job"] = active_job
                st.rerun()

        if active_job and active_job.get("template_bytes") and active_job.get("template_filename") != default_tpl_name:
            if st.button("Reset to default template", icon=":material/restart_alt:", key="reset_tpl_btn"):
                active_job["template_bytes"] = get_default_template_bytes()
                active_job["template_filename"] = default_tpl_name
                st.session_state["job"] = active_job
                st.rerun()

    can_process = bool(shipfile and (cdcfile or has_default_cdc))
    btn_process = st.button(
        t("extract_btn", lang),
        type="primary",
        width="stretch",
        disabled=not can_process,
        icon=":material/play_arrow:",
    )

    if btn_process and can_process:
        if cdcfile:
            c_bytes = cdcfile.getvalue()
            c_name = cdcfile.name
        else:
            c_bytes = get_default_cdc_bytes()
            c_name = default_cdc_name

        tpl_bytes = custom_tpl.getvalue() if custom_tpl else get_default_template_bytes()
        tpl_name = custom_tpl.name if custom_tpl else default_tpl_name
        b_bytes = billfile.getvalue() if billfile else None
        b_name = billfile.name if billfile else ""
        if process_uploaded_files(
            shipfile.getvalue(),
            shipfile.name,
            c_bytes,
            c_name,
            b_bytes,
            b_name,
            tpl_bytes,
            tpl_name,
        ):
            st.rerun()

# If no job is active, stop
if not active_job:
    st.info("Upload a supplier invoice to begin matching against your approved CDC master list.")
    st.stop()

# ── Active job workspace ─────────────────────────────────────
job = active_job
shipmeta, cdcmeta = job["shipmeta"], job["cdcmeta"]
base_results = job["base_results"]
serial = job["serial"]

# Handle text overrides/corrections
overrides = {}
for index, r in enumerate(base_results):
    edited = st.session_state.get(f"translation_{serial}_{index}")
    if isinstance(edited, str) and edited.strip() and edited.strip() != r["query"]:
        overrides[(r["sheet"], r["row"])] = edited.strip()
if overrides:
    changed = [r for r in base_results if (r["sheet"], r["row"]) in overrides]
    revised = build_results(changed, job["cdcitems"], load_mappings(MAPPINGS_PATH), overrides=overrides)
    by_row = {(r["sheet"], r["row"]): r for r in revised}
    results = [by_row.get((r["sheet"], r["row"]), r) for r in base_results]
else:
    results = base_results

# User candidate selections
selections = []
for index, r in enumerate(results):
    saved_pick = st.session_state.get(f"pick_{serial}_{index}")
    candidates = r["candidates"]
    if saved_pick is not None:
        chosen = saved_pick
    elif candidates:
        chosen = (candidates[0]["sheet"], candidates[0]["row"])
    else:
        chosen = None

    selected = next((x for x in candidates if (x["sheet"], x["row"]) == chosen), None)
    dec = st.session_state.get(f"dec_{serial}_{index}", "Approved" if selected else "Unmatched")
    note = st.session_state.get(f"note_{serial}_{index}", "")
    selections.append({"match": selected, "decision": dec, "notes": note})

# Executive Metrics
totals = job["packingmeta"].get("printed_totals", {})
pkg_count = totals.get("packages") or sum(item.get("packages") or 0 for item in job["packingitems"])
gw_count = totals.get("gross_weight") or sum(item.get("gross_weight") or 0 for item in job["packingitems"])
total_val_usd = sum(r.get("total") or 0.0 for r in results)
matched_count = sum(bool(s.get("match")) for s in selections)

with st.container(horizontal=True):
    st.metric(t("kpi_lines", lang), f"{len(results)} items", f"${total_val_usd:,.2f} USD", border=True)
    st.metric(t("kpi_packing", lang), f"{pkg_count:g} pkgs", f"{gw_count:,.1f} kg GW", border=True)
    st.metric(t("kpi_matches", lang), f"{matched_count} of {len(results)} matched", t("kpi_high_conf", lang), border=True)
    category_tokens = (shipmeta.get("category", "") + " " + " ".join(r["chinese"] for r in results)).lower()
    cat_label = (
        "II - RAW MATERIALS"
        if any(w in category_tokens for w in ["fabric", "elastic", "zipper", "label", "string", "stopper", "ribbon", "thread"])
        else "I - MACHINERY"
    )
    st.metric("Exemption Category", cat_label, "100% Formulas Protected", border=True)

# Date Priority: 1. Bill of Lading Date, 2. Supplier Invoice Date, 3. Current Date
bill_meta = job.get("bill_meta") or {}
permit_date_str = None
if bill_meta.get("issue_date"):
    permit_date_str = bill_meta["issue_date"]
elif shipmeta.get("invoice_date"):
    raw_inv_date = shipmeta["invoice_date"]
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d", "%d-%b-%Y"):
        try:
            permit_date_str = datetime.strptime(str(raw_inv_date).strip(), fmt).strftime("%d-%b-%Y")
            break
        except Exception:
            pass
if not permit_date_str:
    permit_date_str = datetime.now().strftime("%d-%b-%Y")

shipping_mode_val = bill_meta.get("shipping_mode") or shipmeta.get("shipping_mode") or "BY SEA"
bl_number_val = bill_meta.get("bl_no") or "—"
has_bill_doc = bool(bill_meta.get("has_bill") or job.get("bill_bytes"))

with st.container(border=True):
    c_info1, c_info2, c_info3, c_act = st.columns([3.5, 3.0, 2.5, 2.0], vertical_alignment="center")
    with c_info1:
        st.markdown(f"**{t('inv_consignee', lang)}:** `{shipmeta.get('consignee') or 'Unknown'}`  \n**{t('inv_no', lang)}:** `{shipmeta.get('invoice_no') or 'Unknown'}` ({permit_date_str})")
    with c_info2:
        st.markdown(f"**Shipper:** `{shipmeta.get('supplier') or 'Unknown'}`  \n**QIP / CIB:** `{cdcmeta.get('qip') or '211/26'}`")
    with c_info3:
        st.markdown(f"**{t('shipping_mode', lang)}:** `{shipping_mode_val}`  \n**{t('bill_no', lang)}:** `{bl_number_val}`")
    with c_act:
        if st.button(t("view_original_btn", lang), icon=":material/visibility:", width="stretch"):
            show_original_excel_dialog(job, lang)

if has_bill_doc:
    reconciliation = reconcile_bill_and_shipping(
        bill_meta=bill_meta,
        shipmeta=shipmeta,
        packingmeta=job.get("packingmeta") or {},
        invoice_items=results,
    )
    is_matched = reconciliation.get("is_fully_matched", False)
    recon_status = reconciliation.get("overall_status", "MATCH")

    if is_matched:
        st.success(
            f"**{t('bl_reconcile_100', lang)}**: Transport Mode ({shipping_mode_val}), Consignee & Bill Address, Total Packages ({pkg_count:g}), Gross Weight ({gw_count:,.1f} kg), and Goods Descriptions align between B/L and INV/PL.",
            icon=":material/verified:"
        )
    elif recon_status == "WARNING":
        st.warning(
            f"**{t('bl_reconcile_title', lang)}**: Verified with notes. Review checklist below.",
            icon=":material/info:"
        )
    else:
        st.error(
            f"**{t('bl_reconcile_warn', lang)}**: Discrepancies detected between B/L and Invoice/Packing List.",
            icon=":material/warning:"
        )

    with st.expander(
        f":material/fact_check: **{t('bl_reconcile_title', lang)}** "
        f"({'✅ ' + t('bl_reconcile_100', lang) if is_matched else '⚠️ Review Notes'})",
        expanded=not is_matched
    ):
        if reconciliation.get("acc_rule_applied"):
            st.info(
                f":material/auto_awesome: **3+ Accessories Matching Rule:** "
                f"Invoice contains **{reconciliation.get('accessories_count')}** garment accessories. "
                f"Per customs declaration standard, they match and are declared collectively as **`GARMENT ACCESSORIES`** on the Bill of Lading.",
                icon=":material/info:"
            )

        chk_rows = []
        for c in reconciliation.get("checklist", []):
            st_badge = "✅ Match" if c["status"] == "MATCH" else ("⚠️ Note" if c["status"] == "WARNING" else "❌ Mismatch")
            chk_rows.append({
                "Parameter": c["item"],
                "Bill of Lading (B/L)": c["bill_value"],
                "Invoice & Packing List": c["inv_value"],
                "Match Status": st_badge,
                "Verification Details": c["note"]
            })

        st.dataframe(pd.DataFrame(chk_rows), hide_index=True, width="stretch")

periods = detect_period_columns(job["cdc_bytes"], sheet_name=cdcmeta.get("sheet"))
consolidation = consolidate_deductions(results, selections)
clean_inv = re.sub(r"[^a-zA-Z0-9]", "_", shipmeta.get("invoice_no") or "invoice")
qip_input = cdcmeta.get("qip") or "211/26"

app_settings = get_settings()
auto_discount_kg = app_settings.get("auto_discount_kg", True)
kg_discount_rate = float(app_settings.get("kg_discount_per_pkg", 1.0))

permit_bytes = generate_permit_document(
    shipmeta,
    cdcmeta,
    results,
    selections,
    job["packingitems"],
    job["packing_pairs"],
    job["packing_issues"],
    qip_reference=qip_input,
    template_bytes=job.get("template_bytes"),
    bill_meta=bill_meta,
    auto_discount_kg=auto_discount_kg,
    discount_rate_per_pkg=kg_discount_rate,
)

if periods:
    period_labels = [p["label"] for p in periods]
    suggested_idx = suggest_period_from_date(shipmeta.get("invoice_date", ""), periods)
    default_index = next((i for i, p in enumerate(periods) if p["col_idx"] == suggested_idx), 0)
    saved_period_label = st.session_state.get(f"period_pick_{serial}")
    if saved_period_label and any(p["label"] == saved_period_label for p in periods):
        selected_period = next(p for p in periods if p["label"] == saved_period_label)
        selected_period_label = saved_period_label
    else:
        selected_period = periods[default_index]
        selected_period_label = selected_period["label"]

    add_existing = st.session_state.get(f"sum_existing_{serial}", True)
    clean_company = re.sub(r"[^a-zA-Z0-9]", "_", cdcmeta.get("company") or shipmeta.get("consignee") or "company")
    clean_period = re.sub(r"[^a-zA-Z0-9]", "_", selected_period["label"])

    updated_master_bytes = apply_deductions_to_cdc_workbook(
        job["cdc_bytes"],
        consolidation["consolidated"],
        target_col_idx=selected_period["col_idx"],
        sheet_name=selected_period.get("sheet_name"),
        add_to_existing=add_existing,
        amount_col_idx=selected_period.get("amount_col_idx"),
    )
else:
    period_labels = []
    default_index = 0
    selected_period_label = ""
    add_existing = True
    clean_company = ""
    clean_period = ""
    updated_master_bytes = None


def format_quantity(val):
    if val is None:
        return "—"
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


# ── The 5 core workspace tabs ─────────────────────────────────
tab_items, tab_permit_inv, tab_permit_pl, tab_cutstock, tab_audit = st.tabs([
    t("tab_matching", lang),
    t("tab_permit_inv", lang),
    t("tab_permit_pl", lang),
    t("tab_cutstock", lang),
    t("tab_audit", lang),
])

# TAB 1: REVIEW CDC MATCHES (EASY-TO-UNDERSTAND TABLE)
with tab_items:
    col_m1, col_m2 = st.columns([3, 1], vertical_alignment="center")
    col_m1.caption(t('matching_hint', lang))
    if col_m2.button(t('accept_all_btn', lang), icon=":material/done_all:", width="stretch"):
        for index, r in enumerate(results):
            if r['candidates']:
                st.session_state[f'pick_{serial}_{index}'] = (r['candidates'][0]['sheet'], r['candidates'][0]['row'])
                st.session_state[f'dec_{serial}_{index}'] = 'Approved'
        st.rerun()

    # ====================================================
    # 1. OVERVIEW MATCHING TABLE (SUMMARY DATAFRAME)
    # ====================================================
    overview_table = []
    has_any_converted = False
    sorted_items = sorted(enumerate(results), key=_get_item_cdc_sort_key)
    for index, r in sorted_items:
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

        th_price_val = match['unit_price'] if match and match.get('unit_price') is not None else r.get('unit_price')
        overview_table.append({
            t('th_cdc_no', lang): cdc_no,
            t('th_orig_desc', lang): orig_desc,
            t('th_cdc_desc', lang): cdc_desc,
            t('th_qty', lang): format_quantity(cdc_qty),
            t('th_orig_unit', lang): raw_unit or '—',
            t('th_cdc_unit', lang): cdc_unit,
            t('th_price', lang): f"${th_price_val:,.2f}" if th_price_val is not None else '—',
            t('th_status', lang): status_text,
        })
    st.dataframe(pd.DataFrame(overview_table), hide_index=True, width="stretch")

    st.space("small")

    # ====================================================
    # 2. INTERACTIVE FINE-TUNING GRID (EDIT & SELECT)
    # ====================================================
    with st.expander(":material/tune: Assign CDC Quota & Fine-Tune", expanded=False):
        st.caption("Click on any dropdown in the **Assign CDC Quota** column to select a different quota match, or click the tune icon to adjust search keywords.")

        col_w = [0.8, 3.2, 1.2, 3.8, 1.2, 1.0, 1.0, 0.6]
        h_cols = st.columns(col_w, vertical_alignment="center")
        h_cols[0].markdown("**CDC #**")
        h_cols[1].markdown("**Invoice Item**")
        h_cols[2].markdown("**Inv Qty**")
        h_cols[3].markdown("**Assign CDC Quota**")
        h_cols[4].markdown("**CDC Qty**")
        h_cols[5].markdown("**Unit Price**")
        h_cols[6].markdown("**Status**")
        h_cols[7].markdown("")

        st.divider()

        for index, r in sorted_items:
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

            if match:
                raw_s = str(match.get('serial') or match['row'])
                cdc_no = raw_s.lstrip('#').strip()
            else:
                cdc_no = f"L{r['row']}"

            orig_desc = r['chinese'] or r['english_provided'] or f"Item {r['row']}"
            th_price_val = match['unit_price'] if match and match.get('unit_price') is not None else r.get('unit_price')

            candidates = r['candidates']
            top_score = candidates[0]['score'] if candidates else 0

            candidate_ids = [None] + [(x['sheet'], x['row']) for x in candidates]
            option_names = {None: '— Unmatched'}
            option_names.update({
                (x['sheet'], x['row']): f"#{x.get('serial', x['row'])}: {x['description']} ({x['unit']}) · {x['score']:.0f}%"
                for x in candidates
            })
            current_pick = (match['sheet'], match['row']) if match else None
            default_idx = candidate_ids.index(current_pick) if current_pick in candidate_ids else 0

            r_cols = st.columns(col_w, vertical_alignment="center")
            r_cols[0].markdown(f"**#{cdc_no}**")
            r_cols[1].write(orig_desc)
            r_cols[2].write(f"{format_quantity(raw_qty)} {raw_unit or '—'}")
            r_cols[3].selectbox(
                "Assign CDC",
                options=candidate_ids,
                index=default_idx,
                format_func=lambda k: option_names[k],
                key=f'pick_{serial}_{index}',
                label_visibility="collapsed"
            )
            r_cols[4].write(f"{format_quantity(cdc_qty)} {cdc_unit}")
            r_cols[5].write(f"${th_price_val:,.2f}" if th_price_val is not None else "—")
            if top_score >= 99:
                r_cols[6].markdown(":green-badge[100%]")
            elif top_score >= 60:
                r_cols[6].markdown(f":orange-badge[{top_score:.0f}%]")
            else:
                r_cols[6].markdown(":red-badge[Unmatched]")

            with r_cols[7].popover("", icon=":material/tune:", help="Tune search keyword or save translation to memory"):
                st.markdown(f"**Line {r['row']}:** `{orig_desc}`")
                edited = st.text_input(
                    "English search keyword",
                    value=base_results[index]['query'],
                    key=f'translation_{serial}_{index}',
                    label_visibility="visible"
                )
                if st.button("Save to Memory", icon=":material/save:", key=f'save_tr_{serial}_{index}', width="stretch"):
                    try:
                        save_verified_translation(TRANSLATIONS_PATH, r['chinese'], edited)
                        st.toast("Saved translation to memory!", icon=":material/check:")
                    except Exception as e:
                        st.error(f'Could not save: {e}')

# TAB 2: INVOICE PERMIT PREVIEW
with tab_permit_inv:
    st.markdown(f"#### {t('permit_inv_title', lang)}")
    st.caption(t("permit_inv_desc", lang))

    with st.container(border=True):
        c_i1, c_i2, c_i3 = st.columns(3)
        c_i1.caption(f"**Shipper:** {shipmeta.get('supplier') or '—'}")
        c_i2.caption(f"**Invoice No:** `{shipmeta.get('invoice_no') or '—'}` ({permit_date_str})")
        tpl_badge_text = f"`{job.get('template_filename')}` (Custom)" if job.get("template_bytes") else "Default (`1-26TKYM164.xlsx`)"
        c_i3.caption(f"**Template:** {tpl_badge_text}")

    consolidated_permit_items = consolidate_permit_items(
        results,
        selections,
        job["packing_pairs"],
        auto_discount_kg=auto_discount_kg,
        discount_rate_per_pkg=kg_discount_rate,
    )
    permit_inv_rows = []
    total_inv_amount = 0.0
    for idx_item, item in enumerate(consolidated_permit_items):
        cdc_num = item["cdc_num"]
        desc = item["desc"]
        qty = item["qty"]
        unit = item["unit"]
        price = item["price"]
        line_amount = round(qty * price, 2)
        total_inv_amount += line_amount

        permit_inv_rows.append({
            t("th_item_no", lang): cdc_num,
            t("th_permit_desc", lang): desc,
            t("th_permit_qty", lang): format_quantity(qty),
            t("th_permit_unit", lang): unit,
            t("th_unit_price_usd", lang): f"${price:,.2f}" if price is not None else "—",
            t("th_amount_usd", lang): f"${line_amount:,.2f}",
        })

    st.dataframe(pd.DataFrame(permit_inv_rows), hide_index=True, width="stretch")
    cons_note = f" · {len(results)} items combined into {len(consolidated_permit_items)} CDC lines" if len(consolidated_permit_items) < len(results) else ""
    has_discounted = any(item.get("is_kg_discounted") for item in consolidated_permit_items)
    disc_note = f" · Tare discount: {kg_discount_rate:g} kg/pkg deducted for Kg items" if has_discounted else ""
    st.caption(f"Total Declared Value: **${total_inv_amount:,.2f} USD**{cons_note}{disc_note} · Official CDC descriptions and units applied.")

# TAB 3: PACKING LIST PERMIT PREVIEW
with tab_permit_pl:
    st.markdown(f"#### {t('permit_pl_title', lang)}")
    st.caption(t("permit_pl_desc", lang))

    if job["packing_issues"]:
        for issue in job["packing_issues"]:
            st.error(f"Issue: {issue}")
    else:
        st.caption(f":material/check_circle: Verification: {len(results)} items agree with packing list ({pkg_count:g} pkgs, {gw_count:,.1f} kg GW).")

    permit_pl_rows = []
    tot_pkgs = 0
    tot_nw = 0.0
    tot_gw = 0.0

    for idx_item, item in enumerate(consolidated_permit_items):
        desc = item["desc"]
        qty = item["qty"]
        unit = item["unit"]
        pkgs = item["pkgs"]
        nw = item["nw"]
        gw = item["gw"]

        if pkgs: tot_pkgs += pkgs
        if nw: tot_nw += nw
        if gw: tot_gw += gw

        permit_pl_rows.append({
            t("th_packages", lang): format_quantity(pkgs),
            t("th_permit_desc", lang): desc,
            t("th_permit_qty", lang): format_quantity(qty),
            t("th_permit_unit", lang): unit,
            t("th_net_weight", lang): f"{nw:,.1f}" if nw is not None else "—",
            t("th_gross_weight", lang): f"{gw:,.1f}" if gw is not None else "—",
        })

    st.dataframe(pd.DataFrame(permit_pl_rows), hide_index=True, width="stretch")
    st.caption(f"Total Packages: **{tot_pkgs:g} pkgs** · Total Net Weight: **{tot_nw:,.1f} kg** · Total Gross Weight: **{tot_gw:,.1f} kg**{disc_note}")

# TAB 4: CUT-STOCK BREAKDOWN
with tab_cutstock:
    st.markdown(f"#### {t('cons_items_title', lang)}")
    if periods:
        col_p_sel, col_p_chk = st.columns([3, 2], vertical_alignment="bottom")
        with col_p_sel:
            new_p = st.selectbox(
                t("target_period", lang),
                options=period_labels,
                index=period_labels.index(selected_period_label) if selected_period_label in period_labels else default_index,
                key=f"period_pick_{serial}",
            )
            if new_p != selected_period_label:
                st.rerun()
        with col_p_chk:
            new_add = st.checkbox(
                t("sum_existing", lang),
                value=add_existing,
                help=t("sum_existing_help", lang),
                key=f"sum_existing_{serial}",
            )
            if new_add != add_existing:
                st.rerun()

    cons_rows = []
    for item in consolidation["consolidated"]:
        status_icon = ":material/warning:" if item["is_exceeded"] else ":material/check_circle:"
        cons_rows.append({
            t("th_cdc_row", lang): f"#{item['cdc_serial'] or item['cdc_row']}",
            t("th_cdc_desc", lang): item["cdc_description"],
            t("th_cdc_unit", lang): item["cdc_unit"],
            t("th_approved", lang): f"{item['approved']:,.0f}" if item["approved"] else "—",
            t("th_prev_rem", lang): f"{item['remaining']:,.0f}" if item["remaining"] is not None else "—",
            t("th_deduct_qty", lang): f"{item['deduct_qty']:,.0f}",
            t("th_new_rem", lang): f"{item['new_remaining']:,.0f}" if item["new_remaining"] is not None else "—",
            t("th_status", lang): status_icon,
            t("th_usd", lang): f"${item['total_invoice_usd']:,.2f}",
        })
    if cons_rows:
        st.dataframe(pd.DataFrame(cons_rows), hide_index=True, width="stretch")
    if consolidation["has_exceeded"]:
        st.error(t("exceeded_warning", lang))

# TAB 5: AUDIT REPORT & RAW INSPECTION
with tab_audit:
    c_aud1, c_aud2 = st.columns(2)
    with c_aud1:
        st.markdown(f"#### {t('doc2_title', lang)}")
        st.caption(t("doc2_desc", lang))
        audit_bytes = export_report(shipmeta, cdcmeta, results, selections)
        st.download_button(
            t("doc2_btn", lang),
            data=audit_bytes,
            file_name=f"CDC_Matching_Audit_{clean_inv}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            icon=":material/download:",
            width="stretch",
        )
    with c_aud2:
        st.markdown("#### Spreadsheet Drawer")
        st.caption("Inspect raw Excel sheets with exact 1-indexed rows and A..Z column headers.")
        if st.button("Open Spreadsheet Viewer", icon=":material/table_chart:", width="stretch"):
            show_original_excel_dialog(job, lang)

# ── Bottom Action: 2 primary download buttons ─────────────────
st.space("small")
with st.container(border=True):
    col_dl1, col_dl2 = st.columns(2)
    with col_dl1:
        st.download_button(
            label=t("permit_download_btn", lang),
            data=permit_bytes,
            file_name=f"Permit_Application_{clean_inv}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
            icon=":material/description:",
            width="stretch",
            key=f"dl_permit_btn_{serial}",
        )
    with col_dl2:
        if periods and updated_master_bytes:
            st.download_button(
                label=t("cutstock_download_btn", lang, period=selected_period_label),
                data=updated_master_bytes,
                file_name=f"CDC_Master_Deducted_{clean_company}_{clean_period}_{clean_inv}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary",
                icon=":material/inventory_2:",
                width="stretch",
                key=f"dl_cutstock_btn_{serial}",
            )

