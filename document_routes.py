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


def is_matching_download(filename: str, tipo: str, cic: str) -> bool:
    """Encuentra documentos por su NOMBRE, sin inspeccionar el contenido.

    BIHOTZ conserva la nomenclatura ``BIHOTZ CIC <cic>``.
    LOGOPEDIA y POLICLINICA aceptan tanto la nomenclatura del expediente
    (``LOGO/POLI CIC <cic>``) como el nombre de descarga ``<cic>.pdf``.
    En todos los casos el identificador debe ser completo: nunca una subcadena.
    """
    identifier = cic.strip()
    if not identifier or Path(filename).suffix.casefold() != ".pdf":
        return False
    get_route(tipo)  # Validar incluso cuando el archivo no coincide.
    expected = re.escape(document_stem(tipo, identifier))
    if re.match(rf"^{expected}(?=\.|[ _(-])", filename, re.IGNORECASE):
        return True
    if tipo in ("LOGO", "POLICLINICA"):
        bare_cic = re.escape(identifier)
        return re.match(rf"^{bare_cic}(?=\.|[ _(-])", filename, re.IGNORECASE) is not None
    return False


def is_foreign_case_filename(filename: str, tipo: str, cic: str) -> bool:
    """Bloquea una selección manual que identifica a otro CIC o servicio.

    Los nombres arbitrarios no identificables pueden seleccionarse mediante
    confirmación explícita. Esta comprobación es solo del nombre de archivo.
    """
    if Path(filename).suffix.casefold() != ".pdf":
        return False
    known = re.match(
        r"^(?:(BIHOTZ|LOGO|POLI)\s+CIC\s+)?(\d+)(?=\.|[ _(-])",
        filename, re.IGNORECASE,
    )
    if not known:
        return False
    prefix, identifier = known.group(1), known.group(2)
    if identifier != cic.strip():
        return True
    if prefix is None:
        return False
    return prefix.upper() != get_route(tipo).filename_prefix


def signed_import_filename(filename: str, tipo: str, cic: str) -> str:
    """Protege el PDF original cuando un firmado llega con el mismo nombre.

    Para LOGO/POLI, el original ya está archivado como ``LOGO/POLI CIC X.pdf``.
    Si el PDF firmado se descarga con ese mismo nombre, guardarlo como
    ``LOGO/POLI CIC X_firmado.pdf`` en lugar de sobrescribir el original.
    """
    if tipo in ("LOGO", "POLICLINICA") and filename.casefold() == original_filename(tipo, cic).casefold():
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
