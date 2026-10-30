import tempfile
import unittest
from pathlib import Path

from services.shipping_store import (
    add_event, attach_existing_document, create_shipment, get_shipment,
    list_documents, list_events, list_shipments, save_uploaded_document,
    seed_tk164, update_shipment,
)


class ShippingStoreTests(unittest.TestCase):
    def test_company_separation_and_document_history(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            database = root / "data" / "shipping.sqlite3"
            xcf = create_shipment(database, "XIN CAI FU", "Import", "INV-1")
            king = create_shipment(database, "KING SG", "Export", "INV-1")
            self.assertNotEqual(xcf, king)
            with self.assertRaises(ValueError):
                create_shipment(database, "XIN CAI FU", "Import", "INV-1")
            update_shipment(database, xcf, status="In transit", hbl="HBL-1")
            self.assertEqual(get_shipment(database, xcf)["hbl"], "HBL-1")
            document = save_uploaded_document(database, root, xcf, "bill_of_lading", "HBL.pdf", b"%PDF-test")
            self.assertTrue(document.is_file())
            attach_existing_document(database, root, xcf, "bill_of_lading", document)
            self.assertEqual(len(list_documents(database, xcf)), 1)
            self.assertEqual(list_documents(database, king), [])
            add_event(database, xcf, "2026-10-25", "Container unloaded", "Forwarder")
            self.assertEqual(list_events(database, xcf)[0]["description"], "Container unloaded")
            self.assertEqual(list_events(database, king), [])
            self.assertEqual(len(list_shipments(database)), 2)

    def test_rejects_invalid_fields_and_external_documents(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            database = root / "data" / "shipping.sqlite3"
            shipment_id = create_shipment(database, "XIN CAI FU", "Import", "INV-1")
            with self.assertRaises(ValueError):
                update_shipment(database, shipment_id, status="Delivered maybe")
            with self.assertRaises(ValueError):
                add_event(database, shipment_id, "2026-99-99", "Arrived")
            with self.assertRaises(ValueError):
                save_uploaded_document(database, root, shipment_id, "other", "../bad.exe", b"payload")
            outside = root.parent / "outside_shipping_test.pdf"
            with self.assertRaises(FileNotFoundError):
                attach_existing_document(database, root, shipment_id, "other", outside)

    def test_tk164_reference_seed_is_idempotent(self):
        root = Path(__file__).parents[1]
        with tempfile.TemporaryDirectory() as temp:
            database = Path(temp) / "shipping.sqlite3"
            seed_tk164(database, root)
            seed_tk164(database, root)
            shipments = list_shipments(database)
            self.assertEqual(len(shipments), 1)
            self.assertEqual(shipments[0]["reference"], "26TKYM164")
            self.assertEqual(shipments[0]["direction"], "Import")
            self.assertEqual(shipments[0]["hbl"], "YS26100022-1")
            self.assertEqual(shipments[0]["container"], "FFAU7241358")
            self.assertEqual(len(list_documents(database, shipments[0]["id"])), 5)


if __name__ == "__main__":
    unittest.main()
