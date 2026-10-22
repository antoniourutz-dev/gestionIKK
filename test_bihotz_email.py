"""Pruebas de correo con dobles; no abre Outlook ni envía emails reales."""
from datetime import date
from pathlib import Path
import tempfile
import unittest

from bihotz_email import (
    RECIPIENT, BODY, archive_stamp, folder_snapshot, mail_subject,
    prepare_outlook_draft, validate_daily_archive,
)


class FakeAttachments:
    def __init__(self): self.paths = []
    def Add(self, value): self.paths.append(value)


class FakeMessage:
    def __init__(self):
        self.To = self.Subject = self.Body = ""
        self.Attachments = FakeAttachments()
        self.displayed = False
        self.sent = False
    def Display(self): self.displayed = True
    def Send(self): self.sent = True


class FakeOutlook:
    def __init__(self): self.message = FakeMessage()
    def CreateItem(self, n):
        assert n == 0
        return self.message


class TestBihotzEmail(unittest.TestCase):
    def test_subject_matches_day_folder_format(self):
        self.assertEqual(mail_subject(date(2026, 10, 22)), "Volantes 22-10-2026")
        self.assertEqual(RECIPIENT, "Info@bihotz.es")

    def test_body_is_full_bilingual_and_uses_real_linebreaks(self):
        self.assertTrue(BODY.startswith("Honekin batera, sinatutako bolantea bidaltzen da / Adjunto se envía volante firmado."))
        for text in ("Adeitasunez / Atentamente,", "Gipuzkoako ikuskaritza medikua",
                     "Inspección médica de Gipuzkoa", "Oharra:", "Nota:",
                     "rogándole que destruya el mismo"):
            self.assertIn(text, BODY)
        self.assertIn("\r\n\r\n", BODY)
        self.assertNotIn("%0D%0A", BODY)

    def test_draft_sets_addressee_subject_body_attachment_and_never_sends(self):
        with tempfile.TemporaryDirectory() as td:
            archive = Path(td) / "BIHOTZ 22-10-2026.7z"
            archive.write_bytes(b"7z\xbc\xaf\x27\x1c" + b"X" * 50)
            fake = FakeOutlook()
            prepare_outlook_draft(archive, date(2026, 10, 22), dispatch=lambda arg: fake)
            self.assertEqual(fake.message.To, RECIPIENT)
            self.assertEqual(fake.message.Subject, "Volantes 22-10-2026")
            self.assertEqual(fake.message.Body, BODY)
            self.assertEqual(fake.message.Attachments.paths, [str(archive.resolve())])
            self.assertTrue(fake.message.displayed)
            self.assertFalse(fake.message.sent)

    def test_new_files_or_changed_archive_block_send(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            folder = root / "BIHOTZ 22-10-2026"
            folder.mkdir()
            (folder / "BIHOTZ CIC 123.pdf").write_bytes(b"pdf content")
            archive = folder.with_suffix(".7z")
            archive.write_bytes(b"7z\xbc\xaf\x27\x1c" + b"x" * 80)
            snapshot, stamp = folder_snapshot(folder), archive_stamp(archive)
            validate_daily_archive(folder, archive, date(2026, 10, 22), snapshot, stamp)
            (folder / "BIHOTZ CIC 456.pdf").write_bytes(b"more content")
            with self.assertRaisesRegex(ValueError, "cambiado"):
                validate_daily_archive(folder, archive, date(2026, 10, 22), snapshot, stamp)
            (folder / "BIHOTZ CIC 456.pdf").unlink()
            archive.write_bytes(b"7z\xbc\xaf\x27\x1c" + b"z" * 90)
            with self.assertRaisesRegex(ValueError, "cambiado"):
                validate_daily_archive(folder, archive, date(2026, 10, 22), snapshot, stamp)

    def test_wrong_day_and_invalid_7z_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            folder = Path(td) / "BIHOTZ 22-10-2026"
            folder.mkdir()
            (folder / "BIHOTZ CIC 123.pdf").write_bytes(b"test")
            archive = folder.with_suffix(".7z")
            archive.write_bytes(b"not a real 7z" * 10)
            with self.assertRaisesRegex(ValueError, "7z"):
                archive_stamp(archive)
            archive.write_bytes(b"7z\xbc\xaf\x27\x1c" + b"z" * 90)
            with self.assertRaisesRegex(ValueError, "no corresponde"):
                validate_daily_archive(folder, archive, date(2026, 10, 23), folder_snapshot(folder), archive_stamp(archive))

    def test_no_pdf_blocks_day_package(self):
        with tempfile.TemporaryDirectory() as td:
            folder = Path(td)
            (folder / "readme.txt").write_text("hello")
            with self.assertRaisesRegex(ValueError, "ningún PDF"):
                folder_snapshot(folder)

if __name__ == "__main__":
    unittest.main()
