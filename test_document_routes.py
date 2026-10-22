"""Pruebas sin datos personales y sin necesidad de abrir una interfaz gráfica."""
import tempfile
import unittest
from pathlib import Path

from document_routes import (
    base_directory, expediente_directory, expediente_folder_name,
    find_matching_downloads, get_route, is_matching_download, original_filename,
)


class TestDocumentRoutes(unittest.TestCase):
    def test_three_existing_modes_have_expected_folders_and_prefixes(self):
        expected = {
            "BIHOTZ": ("BIHOTZ", "BIHOTZ CIC 12345.pdf", True),
            "LOGO": ("LOGOPEDIA", "LOGO CIC 12345.pdf", False),
            "POLICLINICA": ("POLICLINICA", "POLI CIC 12345.pdf", False),
        }
        for tipo, (folder, filename, day) in expected.items():
            with self.subTest(tipo=tipo):
                self.assertEqual(get_route(tipo).folder_name, folder)
                self.assertEqual(original_filename(tipo, " 12345 "), filename)
                self.assertEqual(get_route(tipo).copies_to_day, day)

    def test_poli_matches_only_its_own_cic(self):
        good = (
            "POLI CIC 12345.pdf",
            "poli cic 12345_Firmado.PDF",
            "POLI CIC 12345 (1).pdf",
            "POLI CIC 12345-signed.pdf",
        )
        bad = (
            "POLI CIC 123456.pdf",  # CIC parcial no válido
            "LOGO CIC 12345.pdf",
            "BIHOTZ CIC 12345.pdf",
            "POLI CIC 12345.crdownload",
            "documento POLI CIC 12345.pdf",
            "POLI CIC 12345.pdf.exe",
        )
        for name in good:
            with self.subTest(good=name):
                self.assertTrue(is_matching_download(name, "POLICLINICA", "12345"))
        for name in bad:
            with self.subTest(bad=name):
                self.assertFalse(is_matching_download(name, "POLICLINICA", "12345"))

    def test_other_modes_maintain_download_file_prefix(self):
        self.assertTrue(is_matching_download("LOGO CIC 93_firmado.pdf", "LOGO", "93"))
        self.assertTrue(is_matching_download("BIHOTZ CIC 93 (1).pdf", "BIHOTZ", "93"))
        self.assertFalse(is_matching_download("LOGO CIC 930.pdf", "LOGO", "93"))

    def test_sort_and_ignore_unrelated_downloads(self):
        with tempfile.TemporaryDirectory() as td:
            folder = Path(td)
            for name in (
                "POLI CIC 12345_Firmado.pdf", "POLI CIC 12345.pdf", "POLI CIC 123456.pdf",
                "LOGO CIC 12345.pdf", "POLI CIC 12345.crdownload",
            ):
                (folder / name).write_bytes(b"test content")
            self.assertEqual(
                [p.name for p in find_matching_downloads(folder, "POLICLINICA", "12345")],
                ["POLI CIC 12345.pdf", "POLI CIC 12345_Firmado.pdf"],
            )

    def test_polyclinica_destinations_in_year_2026(self):
        root = Path(r"T:\\00IMArrasate")
        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            self.assertEqual(
                base_directory("POLICLINICA", "T_DRIVE", root, home, 2026),
                root / "2026" / "POLICLINICA",
            )
            self.assertEqual(
                base_directory("POLICLINICA", "ESCRITORIO", root, home, 2026),
                home / "Escritorio",
            )
            (home / "Desktop").mkdir()
            self.assertEqual(
                base_directory("POLICLINICA", "ESCRITORIO", root, home, 2026),
                home / "Desktop",
            )
            with self.assertRaises(ValueError):
                base_directory("POLICLINICA", "OTRO", root, home, 2026)

    def test_expediente_folder_name_comma_and_single_space(self):
        self.assertEqual(expediente_folder_name("CONCEPCIÓN URIARTE", "MARKEL"), "CONCEPCIÓN URIARTE, MARKEL")
        self.assertEqual(expediente_folder_name("  CONCEPCIÓN URIARTE ", " MARKEL  "), "CONCEPCIÓN URIARTE, MARKEL")

    def test_expediente_folder_all_services_both_destinations(self):
        # Confirma que POLICLINICA también crea la subcarpeta por persona.
        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            (home / "Desktop").mkdir()
            network_root = home / "T" / "00IMArrasate"
            expected_dirs = {"BIHOTZ": "BIHOTZ", "LOGO": "LOGOPEDIA", "POLICLINICA": "POLICLINICA"}
            for tipo, service_folder in expected_dirs.items():
                with self.subTest(tipo=tipo, destino="T_DRIVE"):
                    result = expediente_directory(tipo, "T_DRIVE", network_root, home, 2026,
                                                  "CONCEPCIÓN URIARTE", "MARKEL")
                    self.assertEqual(result, network_root / "2026" / service_folder / "CONCEPCIÓN URIARTE, MARKEL")
                    result.mkdir(parents=True, exist_ok=True)
                    self.assertTrue(result.is_dir())
                with self.subTest(tipo=tipo, destino="ESCRITORIO"):
                    result = expediente_directory(tipo, "ESCRITORIO", network_root, home, 2026,
                                                  "CONCEPCIÓN URIARTE", "MARKEL")
                    self.assertEqual(result, home / "Desktop" / "CONCEPCIÓN URIARTE, MARKEL")
                    result.mkdir(parents=True, exist_ok=True)
                    self.assertTrue(result.is_dir())

    def test_missing_download_folder_and_invalid_route(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(FileNotFoundError):
                find_matching_downloads(Path(td) / "missing", "POLICLINICA", "12345")
        with self.assertRaises(ValueError):
            get_route("OTRA")


if __name__ == "__main__":
    unittest.main()
