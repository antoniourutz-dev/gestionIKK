"""Selección explícita de PDF descargados para LOGOPEDIA y POLICLINICA.

Solo se examinan nombres y metadatos de archivos. Nunca se leen textos de los PDF.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox
import tkinter as tk

import customtkinter as ctk

from document_routes import is_foreign_case_filename, is_matching_download


def choose_download_pdf(
    parent: tk.Misc,
    candidates: list[Path],
    downloads: Path,
    tipo: str,
    cic: str,
    *,
    purpose: str = "Firmado",
) -> Path | None:
    """Solicita que el usuario elija UN archivo; no incorpora nada sin selección."""
    result: Path | None = None
    selected = tk.StringVar(value="")
    window = ctk.CTkToplevel(parent)
    window.title(f"{purpose} · Seleccionar PDF")
    window.geometry("680x450")
    window.minsize(590, 350)
    window.transient(parent)
    window.configure(fg_color="#F3F6FB")

    title = ctk.CTkLabel(
        window, text="Selecciona el documento de Descargas",
        font=ctk.CTkFont(family="Segoe UI", size=17, weight="bold"), text_color="#15253F",
    )
    title.pack(fill="x", padx=22, pady=(20, 2), anchor="w")
    details = (
        f"{purpose} · {tipo} · CIC: {cic}\n"
        "La aplicación no comprueba firmas digitales. Revisa que sea el PDF correcto."
    )
    ctk.CTkLabel(window, text=details, font=ctk.CTkFont(size=12),
                 text_color="#617188", justify="left").pack(fill="x", padx=22, anchor="w", pady=(0, 13))

    list_area = ctk.CTkScrollableFrame(window, fg_color="#FFFFFF", corner_radius=10)
    list_area.pack(fill="both", expand=True, padx=20, pady=(0, 12))

    def format_item(path: Path) -> str:
        try:
            stat = path.stat()
            date = datetime.fromtimestamp(stat.st_mtime).strftime("%d-%m-%Y %H:%M")
            size = f"{stat.st_size / 1024:.0f} KB"
            return f"{path.name}\n{date} · {size}"
        except OSError:
            return path.name

    if candidates:
        # Primero los más recientes. Selección deliberada incluso si hay uno solo.
        def mtime(path: Path) -> float:
            try:
                return path.stat().st_mtime
            except OSError:
                return 0.0
        for path in sorted(candidates, key=mtime, reverse=True):
            ctk.CTkRadioButton(
                list_area, text=format_item(path), variable=selected,
                value=str(path), text_color="#15253F", fg_color="#2563EB",
                font=ctk.CTkFont(size=12), radiobutton_height=18,
            ).pack(fill="x", padx=12, pady=9, anchor="w")
    else:
        ctk.CTkLabel(
            list_area,
            text="No hay coincidencias exactas con este CIC.\nPuedes elegir el PDF manualmente.",
            text_color="#617188", font=ctk.CTkFont(size=13), justify="center",
        ).pack(fill="both", expand=True, padx=12, pady=30)

    buttons = ctk.CTkFrame(window, fg_color="transparent")
    buttons.pack(fill="x", padx=20, pady=(0, 20))

    def confirm_path(path: Path) -> bool:
        if not path.is_file() or path.suffix.casefold() != ".pdf":
            messagebox.showerror("Archivo no válido", "Selecciona un documento PDF existente.", parent=window)
            return False
        if is_foreign_case_filename(path.name, tipo, cic):
            messagebox.showerror(
                "Posible expediente equivocado",
                "El nombre del archivo corresponde a otro CIC o circuito documental. "
                "No se permite incorporarlo a este expediente.", parent=window,
            )
            return False
        if not is_matching_download(path.name, tipo, cic):
            return bool(messagebox.askyesno(
                "Comprobar expediente",
                "El nombre de este PDF no sigue la nomenclatura esperada para el CIC introducido.\n\n"
                f"Archivo: {path.name}\nCircuito: {tipo}\nCIC: {cic}\n\n"
                "¿Has comprobado MANUALMENTE que pertenece a este expediente?",
                parent=window,
            ))
        return True

    def accept() -> None:
        nonlocal result
        value = selected.get()
        if not value:
            messagebox.showwarning("Selecciona un archivo", "Marca un PDF o utiliza «Examinar otro PDF».", parent=window)
            return
        path = Path(value)
        if confirm_path(path):
            result = path
            window.destroy()

    def browse() -> None:
        nonlocal result
        chosen = filedialog.askopenfilename(
            parent=window, title=f"Seleccionar PDF para {purpose.lower()}",
            initialdir=str(downloads if downloads.is_dir() else Path.home()),
            filetypes=[("Documentos PDF", "*.pdf")],
        )
        if chosen:
            path = Path(chosen)
            if confirm_path(path):
                result = path
                window.destroy()

    def cancel() -> None:
        window.destroy()

    ctk.CTkButton(buttons, text="Cancelar", command=cancel, width=90,
                  fg_color="white", text_color="#15253F", border_width=1,
                  border_color="#E0E7F1").pack(side="right", padx=(8, 0))
    ctk.CTkButton(buttons, text="Usar seleccionado", command=accept, width=145,
                  fg_color="#2563EB").pack(side="right", padx=4)
    ctk.CTkButton(buttons, text="Examinar otro PDF...", command=browse, width=160,
                  fg_color="#EDF4FF", text_color="#2563EB").pack(side="left")

    window.protocol("WM_DELETE_WINDOW", cancel)
    window.lift()
    window.focus_force()
    window.grab_set()
    parent.wait_window(window)
    return result
