"""Preparación del correo diario BIHOTZ (sin envío automático).

Solo Outlook clásico de Windows ofrece la automatización COM utilizada aquí.
No se extraen datos personales ni se comunica información con servicios web.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

RECIPIENT = "Info@bihotz.es"

BODY = (
    "Honekin batera, sinatutako bolantea bidaltzen da / Adjunto se envía volante firmado.\r\n\r\n\r\n"
    "Adeitasunez / Atentamente,\r\n\r\n"
    "Gipuzkoako ikuskaritza medikua\r\n"
    "Inspección médica de Gipuzkoa\r\n\r\n"
    "Oharra: Posta elektroniko honetako edo eranskin bezala daraman informazioa ez da edozeinentzat, baizik eta bidali dizkiodanarentzat soilik, eta baliteke ezkutukoa edo erabilera mugatukoa izatea, eta baliteke debekaturik egotea beste inon zabaltzea, edonola delarik ere. Ez badizut zuri bidali, jakin ezazu ez duzula ez inon zabaldu behar, ez kopiatu behar, ez harekin beste ezer egin behar. Desegin eta bidaltzaileari jakinarazi, horixe egin, mesedez.\r\n\r\n"
    "Nota: Este correo electrónico o los documentos que incluya, contiene información para uso exclusivo de la(s) persona(s) a la(s) que va dirigido y puede ser confidencial o restringida, estando prohibida cualquier divulgación. Si no es Ud. la persona a la que va dirigida, por la presente le comunicamos que no debe difundir, copiar o tomar acción alguna en relación a su contenido, rogándole que destruya el mismo y notifique a su remitente tal circunstancia."
)

SEVEN_ZIP_SIGNATURE = b"7z\xbc\xaf\x27\x1c"


def mail_subject(day: date) -> str:
    """Exactamente la fecha utilizada para la carpeta BIHOTZ del día."""
    return f"Volantes {day.strftime('%d-%m-%Y')}"


def folder_snapshot(day_folder: Path) -> tuple[tuple[str, int, int], ...]:
    """Huella de todos los archivos para detectar cambios tras comprimir."""
    if not day_folder.is_dir():
        raise ValueError("La carpeta del día ya no está disponible.")
    result = []
    for path in day_folder.rglob("*"):
        if path.is_file():
            stat = path.stat()
            result.append((path.relative_to(day_folder).as_posix(), stat.st_size, stat.st_mtime_ns))
    if not any(name.lower().endswith(".pdf") for name, _, _ in result):
        raise ValueError("La carpeta del día no contiene ningún PDF; no se debe enviar.")
    return tuple(sorted(result))


def archive_stamp(archive: Path) -> tuple[int, int]:
    if not archive.is_file():
        raise ValueError("No existe el archivo comprimido de BIHOTZ para hoy.")
    stat = archive.stat()
    if stat.st_size <= 32:
        raise ValueError("El archivo comprimido está vacío o incompleto.")
    with archive.open("rb") as fh:
        if fh.read(len(SEVEN_ZIP_SIGNATURE)) != SEVEN_ZIP_SIGNATURE:
            raise ValueError("El archivo adjunto no tiene un encabezado 7z válido.")
    return stat.st_size, stat.st_mtime_ns


def validate_daily_archive(
    day_folder: Path, archive: Path, day: date,
    expected_snapshot: tuple[tuple[str, int, int], ...],
    expected_archive_stamp: tuple[int, int],
) -> None:
    expected_folder_name = f"BIHOTZ {day.strftime('%d-%m-%Y')}"
    if day_folder.name != expected_folder_name or archive != day_folder.with_suffix(".7z"):
        raise ValueError("El comprimido no corresponde a la carpeta del día de hoy.")
    if folder_snapshot(day_folder) != expected_snapshot:
        raise ValueError("Los documentos del día han cambiado desde la última compresión. Vuelve a pulsar Comprimir.")
    if archive_stamp(archive) != expected_archive_stamp:
        raise ValueError("El archivo comprimido ha cambiado desde la última compresión. Vuelve a pulsar Comprimir.")


def prepare_outlook_draft(archive: Path, day: date, *, dispatch=None) -> None:
    """Abre borrador con adjunto. Nunca invoca Send().

    Raises RuntimeError if COM/Outlook no está disponible. 'dispatch' permite
    pruebas con un Outlook ficticio sin iniciar correo real.
    """
    if not archive.is_file():
        raise ValueError("El archivo a adjuntar ya no existe.")
    if dispatch is None:
        try:
            from win32com.client import Dispatch
        except ImportError as exc:
            raise RuntimeError("No está disponible la integración con Outlook clásico (pywin32).") from exc
        dispatch = Dispatch
    try:
        outlook = dispatch("Outlook.Application")
        message = outlook.CreateItem(0)  # olMailItem
        message.To = RECIPIENT
        message.Subject = mail_subject(day)
        message.Body = BODY
        message.Attachments.Add(str(archive.resolve()))
        message.Display()  # El usuario revisa el mensaje y pulsa Enviar en Outlook.
    except Exception as exc:
        raise RuntimeError(
            "No se ha podido preparar el correo en Outlook clásico. "
            "Comprueba que Outlook clásico de Windows esté instalado, abierto y configurado. "
            "El nuevo Outlook no admite esta automatización."
        ) from exc
