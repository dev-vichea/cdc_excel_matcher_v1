"""CDC Quotas & Master List Hub.

Inspect approved duty exemption quotas, view remaining balances,
search items, and manage company master lists.
"""

from pathlib import Path
import pandas as pd
import streamlit as st

from services.extraction import extract_cdc
from services.settings_store import (
    get_default_cdc_bytes,
    get_default_cdc_path,
    get_settings,
)

ROOT = Path(__file__).resolve().parent.parent
settings = get_settings()

default_cdc_path = get_default_cdc_path()
has_default_cdc = default_cdc_path.is_file()
default_cdc_name = settings.get("cdc_filename") or default_cdc_path.name

st.caption("Live digital catalog of official Council for the Development of Cambodia (CDC) duty exemption quotas.")

# ── Master List File Header ───────────────────────────────────
with st.container(border=True):
    c1, c2 = st.columns([3, 2], vertical_alignment="center")
    with c1:
        st.markdown(f"**Active Master List:** `{default_cdc_name}`")
        st.caption("Auto-loaded from local application files. Upload below to view a different master list.")
    with c2:
        new_master = st.file_uploader(
            "Upload Master List",
            type=["xlsx"],
            key="cdc_hub_uploader",
            label_visibility="collapsed",
        )

if new_master:
    raw_bytes = new_master.getvalue()
    raw_name = new_master.name
else:
    raw_bytes = get_default_cdc_bytes()
    raw_name = default_cdc_name

if not raw_bytes:
    st.info("No CDC Master List loaded.")
    st.stop()

cdcmeta, cdcitems = extract_cdc(raw_bytes, raw_name)

if not cdcitems:
    st.warning("No quota items detected in the loaded CDC workbook.")
    st.stop()

# ── Summary metrics ───────────────────────────────────────────
total_approved_usd = sum(
    (item.get("approved") or 0) * (item.get("unit_price") or 0)
    for item in cdcitems
    if item.get("approved") and item.get("unit_price")
)
total_approved_items = len(cdcitems)
has_balance_info = any(item.get("remaining") is not None for item in cdcitems)

with st.container(horizontal=True):
    st.metric("Company", cdcmeta.get("company") or "Unknown", border=True)
    st.metric("QIP / CIB Reference", cdcmeta.get("qip") or "211/26", border=True)
    st.metric("Total Approved Items", f"{total_approved_items} items", border=True)
    if total_approved_usd > 0:
        st.metric("Total Quota Value", f"${total_approved_usd:,.0f} USD", border=True)

st.space("small")

# ── Search & Filter ───────────────────────────────────────────
c_srch, c_unit = st.columns([3, 1])
with c_srch:
    search_q = st.text_input(
        "Search items",
        placeholder="Search description, item serial, or keyword...",
        label_visibility="collapsed",
    )
with c_unit:
    units_list = sorted({item.get("unit") for item in cdcitems if item.get("unit")})
    unit_filter = st.selectbox("Unit filter", ["All units", *units_list], label_visibility="collapsed")

filtered = []
for item in cdcitems:
    desc = str(item.get("description") or "")
    sn = str(item.get("serial") or item.get("row") or "")
    u = str(item.get("unit") or "")

    if search_q and search_q.lower() not in desc.lower() and search_q not in sn:
        continue
    if unit_filter != "All units" and u != unit_filter:
        continue
    filtered.append(item)

# ── Table View ────────────────────────────────────────────────
table_rows = []
for item in filtered:
    appr = item.get("approved")
    rem = item.get("remaining")
    price = item.get("unit_price")
    tot_val = appr * price if appr is not None and price is not None else None

    # Quota usage indicator
    if rem is not None and appr and appr > 0:
        pct = (rem / appr) * 100
        health = f"{pct:.0f}% remaining"
    else:
        health = "Available"

    table_rows.append({
        "Item #": item.get("serial") or f"#{item['row']}",
        "Description": item.get("description", "—"),
        "Unit": item.get("unit", "—"),
        "Approved Quota": f"{appr:,.0f}" if appr is not None else "—",
        "Remaining Balance": f"{rem:,.0f}" if rem is not None else "—",
        "Unit Price": f"${price:,.2f}" if price is not None else "—",
        "Total USD": f"${tot_val:,.2f}" if tot_val is not None else "—",
        "Quota Status": health,
    })

st.dataframe(pd.DataFrame(table_rows), hide_index=True, width="stretch", height=500)
st.caption(f"Showing {len(filtered)} of {total_approved_items} approved items.")

