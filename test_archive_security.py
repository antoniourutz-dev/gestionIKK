"""Comprobaciones de selección de claves, sin exponerlas en la salida de tests."""
import unittest
from pathlib import Path
from archive_security import get_service_password, creation_command, test_command, list_command


class TestServiceArchivePasswords(unittest.TestCase):
    def test_all_five_services_have_own_fixed_password(self):
        # La comparación con los valores acordados se hace sin imprimirlos.
        expected = {
            "BIHOTZ": "cc.biho", "MATIA": "cc.mati", "ARANSGI": "cc.aran",
            "ASPACE": "cc.aspa", "POLICLINICA": "cc.poli",
        }
        self.assertEqual({s: get_service_password(s) for s in expected}, expected)
        self.assertEqual(len(set(expected.values())), 5)

    def test_unknown_service_is_rejected(self):
        with self.assertRaises(ValueError):
            get_service_password("DESCONOCIDO")

    def test_creation_encrypted_content_but_visible_names(self):
        cmd = creation_command(Path("7z.exe"), Path("test.7z"), Path("test.pdf"), get_service_password("ASPACE"))
        self.assertIn("-mhe=off", cmd)
        self.assertNotIn("-mhe=on", cmd)
        self.assertEqual(cmd[1], "a")
        self.assertEqual(list_command(Path("7z.exe"), Path("test.7z")), ["7z.exe", "l", "test.7z"])
        self.assertEqual(test_command(Path("7z.exe"), Path("test.7z"), get_service_password("BIHOTZ"))[1], "t")

    def test_empty_password_fails(self):
        with self.assertRaises(ValueError):
            creation_command(Path("7z.exe"), Path("test.7z"), Path("x"), "")


if __name__ == "__main__":
    unittest.main()
