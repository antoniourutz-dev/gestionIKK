"""Reglas de rutas y nombres documentales, sin dependencias de interfaz.

No analiza el contenido de los PDF ni intenta reconocer datos personales.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DocumentRoute:
    value: str
    folder_name: str
    filename_prefix: str
    copies_to_day: bool = False


ROUTES = {
    "BIHOTZ": DocumentRoute("BIHOTZ", "BIHOTZ", "BIHOTZ", copies_to_day=True),
    "LOGO": DocumentRoute("LOGO", "LOGOPEDIA", "LOGO"),
    "POLICLINICA": DocumentRoute("POLICLINICA", "POLICLINICA", "POLI"),
}


def get_route(tipo: str) -> DocumentRoute:
    """Devuelve la configuración exacta del circuito documental."""
    try:
        return ROUTES[tipo]
    except KeyError as exc:
        raise ValueError(f"Tipo documental no reconocido: {tipo}") from exc


def document_stem(tipo: str, cic: str) -> str:
    """Prefijo de archivo (ej. 'POLI CIC 12345')."""
    return f"{get_route(tipo).filename_prefix} CIC {cic.strip()}"


def original_filename(tipo: str, cic: str) -> str:
    return f"{document_stem(tipo, cic)}.pdf"


# Las plataformas de firma pueden anteponer una referencia técnica a los PDF:
#   16451_BIHOTZ CIC 543210.pdf
# El bloque identificador relevante es el que TERMINA el nombre, no el que lo inicia.
# Se conservan variantes habituales de Windows y de firmas (_firmado, -signed, (1)).
_NAMED_CASE_SUFFIX = re.compile(
    r"(?:^|[ _.-])(?P<service>BIHOTZ|LOGO|POLI)\s+CIC\s+(?P<cic>\d+)"
    r"(?:[ _-](?:firmado|firmada|signed))?(?:\s*\(\d+\))?$",
    re.IGNORECASE,
)
_BARE_CIC_FILENAME = re.compile(
    r"^(?P<cic>\d+)(?:[ _-](?:firmado|firmada|signed))?(?:\s*\(\d+\))?$",
    re.IGNORECASE,
)


def _named_case_at_end(filename: str) -> tuple[str, str] | None:
    """Extrae (servicio, CIC) del SUFIJO de un nombre de PDF.

    Ignora los números y otros textos antepuestos por la plataforma de firma.
    No abre ni inspecciona el contenido del documento.
    """
    path = Path(filename)
    if path.suffix.casefold() != ".pdf":
        return None
    match = _NAMED_CASE_SUFFIX.search(path.stem)
    if not match:
        return None
    return match.group("service").upper(), match.group("cic")


def is_named_service_download(filename: str, tipo: str, cic: str) -> bool:
    """Comprueba el sufijo `<BIHOTZ|LOGO|POLI> CIC <CIC>` al final del PDF."""
    route = get_route(tipo)
    return _named_case_at_end(filename) == (route.filename_prefix, cic.strip())


def is_matching_download(filename: str, tipo: str, cic: str) -> bool:
    """Localiza PDF por su sufijo de servicio/CIC, nunca por números iniciales.

    Ej.: `16451_BIHOTZ CIC 543210.pdf` coincide con BIHOTZ/CIC 543210.
    Conserva también las descargas previas denominadas `<CIC>.pdf` (sin
    servicio) y las variantes de firma usuales, para los tres circuitos.
    """
    identifier = cic.strip()
    route = get_route(tipo)
    if not identifier or Path(filename).suffix.casefold() != ".pdf":
        return False
    named = _named_case_at_end(filename)
    if named is not None:
        return named == (route.filename_prefix, identifier)
    bare = _BARE_CIC_FILENAME.fullmatch(Path(filename).stem)
    return bare is not None and bare.group("cic") == identifier


def is_foreign_case_filename(filename: str, tipo: str, cic: str) -> bool:
    """Impide incorporar por selección manual un CIC o servicio diferente.

    En los nombres tipo `16451_BIHOTZ CIC 543210.pdf` la referencia 16451
    NO es el CIC: este debe leerse del sufijo final `BIHOTZ CIC 543210`.
    Los nombres no identificables siguen requiriendo confirmación manual.
    """
    route = get_route(tipo)
    if Path(filename).suffix.casefold() != ".pdf":
        return False
    named = _named_case_at_end(filename)
    if named is not None:
        return named != (route.filename_prefix, cic.strip())
    bare = _BARE_CIC_FILENAME.fullmatch(Path(filename).stem)
    if bare is not None:
        return bare.group("cic") != cic.strip()
    return False


def signed_import_filename(filename: str, tipo: str, cic: str) -> str:
    """Protege el PDF original cuando un firmado llega con el mismo nombre.

    Para LOGO/POLI, el original ya está archivado como ``LOGO/POLI CIC X.pdf``.
    Si el PDF firmado se descarga con ese mismo nombre, guardarlo como
    ``LOGO/POLI CIC X_firmado.pdf`` en lugar de sobrescribir el original.
    """
    if filename.casefold() == original_filename(tipo, cic).casefold():
        return f"{document_stem(tipo, cic)}_firmado.pdf"
    return filename


def find_matching_downloads(folder: Path, tipo: str, cic: str) -> list[Path]:
    if not folder.is_dir():
        raise FileNotFoundError(f"No se encuentra la carpeta de Descargas: {folder}")
    return sorted(
        (item for item in folder.iterdir() if item.is_file() and is_matching_download(item.name, tipo, cic)),
        key=lambda item: item.name.casefold(),
    )


def base_directory(tipo: str, destino: str, network_root: Path, home: Path, year: int) -> Path:
    """Carpeta raíz del expediente en Escritorio o unidad T:, sin crearlas."""
    route = get_route(tipo)
    if destino == "ESCRITORIO":
        english = home / "Desktop"
        return english if english.is_dir() else home / "Escritorio"
    if destino == "T_DRIVE":
        return network_root / str(year) / route.folder_name
    raise ValueError(f"Destino no reconocido: {destino}")


def expediente_folder_name(apellidos: str, nombre: str) -> str:
    """Nomenclatura común a los tres circuitos: 'APELLIDOS, NOMBRE'.

    Los datos se introducen manualmente y la validación de caracteres
    corresponde al formulario de la aplicación.
    """
    return f"{apellidos.strip()}, {nombre.strip()}"


def expediente_directory(
    tipo: str, destino: str, network_root: Path, home: Path, year: int,
    apellidos: str, nombre: str,
) -> Path:
    """Ruta completa del expediente en unidad T: o Escritorio."""
    return base_directory(tipo, destino, network_root, home, year) / expediente_folder_name(apellidos, nombre)


def list_other_download_pdfs(folder: Path, tipo: str, cic: str, *, limit: int = 80) -> list[Path]:
    """PDF no coincidentes, sin nombres que identifiquen otro circuito/CIC.

    Solo se consultan los nombres y las fechas de modificación, nunca el texto del PDF.
    El usuario debe confirmar explícitamente cualquier selección no coincidente.
    """
    get_route(tipo)
    if not folder.is_dir():
        return []
    other = (
        item for item in folder.iterdir()
        if item.is_file()
        and item.suffix.casefold() == ".pdf"
        and not is_matching_download(item.name, tipo, cic)
        and not is_foreign_case_filename(item.name, tipo, cic)
    )
    def mtime(item: Path) -> float:
        try:
            return item.stat().st_mtime
        except OSError:
            return 0.0
    return sorted(other, key=mtime, reverse=True)[:limit]
