"""Configuración de cifrado para el archivo 7z de cada servicio.

AVISO: Las claves compartidas solicitadas se incluyen en el proyecto y, por
consiguiente, pueden recuperarse del código fuente o del ejecutable. Esta
modalidad requiere aprobación de la organización antes de utilizarla con datos
personales sensibles. No imprimir, mostrar ni registrar nunca las claves.
"""
from __future__ import annotations
from pathlib import Path

# Cada servicio tiene su propia clave. LOGOPEDIA usa la del centro seleccionado.
# Se configuran aquí automáticamente; no se pide contraseña al comprimir.
_SERVICE_PASSWORDS = {
    "BIHOTZ": "cc.biho",
    "MATIA": "cc.mati",
    "ARANSGI": "cc.aran",
    "ASPACE": "cc.aspa",
    "POLICLINICA": "cc.poli",
}

SERVICE_LABELS = {
    "BIHOTZ": "BIHOTZ",
    "MATIA": "LOGOPEDIA · MATIA",
    "ARANSGI": "LOGOPEDIA · ARANSGI",
    "ASPACE": "LOGOPEDIA · ASPACE",
    "POLICLINICA": "POLICLINICA",
}


def get_service_password(service: str) -> str:
    """Recupera automáticamente la clave fija del circuito elegido."""
    try:
        return _SERVICE_PASSWORDS[service]
    except KeyError as exc:
        raise ValueError("Servicio no reconocido para la compresión.") from exc


def creation_command(exe: Path, archive: Path, source: Path, password: str) -> list[str]:
    """Cifra los datos pero NO los encabezados: listado de nombres sin clave.

    El contenido solo puede leerse o extraerse con contraseña. 7z recibe la
    contraseña como argumento por limitación de su línea de comandos.
    """
    if not password:
        raise ValueError("Falta la clave de compresión.")
    return [str(exe), "a", "-t7z", f"-p{password}", "-mhe=off", "-sse", str(archive), str(source)]


def test_command(exe: Path, archive: Path, password: str) -> list[str]:
    if not password:
        raise ValueError("Falta la clave de compresión.")
    return [str(exe), "t", f"-p{password}", str(archive)]


def list_command(exe: Path, archive: Path) -> list[str]:
    """El listado debe poder leerse sin contraseña."""
    return [str(exe), "l", str(archive)]
