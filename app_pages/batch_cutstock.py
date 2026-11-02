"""Batch Cut-Stock — cut stock for multiple shipments (e.g. 4 shipments) at once.

Supports multi-file upload or registered shipment selection to aggregate deductions
and update the official CDC Master List Excel in a single step.
"""

from io import BytesIO
from pathlib import Path
import re
import pandas as pd
import streamlit as st

from services.cutstock_updater import (
    apply_deductions_to_cdc_workbook,
    detect_period_columns,
    suggest_period_from_date,
)
from services.extraction import extract_cdc, extract_shipping
from services.matching import build_results, convert_unit_quantity, load_mappings
from services.settings_store import (
    get_default_cdc_bytes,
    get_default_cdc_path,
    get_settings,
)
from services.shipping_store import list_documents, list_shipments, seed_tk164
from services.translation_memory import load_verified_translations

ROOT = Path(__file__).resolve().parent.parent
MAPPINGS_PATH = ROOT / "data" / "approved_mappings.json"
TRANSLATIONS_PATH = ROOT / "data" / "verified_translations.sqlite3"
DB_PATH = ROOT / "data" / "shipping.sqlite3"

lang = st.session_state.get("lang", "en")
app_settings = get_settings()

default_cdc_path = get_default_cdc_path()
has_default_cdc = default_cdc_path.is_file()
default_cdc_name = app_settings.get("cdc_filename") or default_cdc_path.name

st.caption("Consolidate multiple import shipments (e.g. 4 shipments) and deduct their combined quantities into the CDC Master List Excel all at once.")

# ── Select input mode ─────────────────────────────────────────
mode = st.segmented_control(
    "Input method",
    ["Multi-file upload", "From shipping workspace"],
    default="Multi-file upload",
)

st.space("small")

# ── CDC Master List source ────────────────────────────────────
with st.container(border=True):
    st.subheader("1. CDC Master List", icon=":material/verified:")
    c_m1, c_m2 = st.columns([3, 2], vertical_alignment="center")
    with c_m1:
        if has_default_cdc:
            st.caption(f":material/check_circle: Auto-loaded: `{default_cdc_name}`")
        else:
            st.caption("Please upload a CDC Master List.")
    with c_m2:
        cdc_override = st.file_uploader(
            "Override CDC Master",
            type=["xlsx"],
            key="batch_cdc_uploader",
            label_visibility="collapsed",
        )

if cdc_override:
    cdc_bytes = cdc_override.getvalue()
    cdc_filename = cdc_override.name
else:
    cdc_bytes = get_default_cdc_bytes()
    cdc_filename = default_cdc_name

if not cdc_bytes:
    st.warning("No CDC Master List available. Upload one to proceed.")
    st.stop()

# ── Shipments selection ───────────────────────────────────────
shipment_batches = []

if mode == "Multi-file upload":
    with st.container(border=True):
        st.subheader("2. Upload supplier invoices (Select multiple files)", icon=":material/upload_file:")
        st.caption("Select 2, 3, 4, or more supplier invoices (.xls / .xlsx) to deduct together.")
        uploaded_files = st.file_uploader(
            "Upload files",
            type=["xls", "xlsx"],
            accept_multiple_files=True,
            key="batch_multi_uploader",
            label_visibility="collapsed",
        )
        if uploaded_files:
            st.success(f"{len(uploaded_files)} shipment file(s) selected.")
            for f in uploaded_files:
                shipment_batches.append({
                    "name": f.name,
                    "bytes": f.getvalue(),
                    "source": "upload",
                })
else:
    # From shipping workspace database
    seed_tk164(DB_PATH, ROOT)
    db_shipments = list_shipments(DB_PATH)
    with st.container(border=True):
        st.subheader("2. Select shipments from workspace", icon=":material/folder_open:")
        if not db_shipments:
            st.info("No shipments in database. Switch to 'Multi-file upload' to upload files directly.")
        else:
            selected_ids = []
            for s in db_shipments:
                docs = list_documents(DB_PATH, s["id"])
                inv_docs = [d for d in docs if "Invoice" in d.get("kind", "") or d.get("filename", "").endswith((".xls", ".xlsx"))]
                has_doc = len(inv_docs) > 0
                label = f"{s['company']} · {s['reference']} ({s['status']}) — {len(inv_docs)} invoice file(s)"
                if st.checkbox(label, value=has_doc, key=f"sel_ship_{s['id']}"):
                    for d in inv_docs:
                        doc_path = ROOT / d.get("relative_path", "")
                        if doc_path.is_file():
                            shipment_batches.append({
                                "name": f"{s['reference']}_{d['filename']}",
                                "bytes": doc_path.read_bytes(),
                                "source": s["reference"],
                            })

if not shipment_batches:
    st.info("Select or upload at least 1 shipment invoice to see consolidated deductions.")
    st.stop()

# ── Process & Consolidate across all shipments ────────────────
with st.spinner("Extracting items and matching to CDC master list..."):
    cdcmeta, cdcitems = extract_cdc(cdc_bytes, cdc_filename)
    mappings = load_mappings(MAPPINGS_PATH)
    glossary = load_verified_translations(TRANSLATIONS_PATH)

    all_shipment_details = []
    cdc_grouping = {}  # key: (sheet, row) -> {cdc_info, total_deduct, shipments: []}

    auto_discount = app_settings.get("auto_discount_kg", True)
    discount_rate = float(app_settings.get("kg_discount_per_pkg", 1.0))

    for batch in shipment_batches:
        smeta, sitems = extract_shipping(batch["bytes"], batch["name"])
        if not sitems:
            continue
        res = build_results(sitems, cdcitems, mappings, online=False, glossary=glossary)

        inv_num = smeta.get("invoice_no") or batch["name"]
        inv_date = smeta.get("invoice_date") or "—"
        batch_total_val = sum(r.get("total") or 0.0 for r in res)
        all_shipment_details.append({
            "name": batch["name"],
            "invoice_no": inv_num,
            "date": inv_date,
            "supplier": smeta.get("supplier") or "—",
            "items_count": len(sitems),
            "total_val": batch_total_val,
        })

        for r in res:
            cands = r.get("candidates")
            if not cands:
                continue
            best = cands[0]
            key = (best["sheet"], best["row"])

            if key not in cdc_grouping:
                cdc_grouping[key] = {
                    "cdc_sheet": best["sheet"],
                    "cdc_row": best["row"],
                    "cdc_serial": best.get("serial", ""),
                    "cdc_desc": best["description"],
                    "cdc_unit": best["unit"],
                    "approved": best.get("approved"),
                    "remaining": best.get("remaining"),
                    "total_deduct": 0.0,
                    "total_usd": 0.0,
                    "shipments": [],
                }

            qty = float(r.get("qty") or 0.0)
            cdc_qty, _ = convert_unit_quantity(qty, r.get("unit", ""), best["unit"])

            cdc_grouping[key]["total_deduct"] += cdc_qty
            cdc_grouping[key]["total_usd"] += float(r.get("total") or 0.0)
            cdc_grouping[key]["shipments"].append({
                "invoice_no": inv_num,
                "item_desc": r.get("english_provided") or r.get("chinese", ""),
                "qty": qty,
                "unit": r.get("unit", ""),
                "cdc_qty": cdc_qty,
            })

# ── Summary of shipments in this batch ────────────────────────
with st.container(border=True):
    st.subheader(f"3. Processed shipments ({len(all_shipment_details)} invoices)", icon=":material/receipt_long:")
    s_rows = []
    for s in all_shipment_details:
        s_rows.append({
            "File": s["name"],
            "Invoice No": s["invoice_no"],
            "Date": s["date"],
            "Supplier": s["supplier"],
            "Items": s["items_count"],
            "Total USD": f"${s['total_val']:,.2f}",
        })
    st.dataframe(pd.DataFrame(s_rows), hide_index=True, width="stretch")

# ── Consolidated CDC Deductions table ─────────────────────────
with st.container(border=True):
    st.subheader("4. Combined CDC Master Deductions", icon=":material/calculate:")
    st.caption("All quantities from the shipments above are summed up for each CDC Master Item:")

    cons_rows = []
    deductions_payload = []
    has_exceeded = False

    for item in sorted(cdc_grouping.values(), key=lambda x: (x["cdc_sheet"], x["cdc_row"])):
        rem = item["remaining"]
        appr = item["approved"]
        base_bal = rem if rem is not None else appr
        deduct_val = round(item["total_deduct"], 4)
        new_rem = round(base_bal - deduct_val, 4) if base_bal is not None else None
        is_exc = base_bal is not None and deduct_val > base_bal
        if is_exc:
            has_exceeded = True

        status_badge = ":material/warning: Exceeded" if is_exc else ":material/check_circle: OK"
        invoices_list = ", ".join(sorted({sh["invoice_no"] for sh in item["shipments"]}))

        cons_rows.append({
            "CDC #": f"#{item['cdc_serial'] or item['cdc_row']}",
            "Description": item["cdc_desc"],
            "Unit": item["cdc_unit"],
            "Quota Approved": f"{appr:,.0f}" if appr else "—",
            "Prev Remaining": f"{rem:,.0f}" if rem is not None else "—",
            "Batch Deduct Qty": f"{deduct_val:,.1f}",
            "New Remaining": f"{new_rem:,.1f}" if new_rem is not None else "—",
            "Total USD": f"${item['total_usd']:,.2f}",
            "Invoices Combined": invoices_list,
            "Status": status_badge,
        })

        deductions_payload.append({
            "cdc_sheet": item["cdc_sheet"],
            "cdc_row": item["cdc_row"],
            "deduct_qty": deduct_val,
            "total_invoice_usd": round(item["total_usd"], 2),
            "amount_col_idx": None,
        })

    st.dataframe(pd.DataFrame(cons_rows), hide_index=True, width="stretch")

    if has_exceeded:
        st.error("Warning: One or more items exceed approved CDC quota balance.")

# ── Target month & 1-click Download ───────────────────────────
periods = detect_period_columns(cdc_bytes, sheet_name=cdcmeta.get("sheet"))
if periods:
    with st.container(border=True):
        st.subheader("5. Update CDC Master List Excel", icon=":material/download:")
        c_p1, c_p2 = st.columns([3, 2], vertical_alignment="bottom")
        with c_p1:
            period_labels = [p["label"] for p in periods]
            chosen_period_label = st.selectbox("Target deduction column", options=period_labels, index=0)
            chosen_period = next(p for p in periods if p["label"] == chosen_period_label)
        with c_p2:
            add_to_existing = st.checkbox("Add to existing month numbers (Sum)", value=True, help="If the month column already has numbers, add to them instead of overwriting.")

        updated_master = apply_deductions_to_cdc_workbook(
            cdc_bytes,
            deductions_payload,
            target_col_idx=chosen_period["col_idx"],
            sheet_name=chosen_period.get("sheet_name"),
            add_to_existing=add_to_existing,
            amount_col_idx=chosen_period.get("amount_col_idx"),
        )

        clean_period_name = re.sub(r"[^a-zA-Z0-9]", "_", chosen_period_label)
        st.download_button(
            label=f"Download Deducted CDC Master ({len(all_shipment_details)} Shipments into {chosen_period_label})",
            data=updated_master,
            file_name=f"CDC_Master_Batch_Deducted_{clean_period_name}_{len(all_shipment_details)}_Shipments.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
            icon=":material/inventory_2:",
            width="stretch",
        )
else:
    st.info("No deduction period columns (e.g. AUG 2026, SEP 2026) detected in this CDC master list.")

