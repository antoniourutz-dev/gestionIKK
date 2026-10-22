"""Ventana de consulta de historial: filtros por fecha, archivos y carpetas."""
from __future__ import annotations

import os
import sqlite3
import tkinter as tk
from datetime import date, datetime, timedelta
from pathlib import Path
from tkinter import messagebox, ttk

import customtkinter as ctk

from history_store import HistoryRecord, HistoryStore, bihotz_day_directory, folder_documents

BG = "#F3F6FB"
WHITE = "#FFFFFF"
NAVY = "#15253F"
BLUE = "#2563EB"
MUTED = "#617188"
BORDER = "#E0E7F1"


class HistoryWindow(ctk.CTkToplevel):
    """Solo consulta el historial; no modifica ni elimina ningún archivo."""

    def __init__(self, parent, store: HistoryStore, network_root: Path):
        super().__init__(parent)
        self.title("Historial de trabajos | Gestor Documental")
        self.geometry("1110x710")
        self.minsize(850, 580)
        self.configure(fg_color=BG)
        self.store = store
        self.network_root = network_root
        self.date_var = tk.StringVar(value=date.today().strftime("%d-%m-%Y"))
        self.service_var = tk.StringVar(value="TODOS")
        self.all_dates_var = tk.BooleanVar(value=False)
        self.summary_var = tk.StringVar()
        self.detail_var = tk.StringVar(value="Selecciona una operación para consultar su ubicación.")
        self._records: dict[str, HistoryRecord] = {}
        self._current_folder: Path | None = None
        self._visible_files: dict[str, Path] = {}
        self._build()
        self.refresh()
        self.after(100, self.lift)

    def _label(self, parent, text: str = "", *, size: int = 12, color: str = MUTED, bold: bool = False, **kw):
        return ctk.CTkLabel(parent, text=text, text_color=color,
                            font=ctk.CTkFont(family="Segoe UI", size=size,
                                             weight="bold" if bold else "normal"), **kw)

    def _button(self, parent, text: str, cmd, *, primary: bool = False, width: int = 90):
        return ctk.CTkButton(parent, text=text, command=cmd, width=width, height=33,
                             corner_radius=8,
                             fg_color=BLUE if primary else "#EAF1FF",
                             hover_color="#174FC3" if primary else "#D9E5FA",
                             text_color=WHITE if primary else BLUE,
                             font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"))

    def _build(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        header = ctk.CTkFrame(self, fg_color=WHITE, corner_radius=12)
        header.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 9))
        self._label(header, "HISTORIAL DE TRABAJOS", size=18, color=NAVY, bold=True).pack(anchor="w", padx=18, pady=(13, 0))
        self._label(header, "Consulta por fecha y servicio. Abre el documento o su carpeta sin modificarlo.", size=11).pack(anchor="w", padx=18, pady=(1, 12))

        controls = ctk.CTkFrame(self, fg_color=WHITE, corner_radius=12)
        controls.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 9))
        self._label(controls, "FECHA", size=10, color=NAVY, bold=True).pack(side="left", padx=(16, 7))
        self._button(controls, "‹", lambda: self._move_day(-1), width=35).pack(side="left", pady=10)
        self.date_entry = ctk.CTkEntry(controls, textvariable=self.date_var, width=112, height=33, justify="center")
        self.date_entry.pack(side="left", padx=5)
        self.date_entry.bind("<Return>", lambda _event: self.refresh())
        self._button(controls, "›", lambda: self._move_day(1), width=35).pack(side="left")
        self._button(controls, "Hoy", self._today, width=50).pack(side="left", padx=(9, 6))
        ctk.CTkCheckBox(controls, text="Todas las fechas", variable=self.all_dates_var,
                        command=self._switch_all_dates, width=130, font=ctk.CTkFont(size=11)).pack(side="left", padx=7)
        ctk.CTkOptionMenu(controls, values=["TODOS", "BIHOTZ", "LOGO", "POLICLINICA"],
                          variable=self.service_var, command=lambda _value: self.refresh(),
                          width=142, height=33, fg_color="#EAF1FF", button_color=BLUE,
                          text_color=NAVY).pack(side="left", padx=(8, 4))
        self._button(controls, "Consultar", self.refresh, primary=True, width=90).pack(side="right", padx=(0, 14))

        main = ctk.CTkFrame(self, fg_color="transparent")
        main.grid(row=2, column=0, sticky="nsew", padx=16, pady=(0, 8))
        main.grid_columnconfigure(0, weight=5)
        main.grid_columnconfigure(1, weight=3)
        main.grid_rowconfigure(0, weight=1)

        results = ctk.CTkFrame(main, fg_color=WHITE, corner_radius=12)
        results.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        results.grid_rowconfigure(1, weight=1)
        results.grid_columnconfigure(0, weight=1)
        self._label(results, "OPERACIONES REALIZADAS", size=12, color=NAVY, bold=True).grid(row=0, column=0, sticky="w", padx=14, pady=(14, 9))

        self._setup_tree_style()
        list_frame = tk.Frame(results, background=WHITE)
        list_frame.grid(row=1, column=0, sticky="nsew", padx=12)
        list_frame.grid_columnconfigure(0, weight=1)
        list_frame.grid_rowconfigure(0, weight=1)
        self.tree = ttk.Treeview(list_frame, columns=("hora", "tipo", "accion", "expediente", "archivo"),
                                 show="headings", selectmode="browse", style="History.Treeview")
        specs = [("hora", "Fecha y hora", 126), ("tipo", "Servicio", 98),
                 ("accion", "Operación", 134), ("expediente", "Carpeta", 160),
                 ("archivo", "Archivo", 175)]
        for key, title, size in specs:
            self.tree.heading(key, text=title)
            self.tree.column(key, width=size, minwidth=72, anchor="w", stretch=key in ("expediente", "archivo"))
        self.tree.grid(row=0, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.bind("<<TreeviewSelect>>", self._selected_record)
        self.tree.bind("<Double-1>", lambda _event: self.open_selected_document())
        self._label(results, textvariable=self.summary_var, size=11).grid(row=2, column=0, sticky="w", padx=14, pady=(10, 12))

        detail = ctk.CTkFrame(main, fg_color=WHITE, corner_radius=12)
        detail.grid(row=0, column=1, sticky="nsew")
        detail.grid_columnconfigure(0, weight=1)
        detail.grid_rowconfigure(3, weight=1)
        self._label(detail, "DETALLE Y DOCUMENTOS", size=12, color=NAVY, bold=True).grid(row=0, column=0, sticky="w", padx=14, pady=(14, 7))
        self._label(detail, textvariable=self.detail_var, size=11, justify="left",
                    wraplength=340).grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 11))
        row = ctk.CTkFrame(detail, fg_color="transparent")
        row.grid(row=2, column=0, sticky="ew", padx=14, pady=(0, 12))
        self._button(row, "Abrir archivo", self.open_selected_document, width=103, primary=True).pack(side="left", padx=(0, 5))
        self._button(row, "Abrir carpeta", self.open_selected_folder, width=113).pack(side="left")

        files_frame = ctk.CTkFrame(detail, fg_color="#F7F9FD", corner_radius=8)
        files_frame.grid(row=3, column=0, sticky="nsew", padx=13, pady=(0, 13))
        files_frame.grid_rowconfigure(1, weight=1)
        files_frame.grid_columnconfigure(0, weight=1)
        self._label(files_frame, "ARCHIVOS EN LA CARPETA (.PDF / .7Z)", size=10, color=NAVY,
                    bold=True).grid(row=0, column=0, sticky="w", padx=10, pady=(9, 5))
        self.file_list = tk.Listbox(files_frame, borderwidth=0, highlightthickness=0,
                                    background="#F7F9FD", foreground=NAVY,
                                    selectbackground="#DCE9FF", selectforeground=NAVY,
                                    font=("Segoe UI", 10), activestyle="none")
        self.file_list.grid(row=1, column=0, sticky="nsew", padx=(10, 0), pady=(0, 5))
        file_scroll = ttk.Scrollbar(files_frame, orient="vertical", command=self.file_list.yview)
        file_scroll.grid(row=1, column=1, sticky="ns", pady=(0, 5), padx=(0, 5))
        self.file_list.configure(yscrollcommand=file_scroll.set)
        self.file_list.bind("<Double-1>", lambda _event: self.open_list_file())
        self._button(files_frame, "Abrir archivo seleccionado", self.open_list_file,
                     width=195).grid(row=2, column=0, sticky="w", padx=10, pady=(3, 10))

        footer = ctk.CTkFrame(self, fg_color=WHITE, corner_radius=12)
        footer.grid(row=3, column=0, sticky="ew", padx=16, pady=(0, 14))
        self._button(footer, "Ver carpeta BIHOTZ de la fecha", self.open_day_folder, width=233).pack(side="left", padx=12, pady=10)
        self._button(footer, "Mostrar sus archivos", self.show_day_files, width=170).pack(side="left", padx=(0, 8))
        self._label(footer, "Las carpetas antiguas se pueden consultar aunque no exista un registro previo.",
                    size=10).pack(side="left", padx=5)

    def _setup_tree_style(self) -> None:
        style = ttk.Style(self)
        style.configure("History.Treeview", background=WHITE, fieldbackground=WHITE,
                        foreground=NAVY, rowheight=28, borderwidth=0, font=("Segoe UI", 10))
        style.configure("History.Treeview.Heading", font=("Segoe UI", 10, "bold"),
                        background="#EAF1FF", foreground=NAVY)
        style.map("History.Treeview", background=[("selected", "#DCE9FF")],
                  foreground=[("selected", NAVY)])

    def _date(self) -> date | None:
        if self.all_dates_var.get():
            return None
        try:
            return datetime.strptime(self.date_var.get().strip(), "%d-%m-%Y").date()
        except ValueError:
            messagebox.showwarning("Fecha incorrecta", "Introduce una fecha válida con formato DD-MM-AAAA.", parent=self)
            return None

    def refresh(self) -> None:
        day = self._date()
        if day is None and not self.all_dates_var.get():
            return
        try:
            records = self.store.list(day, None if self.service_var.get() == "TODOS" else self.service_var.get())
        except (OSError, sqlite3.Error, ValueError) as exc:
            messagebox.showerror("Historial", f"No se puede consultar el historial:\n{exc}", parent=self)
            return
        self._records.clear()
        self.tree.delete(*self.tree.get_children())
        self._current_folder = None
        self._set_files(None)
        self.detail_var.set("Selecciona una operación para consultar su ubicación.")
        for rec in records:
            timestamp = datetime.fromisoformat(rec.timestamp).strftime("%d-%m %H:%M")
            iid = str(rec.id)
            self.tree.insert("", "end", iid=iid,
                             values=(timestamp, rec.kind, rec.action, rec.folder.name,
                                     rec.file.name if rec.file else "—"))
            self._records[iid] = rec
        self.summary_var.set(f"{len(records)} operación(es) · {'últimas 2.000' if len(records) == 2000 else 'registro local'}")

    def _selected_record(self, _event=None) -> None:
        rec = self._selection()
        if rec is None:
            return
        self._current_folder = rec.folder
        self.detail_var.set(f"{rec.kind}  ·  {rec.action}\n{rec.folder}\n" +
                            (f"Archivo: {rec.file.name}" if rec.file else "Operación de carpeta"))
        self._set_files(rec.folder)

    def _selection(self) -> HistoryRecord | None:
        chosen = self.tree.selection()
        return self._records.get(chosen[0]) if chosen else None

    def _set_files(self, folder: Path | None, *, extra_files: list[Path] | None = None) -> None:
        self.file_list.delete(0, tk.END)
        self._visible_files.clear()
        if folder is None:
            return
        try:
            files = folder_documents(folder)
            for extra in extra_files or []:
                if extra.is_file() and extra.suffix.casefold() in (".pdf", ".7z") and extra not in files:
                    files.append(extra)
        except OSError as exc:
            self.file_list.insert(tk.END, f"Sin acceso: {exc}")
            return
        if not files:
            self.file_list.insert(tk.END, "No hay PDF/7z accesibles en esta carpeta.")
        for i, file in enumerate(files):
            self.file_list.insert(tk.END, file.name)
            self._visible_files[str(i)] = file

    def _open(self, path: Path, *, directory: bool = False) -> None:
        try:
            if directory:
                if not path.is_dir():
                    raise FileNotFoundError("La carpeta no existe o la unidad T: no está disponible.")
            else:
                if path.suffix.lower() not in (".pdf", ".7z"):
                    raise ValueError("Solo se permite abrir archivos PDF o 7z desde el historial.")
                if not path.is_file():
                    raise FileNotFoundError("El archivo ya no existe o la unidad T: no está disponible.")
            os.startfile(str(path))  # Windows: abrir con su aplicación predeterminada
        except (OSError, ValueError, AttributeError) as exc:
            messagebox.showwarning("No se puede abrir", str(exc), parent=self)

    def open_selected_document(self) -> None:
        rec = self._selection()
        if rec is None:
            messagebox.showinfo("Historial", "Selecciona una operación del listado.", parent=self)
        elif rec.file is not None:
            self._open(rec.file)
        else:
            self._open(rec.folder, directory=True)

    def open_selected_folder(self) -> None:
        rec = self._selection()
        if rec is None:
            messagebox.showinfo("Historial", "Selecciona una operación del listado.", parent=self)
        else:
            self._open(rec.folder, directory=True)

    def open_list_file(self) -> None:
        selected = self.file_list.curselection()
        if not selected:
            messagebox.showinfo("Archivos", "Selecciona un PDF o archivo comprimido de la lista.", parent=self)
            return
        file = self._visible_files.get(str(selected[0]))
        if file:
            self._open(file)

    def _selected_day(self) -> date | None:
        try:
            return datetime.strptime(self.date_var.get().strip(), "%d-%m-%Y").date()
        except ValueError:
            messagebox.showwarning("Fecha incorrecta", "Introduce una fecha válida con formato DD-MM-AAAA.", parent=self)
            return None

    def open_day_folder(self) -> None:
        day = self._selected_day()
        if day:
            self._open(bihotz_day_directory(self.network_root, day), directory=True)

    def show_day_files(self) -> None:
        day = self._selected_day()
        if not day:
            return
        folder = bihotz_day_directory(self.network_root, day)
        archive = folder.with_suffix(".7z")
        if not folder.is_dir() and not archive.is_file():
            messagebox.showwarning("Carpeta BIHOTZ", "No se encuentra la carpeta ni el comprimido para esa fecha.", parent=self)
            return
        self._current_folder = folder
        self.detail_var.set(f"BIHOTZ · Documentos del día\n{folder}\nSe incluye el .7z de esa fecha si existe.")
        self._set_files(folder, extra_files=[archive])

    def _move_day(self, offset: int) -> None:
        day = self._selected_day()
        if day:
            self.all_dates_var.set(False)
            self.date_var.set((day + timedelta(days=offset)).strftime("%d-%m-%Y"))
            self.refresh()

    def _today(self) -> None:
        self.all_dates_var.set(False)
        self.date_var.set(date.today().strftime("%d-%m-%Y"))
        self.refresh()

    def _switch_all_dates(self) -> None:
        self.date_entry.configure(state="disabled" if self.all_dates_var.get() else "normal")
        self.refresh()
