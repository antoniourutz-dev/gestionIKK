"""Pruebas del historial: fechas, persistencia, ruta local y acceso a archivos."""
import os
import sqlite3
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path
from unittest.mock import patch

from history_store import HistoryStore, bihotz_day_directory, database_location, folder_documents


class HistoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.db = self.root / "data" / "historial.sqlite3"

    def test_persistence_between_instances(self):
        store = HistoryStore(self.db)
        folder = self.root / "CONCEPCIÓN URIARTE, MARKEL"
        pdf = folder / "POLI CIC 12345.pdf"
        store.add("POLICLINICA", "Documento guardado", folder, pdf,
                  when=datetime(2026, 10, 22, 9, 41))
        reopened = HistoryStore(self.db)
        rows = reopened.list(date(2026, 10, 22))
        self.assertEqual(1, len(rows))
        self.assertEqual("POLICLINICA", rows[0].kind)
        self.assertEqual(pdf, rows[0].file)
        self.assertEqual(folder, rows[0].folder)
        self.assertEqual("2026-10-22T09:41:00", rows[0].timestamp)

    def test_day_and_service_filters(self):
        store = HistoryStore(self.db)
        store.add("BIHOTZ", "Documento guardado", self.root,
                  when=datetime(2026, 10, 22, 8, 0))
        store.add("LOGO", "Firmado incorporado", self.root,
                  when=datetime(2026, 10, 22, 9, 0))
        store.add("BIHOTZ", "Día comprimido", self.root,
                  when=datetime(2026, 10, 21, 20, 0))
        self.assertEqual(2, len(store.list(date(2026, 10, 22))))
        self.assertEqual(1, len(store.list(date(2026, 10, 22), "BIHOTZ")))
        self.assertEqual(2, len(store.list(None, "BIHOTZ")))
        self.assertEqual(0, len(store.list(date(2026, 10, 23))))
        all_rows = store.list(None)
        self.assertEqual(["LOGO", "BIHOTZ", "BIHOTZ"], [r.kind for r in all_rows])

    def test_does_not_copy_or_modify_document(self):
        store = HistoryStore(self.db)
        folder = self.root / "expediente"
        folder.mkdir()
        pdf = folder / "BIHOTZ CIC 9.pdf"
        pdf.write_bytes(b"un documento de prueba")
        before = pdf.stat().st_mtime_ns
        store.add("BIHOTZ", "Documento guardado", folder, pdf)
        store.list(date.today())
        self.assertEqual(b"un documento de prueba", pdf.read_bytes())
        self.assertEqual(before, pdf.stat().st_mtime_ns)

    def test_invalid_kind_not_recorded(self):
        store = HistoryStore(self.db)
        with self.assertRaises(ValueError):
            store.add("OTRO", "Guardado", self.root)
        with self.assertRaises(ValueError):
            store.list(None, "OTRO")
        self.assertEqual([], store.list(None))

    def test_file_list_includes_only_pdf_and_7z(self):
        folder = self.root / "dia"
        folder.mkdir()
        for filename in ("X.pdf", "Y.7z", "otro.txt", "malicioso.exe", "z.PDF"):
            (folder / filename).touch()
        (folder / "subdirectorio").mkdir()
        self.assertEqual({"X.pdf", "Y.7z", "z.PDF"}, {p.name for p in folder_documents(folder)})
        self.assertEqual([], folder_documents(self.root / "inexistente"))

    def test_historical_bihotz_folder_uses_selected_date_and_year(self):
        root = Path("T:/00IMArrasate")
        folder = bihotz_day_directory(root, date(2025, 12, 31))
        self.assertEqual(root / "2025" / "BIHOTZ POR DIAS" / "BIHOTZ 31-12-2025", folder)
        self.assertFalse(folder.exists())  # no crea directorios

    def test_local_appdata_separated_from_executable(self):
        with patch.dict(os.environ, {"LOCALAPPDATA": str(self.root / "AppData" )}):
            self.assertEqual(self.root / "AppData" / "GestorPDF" / "historial.sqlite3", database_location())

    def test_records_do_not_include_document_content_or_password(self):
        store = HistoryStore(self.db)
        store.add("BIHOTZ", "Día comprimido", self.root, self.root / "fecha.7z")
        conn = sqlite3.connect(self.db)
        try:
            fields = {r[1] for r in conn.execute('PRAGMA table_info(actions)')}
        finally:
            conn.close()
        self.assertEqual({"id", "timestamp", "kind", "action", "folder", "file"}, fields)

    def test_limit(self):
        store = HistoryStore(self.db)
        for n in range(4):
            store.add("BIHOTZ", f"accion {n}", self.root)
        self.assertEqual(["accion 3", "accion 2"], [r.action for r in store.list(None, limit=2)])
        with self.assertRaises(ValueError):
            store.list(None, limit=0)


if __name__ == "__main__":
    unittest.main()
