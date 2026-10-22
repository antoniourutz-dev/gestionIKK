"""Motor local del visor PDF (no extrae ni infiere datos de expedientes)."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import fitz
from PIL import Image, ImageDraw


@dataclass(frozen=True)
class Match:
    page: int
    rect: tuple[float, float, float, float]


class PDFViewerError(Exception):
    pass


class PDFDocument:
    """Abre archivos PDF en modo lectura; las rotaciones solo afectan a la vista."""

    MAX_PIXELS = 20_000_000

    def __init__(self) -> None:
        self._doc: fitz.Document | None = None
        self.path: Path | None = None

    @property
    def page_count(self) -> int:
        return len(self._doc) if self._doc else 0

    @property
    def is_open(self) -> bool:
        return self._doc is not None and not self._doc.is_closed

    def open(self, path: str | Path) -> None:
        p = Path(path)
        if not p.is_file() or p.suffix.lower() != ".pdf":
            raise PDFViewerError("Selecciona un archivo PDF existente.")
        try:
            candidate = fitz.open(str(p))
            if not candidate.is_pdf or candidate.needs_pass:
                candidate.close()
                raise PDFViewerError("Este archivo no es un PDF válido o requiere contraseña.")
            if len(candidate) == 0:
                candidate.close()
                raise PDFViewerError("El archivo PDF no contiene páginas.")
        except PDFViewerError:
            raise
        except Exception as exc:
            raise PDFViewerError(f"No se ha podido abrir el PDF: {exc}") from exc
        self.close()
        self._doc = candidate
        self.path = p

    def close(self) -> None:
        if self._doc and not self._doc.is_closed:
            self._doc.close()
        self._doc = None
        self.path = None

    def _page(self, index: int) -> fitz.Page:
        if not self.is_open or not 0 <= index < self.page_count:
            raise PDFViewerError("La página solicitada no está disponible.")
        assert self._doc is not None
        return self._doc.load_page(index)

    def dimensions(self, index: int, view_rotation: int = 0) -> tuple[float, float]:
        page = self._page(index)
        rect = page.rect  # incorpora la rotación original del propio PDF
        if view_rotation % 180:
            return rect.height, rect.width
        return rect.width, rect.height

    def find_in_page(self, index: int, query: str) -> list[Match]:
        if not query.strip():
            return []
        try:
            page = self._page(index)
            return [Match(index, tuple(rect)) for rect in page.search_for(query.strip())]
        except Exception as exc:
            raise PDFViewerError(f"No se pudo buscar texto en la página {index+1}: {exc}") from exc

    @staticmethod
    def _place_highlights(
        image: Image.Image,
        page: fitz.Page,
        pixels: fitz.Pixmap,
        scale: float,
        matches: Iterable[tuple[Match, bool]],
    ) -> Image.Image:
        layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(layer, "RGBA")
        matrix = fitz.Matrix(scale, scale)
        for hit, active in matches:
            rect = fitz.Rect(hit.rect) * page.rotation_matrix * matrix
            box = (
                int(rect.x0 - pixels.x), int(rect.y0 - pixels.y),
                int(rect.x1 - pixels.x), int(rect.y1 - pixels.y),
            )
            draw.rectangle(
                box,
                fill=(48, 113, 224, 95) if active else (246, 187, 59, 98),
                outline=(28, 82, 186, 255) if active else (221, 145, 18, 255),
                width=2 if active else 1,
            )
        if layer.getbbox() is None:
            return image
        return Image.alpha_composite(image.convert("RGBA"), layer).convert("RGB")

    def render(
        self,
        index: int,
        scale: float,
        rotation: int = 0,
        highlights: Iterable[tuple[Match, bool]] = (),
    ) -> Image.Image:
        if scale <= 0:
            raise PDFViewerError("El zoom debe ser mayor que cero.")
        page = self._page(index)
        page_rect = page.rect
        pixels_estimate = (page_rect.width * scale) * (page_rect.height * scale)
        if pixels_estimate > self.MAX_PIXELS:
            raise PDFViewerError("El zoom solicitado generaría una imagen demasiado grande.")
        try:
            pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), colorspace=fitz.csRGB, alpha=False)
            image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            image = self._place_highlights(image, page, pix, scale, highlights)
            if rotation % 360:
                # PIL gira en sentido antihorario; en el visor los 90° son horarios.
                image = image.rotate(-(rotation % 360), expand=True)
            return image
        except PDFViewerError:
            raise
        except Exception as exc:
            raise PDFViewerError(f"No se pudo dibujar la página: {exc}") from exc

    def thumbnail(self, index: int, max_width: int = 122, max_height: int = 160) -> Image.Image:
        w, h = self.dimensions(index)
        scale = max(0.01, min(max_width / w, max_height / h))
        return self.render(index, scale)
