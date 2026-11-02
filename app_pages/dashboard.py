"""Dashboard — executive overview of import activity, shipment tracking, and CDC quota health."""

from pathlib import Path
import pandas as pd
import streamlit as st

from services.extraction import extract_cdc
from services.i18n import t
from services.settings_store import (
    get_default_cdc_bytes,
    get_default_cdc_path,
    get_settings,
)
from services.shipping_store import list_shipments, seed_tk164

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "shipping.sqlite3"
seed_tk164(DB_PATH, ROOT)

lang = st.session_state.get("lang", "en")
active_job = st.session_state.get("job")
settings = get_settings()

default_cdc_path = get_default_cdc_path()
has_default_cdc = default_cdc_path.is_file()
default_cdc_name = settings.get("cdc_filename") or default_cdc_path.name

# ── If an active invoice job is loaded ─────────────────────────
if active_job:
    shipmeta = active_job["shipmeta"]
    cdcmeta = active_job["cdcmeta"]
    results = active_job["base_results"]
    packingmeta = active_job.get("packingmeta", {})
    bill_meta = active_job.get("bill_meta") or {}

    totals = packingmeta.get("printed_totals", {})
    pkg_count = totals.get("packages") or sum(
        item.get("packages") or 0 for item in active_job.get("packingitems", [])
    )
    gw_count = totals.get("gross_weight") or sum(
        item.get("gross_weight") or 0 for item in active_job.get("packingitems", [])
    )
    total_val_usd = sum(r.get("total") or 0.0 for r in results)
    matched_count = sum(1 for r in results if r.get("candidates"))

    # KPI row
    with st.container(horizontal=True):
        st.metric("Invoice items", f"{len(results)} items", f"${total_val_usd:,.0f} USD", border=True)
        st.metric("Packages", f"{pkg_count:g} pkgs", f"{gw_count:,.0f} kg gross", border=True)
        st.metric("CDC matches", f"{matched_count}/{len(results)}",
                  delta=f"{matched_count / len(results) * 100:.0f}%" if results else None,
                  border=True)
        category_tokens = (shipmeta.get("category", "") + " " + " ".join(r.get("chinese", "") for r in results)).lower()
        cat_label = "Raw materials" if any(w in category_tokens for w in ["fabric", "elastic", "zipper", "label", "thread"]) else "Machinery"
        st.metric("Exemption Category", cat_label, "100% Formulas Protected", border=True)

    st.space("small")

    col_ship, col_cdc = st.columns(2)
    with col_ship:
        with st.container(border=True):
            st.subheader("Active shipment", icon=":material/local_shipping:")
            r1c1, r1c2 = st.columns(2)
            r1c1.markdown(f"**Invoice:** `{shipmeta.get('invoice_no') or '—'}`")
            r1c2.markdown(f"**Supplier:** `{shipmeta.get('supplier') or '—'}`")
            r2c1, r2c2 = st.columns(2)
            r2c1.markdown(f"**Consignee:** `{shipmeta.get('consignee') or '—'}`")
            r2c2.markdown(f"**Date:** `{shipmeta.get('invoice_date') or '—'}`")
            if bill_meta.get("bl_no"):
                r3c1, r3c2 = st.columns(2)
                r3c1.markdown(f"**B/L:** `{bill_meta['bl_no']}`")
                r3c2.markdown(f"**Mode:** `{bill_meta.get('shipping_mode') or '—'}`")

    with col_cdc:
        with st.container(border=True):
            st.subheader("CDC master list", icon=":material/verified:")
            r1c1, r1c2 = st.columns(2)
            r1c1.markdown(f"**Company:** `{cdcmeta.get('company') or '—'}`")
            r1c2.markdown(f"**QIP / CIB:** `{cdcmeta.get('qip') or '—'}`")
            cdc_items = active_job.get("cdcitems", [])
            r2c1, r2c2 = st.columns(2)
            r2c1.markdown(f"**Total items:** `{len(cdc_items)}`")
            r2c2.markdown(f"**File:** `{active_job.get('cdc_filename', '—')}`")

    st.space("small")

    with st.container(border=True):
        st.subheader("Invoice items overview", icon=":material/table_chart:")
        rows = []
        for r in results:
            best = r["candidates"][0] if r.get("candidates") else None
            rows.append({
                "Description": r.get("english_provided") or r.get("query", ""),
                "Chinese": r.get("chinese", ""),
                "Qty": r.get("qty"),
                "Unit": r.get("unit", ""),
                "Total USD": f"${r.get('total', 0):,.2f}",
                "CDC match": best["description"] if best else "—",
                "Score": f"{best['score']:.0%}" if best else "—",
            })
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
        st.caption(f"{len(results)} items · ${total_val_usd:,.2f} total declared value")

else:
    # ── Overview from database & default CDC Master ───────────
    all_shipments = list_shipments(DB_PATH)
    cleared_count = sum(1 for s in all_shipments if s["status"] == "Cleared")
    transit_count = sum(1 for s in all_shipments if s["status"] in ("In Transit", "Arrived"))
    draft_count = sum(1 for s in all_shipments if s["status"] == "Draft")

    # Metrics row
    with st.container(horizontal=True):
        st.metric("Tracked shipments", f"{len(all_shipments)}", border=True)
        st.metric("Cleared shipments", f"{cleared_count}", border=True)
        st.metric("In transit", f"{transit_count}", border=True)
        st.metric("Draft records", f"{draft_count}", border=True)

    st.space("small")

    c_act, c_cdc = st.columns([3, 2])
    with c_act:
        with st.container(border=True):
            st.subheader("Quick actions", icon=":material/bolt:")
            st.markdown("""
- **Import matcher**: Upload a supplier invoice & packing list to match CDC items and export official customs documents (`PERMIT_*.xlsx`).
- **Batch cut-stock**: Cut stock for multiple shipments (e.g. 4 shipments) into the CDC Master List Excel all at once.
- **Shipments workspace**: Manage shipping documents, tracking events, ETA port, and forwarder details.
            """)
            col_b1, col_b2 = st.columns(2)
            with col_b1:
                st.page_link("app_pages/import_matcher.py", label="Open import matcher", icon=":material/sync_alt:")
            with col_b2:
                st.page_link("app_pages/batch_cutstock.py", label="Open batch cut-stock", icon=":material/layers:")

    with c_cdc:
        with st.container(border=True):
            st.subheader("Master list status", icon=":material/verified:")
            if has_default_cdc:
                raw_bytes = get_default_cdc_bytes()
                cdcmeta, cdcitems = extract_cdc(raw_bytes, default_cdc_name)
                st.markdown(f"**Company:** `{cdcmeta.get('company') or 'XIN CAI FU'}`")
                st.markdown(f"**QIP / CIB:** `{cdcmeta.get('qip') or '211/26'}`")
                st.markdown(f"**Approved items:** `{len(cdcitems)} items`")
                st.caption(f":material/check_circle: File: `{default_cdc_name}`")
            else:
                st.info("No default CDC Master List file found in `data/defaults/`.")

    st.space("small")

    # Recent shipments table
    with st.container(border=True):
        st.subheader("Recent shipments log", icon=":material/history:")
        if all_shipments:
            table_rows = []
            for s in all_shipments[:10]:
                table_rows.append({
                    "Company": s["company"],
                    "Direction": s["direction"],
                    "Reference": s["reference"],
                    "Status": s["status"],
                    "B/L": s["hbl"] or "—",
                    "Container": s["container"] or "—",
                    "ETA Port": s["eta_port"] or "—",
                    "ETA Factory": s["eta_factory"] or "—",
                })
            st.dataframe(pd.DataFrame(table_rows), hide_index=True, width="stretch")
        else:
            st.caption("No shipments registered yet.")
