import tempfile
import unittest
from pathlib import Path

import fitz

from pdf_core import PDFDocument, PDFViewerError


class TestPDFDocument(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.pdf_path = Path(self.temp.name) / "documento_prueba.pdf"
        doc = fitz.open()
        a = doc.new_page(width=400, height=600)
        a.insert_text((50, 100), "El documento tiene una frase de prueba.")
        a.insert_text((50, 140), "Otra frase de prueba.")
        b = doc.new_page(width=600, height=400)
        b.insert_text((50, 100), "Segunda pagina, con prueba adicional.")
        doc.save(self.pdf_path)
        doc.close()
        self.viewer = PDFDocument()
        self.addCleanup(self.viewer.close)

    def test_open_and_navigation(self):
        self.viewer.open(self.pdf_path)
        self.assertEqual(self.viewer.page_count, 2)
        self.assertEqual(self.viewer.dimensions(0), (400, 600))
        self.assertEqual(self.viewer.dimensions(0, 90), (600, 400))
        with self.assertRaises(PDFViewerError):
            self.viewer.dimensions(3)

    def test_render_rotation_and_thumbnail(self):
        self.viewer.open(self.pdf_path)
        normal = self.viewer.render(0, scale=1)
        rotated = self.viewer.render(0, scale=1, rotation=90)
        thumb = self.viewer.thumbnail(0)
        self.assertEqual(normal.size, (400, 600))
        self.assertEqual(rotated.size, (600, 400))
        self.assertLessEqual(thumb.width, 122)
        self.assertLessEqual(thumb.height, 160)

    def test_manual_search_and_highlight(self):
        self.viewer.open(self.pdf_path)
        hits_a = self.viewer.find_in_page(0, "prueba")
        hits_b = self.viewer.find_in_page(1, "prueba")
        self.assertEqual(len(hits_a), 2)
        self.assertEqual(len(hits_b), 1)
        plain = self.viewer.render(0, 1)
        marked = self.viewer.render(0, 1, highlights=[(hits_a[0], True)])
        self.assertNotEqual(plain.tobytes(), marked.tobytes())

    def test_bad_input_does_not_discard_open_document(self):
        self.viewer.open(self.pdf_path)
        with self.assertRaises(PDFViewerError):
            self.viewer.open(Path(self.temp.name) / "ausente.pdf")
        self.assertEqual(self.viewer.page_count, 2)

    def test_too_large_render_is_rejected(self):
        self.viewer.open(self.pdf_path)
        with self.assertRaises(PDFViewerError):
            self.viewer.render(0, scale=25)


if __name__ == "__main__":
    unittest.main()
