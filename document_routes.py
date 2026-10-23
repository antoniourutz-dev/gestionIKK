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

    Los tres servicios admiten su prefijo propio y también la descarga
    ``<cic>.pdf``. En BIHOTZ el nombre sin prefijo exige confirmación manual
    en el selector porque no identifica por sí solo el servicio.
    En todos los casos el identificador debe ser completo: nunca una subcadena.
    """
    identifier = cic.strip()
    if not identifier or Path(filename).suffix.casefold() != ".pdf":
        return False
    get_route(tipo)  # Validar incluso cuando el archivo no coincide.
    expected = re.escape(document_stem(tipo, identifier))
    if re.match(rf"^{expected}(?=\.|[ _(-])", filename, re.IGNORECASE):
        return True
    bare_cic = re.escape(identifier)
    return re.match(rf"^{bare_cic}(?=\.|[ _(-])", filename, re.IGNORECASE) is not None


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
