"""Shipments — track import and export shipments with documents and events."""

from datetime import date
from pathlib import Path
import pandas as pd
import streamlit as st

from services.shipping_store import (
    DOCUMENT_TYPES,
    EXPORT_DOCUMENTS,
    IMPORT_DOCUMENTS,
    STATUSES,
    add_event,
    create_shipment,
    get_shipment,
    list_documents,
    list_events,
    list_shipments,
    save_uploaded_document,
    seed_tk164,
    update_shipment,
)

ROOT = Path(__file__).resolve().parent.parent
database = ROOT / "data" / "shipping.sqlite3"
seed_tk164(database, ROOT)

lang = st.session_state.get("lang", "en")

# ── Shipment list ────────────────────────────────────────────
shipments = list_shipments(database)

# Top actions row
with st.container(horizontal=True):
    if st.button("Create shipment", icon=":material/add:", type="primary"):
        st.session_state["show_create_form"] = True
    st.caption(f"{len(shipments)} shipment{'s' if len(shipments) != 1 else ''} tracked")

# Create form (toggled)
if st.session_state.get("show_create_form"):
    with st.container(border=True):
        st.subheader("New shipment", icon=":material/add_circle:")
        with st.form("create_shipment", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            company = c1.text_input("Company", placeholder="e.g. XIN CAI FU (CAMBODIA) CO., LTD.")
            direction = c2.selectbox("Direction", ["Import", "Export"])
            reference = c3.text_input("Reference", placeholder="Invoice or booking number")
            partner = st.text_input("Supplier or customer")
            col_sub, col_cancel = st.columns(2)
            submitted = col_sub.form_submit_button("Create", type="primary", width="stretch")
            cancel = col_cancel.form_submit_button("Cancel", width="stretch")
        if submitted:
            try:
                shipment_id = create_shipment(database, company, direction, reference, partner=partner)
                st.session_state["selected_shipment_id"] = shipment_id
                st.session_state["show_create_form"] = False
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))
        if cancel:
            st.session_state["show_create_form"] = False
            st.rerun()

if not shipments:
    with st.container(border=True):
        st.markdown("No shipments yet. Click **Create shipment** to start tracking.")
    st.stop()

# Filters
with st.container(horizontal=True):
    companies = sorted({item["company"] for item in shipments})
    company_filter = st.selectbox("Company", ["All companies", *companies], label_visibility="collapsed")
    direction_filter = st.segmented_control("Direction", ["All", "Import", "Export"], default="All")

visible = [item for item in shipments
           if (company_filter == "All companies" or item["company"] == company_filter)
           and (direction_filter == "All" or item["direction"] == direction_filter)]

# Shipments table
if visible:
    table_data = []
    for item in visible:
        table_data.append({
            "Company": item["company"],
            "Direction": item["direction"],
            "Reference": item["reference"],
            "Status": item["status"],
            "B/L": item["hbl"] or "—",
            "Container": item["container"] or "—",
            "ETA port": item["eta_port"] or "—",
            "ETA factory": item["eta_factory"] or "—",
        })
    st.dataframe(pd.DataFrame(table_data), hide_index=True, width="stretch", alt="Shipments table")
else:
    st.caption("No shipments match the current filters.")
    st.stop()

# ── Shipment detail ──────────────────────────────────────────
ids = [item["id"] for item in visible]
saved = st.session_state.get("selected_shipment_id")
selection = st.selectbox(
    "Open shipment",
    ids,
    index=ids.index(saved) if saved in ids else 0,
    format_func=lambda sid: next(
        f"{item['company']} · {item['direction']} · {item['reference']}"
        for item in visible if item["id"] == sid
    ),
    label_visibility="collapsed",
)
st.session_state["selected_shipment_id"] = selection
shipment = get_shipment(database, selection)

with st.container(border=True):
    st.subheader(f"{shipment['reference']} · {shipment['direction']}", icon=":material/description:")
    st.caption(f"**{shipment['company']}** · Partner: {shipment['partner'] or '—'}")

    with st.form(f"details_{selection}"):
        c1, c2, c3 = st.columns(3)
        status = c1.selectbox("Status", STATUSES, index=STATUSES.index(shipment["status"]))
        hbl = c2.text_input("B/L or HBL", value=shipment["hbl"])
        container = c3.text_input("Container", value=shipment["container"])

        c4, c5, c6 = st.columns(3)
        origin = c4.text_input("Origin", value=shipment["origin"])
        destination = c5.text_input("Destination", value=shipment["destination"])
        forwarder = c6.text_input("Forwarder", value=shipment["forwarder"])

        c7, c8, c9 = st.columns(3)
        etd = c7.text_input("ETD", value=shipment["etd"], placeholder="YYYY-MM-DD")
        eta_port = c8.text_input("ETA port", value=shipment["eta_port"], placeholder="YYYY-MM-DD")
        eta_factory = c9.text_input("ETA factory", value=shipment["eta_factory"], placeholder="YYYY-MM-DD")

        notes = st.text_area("Notes", value=shipment["notes"])
        save = st.form_submit_button("Save changes", type="primary", width="stretch")

    if save:
        try:
            for value in (etd, eta_port, eta_factory):
                if value:
                    date.fromisoformat(value)
            update_shipment(database, selection, status=status, hbl=hbl.strip(),
                            container=container.strip(), origin=origin.strip(),
                            destination=destination.strip(), forwarder=forwarder.strip(),
                            etd=etd, eta_port=eta_port, eta_factory=eta_factory, notes=notes.strip())
            st.toast("Shipment saved", icon=":material/check:")
        except ValueError as exc:
            st.error(str(exc))

# Documents section
with st.container(border=True):
    st.subheader("Documents", icon=":material/folder:")
    docs = list_documents(database, selection)
    if docs:
        for doc in docs:
            doc_path = ROOT / doc["relative_path"]
            doc_data = doc_path.read_bytes() if doc_path.exists() else b""
            with st.container(horizontal=True):
                st.caption(f":material/description: **{doc['kind']}** — `{doc['filename']}`")
                if doc_data:
                    st.download_button(
                        "Download",
                        data=doc_data,
                        file_name=doc["filename"],
                        key=f"dl_doc_{doc['id']}",
                    )
    else:
        st.caption("No documents attached yet.")

    doc_types = IMPORT_DOCUMENTS if shipment["direction"] == "Import" else EXPORT_DOCUMENTS
    with st.expander("Upload document", icon=":material/upload:"):
        doc_type = st.selectbox("Document type", doc_types, label_visibility="collapsed")
        doc_file = st.file_uploader("File", label_visibility="collapsed", key=f"doc_up_{selection}")
        if doc_file and st.button("Attach", type="primary", width="stretch"):
            save_uploaded_document(database, ROOT, selection, doc_type, doc_file.name, doc_file.getvalue())
            st.toast("Document attached", icon=":material/check:")
            st.rerun()

# Events / timeline
with st.container(border=True):
    st.subheader("Activity log", icon=":material/timeline:")
    events = list_events(database, selection)
    if events:
        for ev in events:
            ev_date = ev.get("event_date") or ""
            st.caption(f"`{ev_date}` — {ev['description']}")
    else:
        st.caption("No events recorded yet.")

    with st.expander("Add event", icon=":material/add:"):
        event_desc = st.text_input("Event description", placeholder="e.g. Arrived at Prey Vor border", label_visibility="collapsed")
        if event_desc and st.button("Log event", type="primary", width="stretch"):
            add_event(database, selection, str(date.today()), event_desc)
            st.toast("Event logged", icon=":material/check:")
            st.rerun()
