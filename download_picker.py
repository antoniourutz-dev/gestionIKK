"""Selección manual de PDF descargados por expediente y servicio.

Nunca se leen textos de los PDF ni se asume que un archivo está firmado.
BIHOTZ permite elegir varios; LOGO/POLICLINICA mantienen elección individual.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox
import tkinter as tk

import customtkinter as ctk

from document_routes import is_foreign_case_filename, is_matching_download, document_stem


def _choose_downloads(
    parent: tk.Misc,
    candidates: list[Path],
    downloads: Path,
    tipo: str,
    cic: str,
    *,
    purpose: str,
    other_candidates: list[Path] | None,
    multiple: bool,
) -> list[Path]:
    """Permite elegir explícitamente uno o varios archivos, o cancelar."""
    result: list[Path] = []
    selected = tk.StringVar(value="")
    checks: dict[Path, tk.BooleanVar] = {}

    window = ctk.CTkToplevel(parent)
    window.title(f"{purpose} · {tipo} · Seleccionar PDF")
    window.geometry("760x525")
    window.minsize(640, 390)
    window.transient(parent)
    window.configure(fg_color="#F3F6FB")

    ctk.CTkLabel(
        window, text="Selecciona los PDF de Descargas" if multiple else "Selecciona el documento de Descargas",
        font=ctk.CTkFont(family="Segoe UI", size=17, weight="bold"), text_color="#15253F",
    ).pack(fill="x", padx=22, pady=(20, 2), anchor="w")
    detail = (
        f"{purpose} · Servicio: {tipo} · CIC: {cic}\n"
        f"Descargas consultada: {downloads}\n"
        + ("Marca únicamente los firmados que quieres incorporar.\n" if multiple else "Elige el PDF correcto.\n")
        + "No se verifica la firma digital: comprueba manualmente cada documento."
    )
    ctk.CTkLabel(window, text=detail, font=ctk.CTkFont(size=12),
                 text_color="#617188", justify="left").pack(fill="x", padx=22, anchor="w", pady=(0, 13))

    list_area = ctk.CTkScrollableFrame(window, fg_color="#FFFFFF", corner_radius=10)
    list_area.pack(fill="both", expand=True, padx=20, pady=(0, 12))

    def mtime(path: Path) -> float:
        try:
            return path.stat().st_mtime
        except OSError:
            return 0.0

    def format_item(path: Path) -> str:
        try:
            stat = path.stat()
            date = datetime.fromtimestamp(stat.st_mtime).strftime("%d-%m-%Y %H:%M")
            size = f"{stat.st_size / 1024:.0f} KB"
            return f"{path.name}\n{date} · {size}"
        except OSError:
            return path.name

    def add_entry(path: Path) -> None:
        if multiple:
            variable = tk.BooleanVar(value=False)
            checks[path] = variable
            ctk.CTkCheckBox(
                list_area, text=format_item(path), variable=variable, text_color="#15253F",
                fg_color="#2563EB", font=ctk.CTkFont(size=12), checkbox_height=18,
            ).pack(fill="x", padx=12, pady=9, anchor="w")
        else:
            ctk.CTkRadioButton(
                list_area, text=format_item(path), variable=selected,
                value=str(path), text_color="#15253F", fg_color="#2563EB",
                font=ctk.CTkFont(size=12), radiobutton_height=18,
            ).pack(fill="x", padx=12, pady=9, anchor="w")

    unique_candidates = list(dict.fromkeys(candidates))
    if unique_candidates:
        ctk.CTkLabel(list_area, text=f"Coinciden con el CIC ({len(unique_candidates)})",
                     text_color="#15253F", font=ctk.CTkFont(size=12, weight="bold")
                     ).pack(fill="x", anchor="w", padx=12, pady=(12, 2))
        for path in sorted(unique_candidates, key=mtime, reverse=True):
            add_entry(path)
    else:
        ctk.CTkLabel(
            list_area, text="No hay coincidencias con la nomenclatura prevista.\n"
                            "Puedes elegir otro PDF o examinar la carpeta manualmente.",
            text_color="#617188", font=ctk.CTkFont(size=12), justify="left",
        ).pack(fill="x", anchor="w", padx=12, pady=14)

    extras = [p for p in dict.fromkeys(other_candidates or []) if p not in unique_candidates]
    if extras:
        ctk.CTkLabel(list_area, text="Otros PDF (comprobar manualmente antes de importar)",
                     text_color="#15253F", font=ctk.CTkFont(size=12, weight="bold")
                     ).pack(fill="x", anchor="w", padx=12, pady=(12, 2))
        for path in sorted(extras, key=mtime, reverse=True):
            add_entry(path)

    buttons = ctk.CTkFrame(window, fg_color="transparent")
    buttons.pack(fill="x", padx=20, pady=(0, 20))

    def confirm_path(path: Path) -> bool:
        if not path.is_file() or path.suffix.casefold() != ".pdf":
            messagebox.showerror("Archivo no válido", f"No existe este PDF:\n{path}", parent=window)
            return False
        if is_foreign_case_filename(path.name, tipo, cic):
            messagebox.showerror(
                "Posible expediente equivocado",
                "El nombre de este archivo identifica otro CIC o servicio. No se permite incorporarlo.",
                parent=window,
            )
            return False
        if not is_matching_download(path.name, tipo, cic):
            return bool(messagebox.askyesno(
                "Comprobar expediente",
                "El archivo no sigue la nomenclatura esperada.\n\n"
                f"Archivo: {path.name}\nServicio: {tipo}\nCIC: {cic}\n\n"
                "¿Has comprobado MANUALMENTE que pertenece a este expediente?",
                parent=window,
            ))
        # BIHOTZ también admite '<CIC>.pdf', pero ese formato no identifica el servicio.
        if tipo == "BIHOTZ" and not path.name.casefold().startswith(document_stem(tipo, cic).casefold()):
            return bool(messagebox.askyesno(
                "Confirmar documento BIHOTZ",
                f"El archivo «{path.name}» coincide con el CIC, pero no incluye BIHOTZ en el nombre.\n\n"
                "¿Has comprobado MANUALMENTE que es el documento firmado de BIHOTZ?",
                parent=window,
            ))
        return True

    def accept() -> None:
        nonlocal result
        paths = [p for p, var in checks.items() if var.get()] if multiple else ([Path(selected.get())] if selected.get() else [])
        if not paths:
            messagebox.showwarning("Selecciona un archivo", "Marca un PDF o utiliza «Examinar otro PDF».", parent=window)
            return
        # No se incorpora ningún archivo si hay elementos con validación fallida.
        if all(confirm_path(path) for path in paths):
            result = paths
            window.destroy()

    def browse() -> None:
        nonlocal result
        opts = dict(parent=window, title=f"Seleccionar PDF para {purpose.lower()}",
                    initialdir=str(downloads if downloads.is_dir() else Path.home()),
                    filetypes=[("Documentos PDF", "*.pdf")])
        chosen = filedialog.askopenfilenames(**opts) if multiple else filedialog.askopenfilename(**opts)
        paths = [Path(p) for p in chosen] if multiple else ([Path(chosen)] if chosen else [])
        if paths and all(confirm_path(path) for path in paths):
            result = paths
            window.destroy()

    def cancel() -> None:
        window.destroy()

    ctk.CTkButton(buttons, text="Cancelar", command=cancel, width=90,
                  fg_color="white", text_color="#15253F", border_width=1,
                  border_color="#E0E7F1").pack(side="right", padx=(8, 0))
    ctk.CTkButton(buttons, text="Incorporar seleccionados" if multiple else "Usar seleccionado",
                  command=accept, width=155 if multiple else 145,
                  fg_color="#2563EB").pack(side="right", padx=4)
    ctk.CTkButton(buttons, text="Examinar PDF...", command=browse, width=160,
                  fg_color="#EDF4FF", text_color="#2563EB").pack(side="left")

    window.protocol("WM_DELETE_WINDOW", cancel)
    window.lift()
    window.focus_force()
    window.grab_set()
    parent.wait_window(window)
    return result


def choose_download_pdf(
    parent: tk.Misc, candidates: list[Path], downloads: Path, tipo: str, cic: str,
    *, purpose: str = "Firmado", other_candidates: list[Path] | None = None,
) -> Path | None:
    """Selección individual para LOGOPEDIA y POLICLINICA (y sus Volantes)."""
    result = _choose_downloads(
        parent, candidates, downloads, tipo, cic, purpose=purpose,
        other_candidates=other_candidates, multiple=False,
    )
    return result[0] if result else None


def choose_download_pdfs(
    parent: tk.Misc, candidates: list[Path], downloads: Path, tipo: str, cic: str,
    *, purpose: str = "Firmado", other_candidates: list[Path] | None = None,
) -> list[Path]:
    """Selección múltiple explícita para BIHOTZ; cancelar devuelve []."""
    return _choose_downloads(
        parent, candidates, downloads, tipo, cic, purpose=purpose,
        other_candidates=other_candidates, multiple=True,
    )
