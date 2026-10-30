"""Streamlit screens for the shared import/export shipment workspace."""

from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

from services.shipping_store import (
    DOCUMENT_TYPES, EXPORT_DOCUMENTS, IMPORT_DOCUMENTS, STATUSES, add_event,
    create_shipment, get_shipment, list_documents, list_events, list_shipments,
    save_uploaded_document, seed_tk164, update_shipment,
)


def render(project_root: Path) -> None:
    database = project_root / "data" / "shipping.sqlite3"
    seed_tk164(database, project_root)
    st.title("Shipping workspace")
    st.caption("One shipment record for documents, transport, and follow-up across imports and exports. Local working data; no customs submission or CDC stock deduction.")

    with st.expander("Create shipment"):
        with st.form("create_shipment", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            company = c1.text_input("Company", placeholder="e.g. XIN CAI FU (CAMBODIA) CO., LTD.")
            direction = c2.selectbox("Direction", ["Import", "Export"])
            reference = c3.text_input("Shipment reference", placeholder="Invoice, order, or booking number")
            partner = st.text_input("Supplier or customer")
            submitted = st.form_submit_button("Create shipment", type="primary")
        if submitted:
            try:
                shipment_id = create_shipment(database, company, direction, reference, partner=partner)
                st.session_state["selected_shipment_id"] = shipment_id
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))

    shipments = list_shipments(database)
    if not shipments:
        st.info("Create a shipment to start tracking its documents and events.")
        return

    filter_col1, filter_col2 = st.columns(2)
    companies = sorted({item["company"] for item in shipments})
    company_filter = filter_col1.selectbox("Company filter", ["All companies", *companies])
    direction_filter = filter_col2.selectbox("Direction filter", ["All directions", "Import", "Export"])
    visible = [item for item in shipments
               if (company_filter == "All companies" or item["company"] == company_filter)
               and (direction_filter == "All directions" or item["direction"] == direction_filter)]
    st.dataframe(pd.DataFrame([{
        "Company": item["company"], "Direction": item["direction"],
        "Reference": item["reference"], "Status": item["status"],
        "HBL": item["hbl"], "Container": item["container"],
        "ETA port": item["eta_port"], "ETA factory": item["eta_factory"],
    } for item in visible]), hide_index=True, width="stretch")
    if not visible:
        st.info("No shipments match these filters.")
        return

    ids = [item["id"] for item in visible]
    saved = st.session_state.get("selected_shipment_id")
    selection = st.selectbox(
        "Open shipment", ids, index=ids.index(saved) if saved in ids else 0,
        format_func=lambda shipment_id: next(
            f"{item['company']} · {item['direction']} · {item['reference']}"
            for item in visible if item["id"] == shipment_id
        ),
    )
    st.session_state["selected_shipment_id"] = selection
    shipment = get_shipment(database, selection)
    st.divider()
    st.subheader(f"{shipment['reference']} · {shipment['direction']}")
    st.write(f"**Company:** {shipment['company']}  ·  **Partner:** {shipment['partner'] or '—'}")

    with st.form(f"details_{selection}"):
        c1, c2, c3 = st.columns(3)
        status = c1.selectbox("Status", STATUSES, index=STATUSES.index(shipment["status"]))
        hbl = c2.text_input("B/L or HBL number", value=shipment["hbl"])
        container = c3.text_input("Container number", value=shipment["container"])
        c4, c5, c6 = st.columns(3)
        origin = c4.text_input("Origin", value=shipment["origin"])
        destination = c5.text_input("Destination", value=shipment["destination"])
        forwarder = c6.text_input("Forwarder", value=shipment["forwarder"])
        c7, c8, c9 = st.columns(3)
        etd = c7.text_input("ETD (YYYY-MM-DD)", value=shipment["etd"])
        eta_port = c8.text_input("ETA port (YYYY-MM-DD)", value=shipment["eta_port"])
        eta_factory = c9.text_input("ETA factory (YYYY-MM-DD)", value=shipment["eta_factory"])
        notes = st.text_area("Notes", value=shipment["notes"])
        save = st.form_submit_button("Save shipment details")
    if save:
        try:
            for value in (etd, eta_port, eta_factory):
                if value:
                    date.fromisoformat(value)
            update_shipment(database, selection, status=status, hbl=hbl.strip(),
                            container=container.strip(), origin=origin.strip(),
                            destination=destination.strip(), forwarder=forwarder.strip(),
                            etd=etd, eta_port=eta_port, eta_factory=eta_factory, notes=notes.strip())
            st.success("Shipment details saved.")
        except ValueError as exc:
            st.error(f"Check the dates and fields: {exc}")

    st.subheader("Document checklist")
    documents = list_documents(database, selection)
    checklist = IMPORT_DOCUMENTS if shipment["direction"] == "Import" else EXPORT_DOCUMENTS
    rows = []
    for kind, label in checklist.items():
        attached = [item for item in documents if item["kind"] == kind]
        rows.append({"Document": label, "Status": "Attached" if attached else "Missing / not recorded",
                     "Files": ", ".join(item["filename"] for item in attached)})
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
    st.caption("Attached means a file is recorded; it does not mean the document has been approved or submitted.")
    with st.form(f"attach_{selection}"):
        kind = st.selectbox("Document type", list(checklist) + ["other"],
                            format_func=lambda value: DOCUMENT_TYPES[value])
        upload = st.file_uploader("Attach document", type=["pdf", "xls", "xlsx", "doc", "docx", "jpg", "jpeg", "png"])
        attach = st.form_submit_button("Save attachment")
    if attach:
        if upload is None:
            st.error("Choose a file first.")
        else:
            try:
                save_uploaded_document(database, project_root, selection, kind, upload.name, upload.getvalue())
                st.success("Document saved to this shipment.")
                st.rerun()
            except (OSError, ValueError) as exc:
                st.error(str(exc))
    with st.expander("All attached files"):
        for item in documents:
            file_path = project_root / item["relative_path"]
            if file_path.is_file():
                st.download_button(
                    f"{DOCUMENT_TYPES.get(item['kind'], item['kind'])}: {item['filename']}",
                    data=file_path.read_bytes(), file_name=item["filename"],
                    key=f"download_{item['id']}",
                )
            else:
                st.warning(f"Missing local file: {item['filename']}")

    st.subheader("Shipment timeline")
    events = list_events(database, selection)
    if events:
        st.dataframe(pd.DataFrame([{
            "Date": event["event_date"], "Event": event["description"],
            "Source": event["source"],
        } for event in events]), hide_index=True, width="stretch")
    else:
        st.caption("No confirmed events recorded. ETA fields above are plans, not actual events.")
    with st.form(f"event_{selection}", clear_on_submit=True):
        c1, c2 = st.columns([1, 3])
        event_date = c1.date_input("Event date", value=date.today())
        description = c2.text_input("What happened?", placeholder="e.g. Container unloaded at Sihanoukville")
        source = st.text_input("Source", placeholder="Carrier, forwarder, port, or staff")
        record = st.form_submit_button("Record event")
    if record:
        try:
            add_event(database, selection, event_date.isoformat(), description, source)
            st.rerun()
        except ValueError as exc:
            st.error(str(exc))
