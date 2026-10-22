"""Gestor PDF 2.0 · Interfaz renovada + visor de documentos multipágina.

Ninguna función reconoce automáticamente pacientes, CIC, nombres ni apellidos.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog

import customtkinter as ctk
from PIL import ImageTk
from tkinterdnd2 import DND_FILES, TkinterDnD

from pdf_core import Match, PDFDocument, PDFViewerError


# Identidad visual (modo claro, diseñado para pantallas de oficina).
BG = "#F3F6FB"
WHITE = "#FFFFFF"
NAVY = "#15253F"
BLUE = "#2563EB"
BLUE_HOVER = "#174FC3"
BLUE_PALE = "#EDF4FF"
MUTED = "#617188"
BORDER = "#E0E7F1"
CANVAS_BG = "#E9EEF6"
SUCCESS = "#0A8B65"
AMBER = "#B46A16"

BASE_ROOT = Path(r"T:\00IMArrasate")
VOLANTES_ROOT = Path(r"T:\00Archivo_Volantes_Gipuzkoa")
THUMBS_PER_BATCH = 10
MIN_ZOOM = 0.25
MAX_ZOOM = 3.5

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")


class App(TkinterDnD.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Gestor documental | BIHOTZ · LOGOPEDIA")
        self.geometry("1440x875")
        self.minsize(1090, 690)
        self.configure(bg=BG)

        self.pdf = PDFDocument()
        self.page_index = 0
        self.view_rotation = 0
        self.zoom = 1.0
        self.fit_mode = "page"
        self.thumb_batch = 0
        self._canvas_photo: ImageTk.PhotoImage | None = None
        self._thumb_photos: list[ImageTk.PhotoImage] = []
        self._resize_task: str | None = None
        self._search_token = 0
        self._matches: list[Match] = []
        self._match_index = -1
        self._searching = False

        # Estado de las operaciones existentes.
        self.pdf_path = tk.StringVar()
        self.nom = tk.StringVar()
        self.ape = tk.StringVar()
        self.cic = tk.StringVar()
        self.tipo = tk.StringVar(value="BIHOTZ")
        self.destino_var = tk.StringVar(value="T_DRIVE")
        self.centro_logo_var = tk.StringVar(value="MATIA")
        self.page_var = tk.StringVar(value="—")
        self.zoom_var = tk.StringVar(value="100 %")
        self.search_var = tk.StringVar()
        self.search_result_var = tk.StringVar(value="Buscar en el PDF")
        self.status_var = tk.StringVar(value="Preparado · Selecciona o arrastra un PDF")
        self.doc_info_var = tk.StringVar(value="Sin documento abierto")
        self.carpeta_generada: Path | None = None
        self.archivo_firmado_path: Path | None = None

        self._create_layout()
        self._keyboard_shortcuts()
        self.protocol("WM_DELETE_WINDOW", self._close)
        self.after(100, self._draw_empty)

    def _label(self, parent, text: str, *, size: int = 12, color: str = MUTED, bold: bool = False, **kwargs):
        return ctk.CTkLabel(
            parent, text=text,
            font=ctk.CTkFont(family="Segoe UI", size=size, weight="bold" if bold else "normal"),
            text_color=color, **kwargs,
        )

    def _button(self, parent, text: str, command, *, width: int = 80, kind: str = "soft", height: int = 34, **kwargs):
        schemes = {
            "soft": dict(fg_color=BLUE_PALE, hover_color="#DCE9FF", text_color=BLUE, border_width=0),
            "plain": dict(fg_color=WHITE, hover_color=BG, text_color=NAVY, border_width=1, border_color=BORDER),
            "primary": dict(fg_color=BLUE, hover_color=BLUE_HOVER, text_color=WHITE, border_width=0),
            "green": dict(fg_color=SUCCESS, hover_color="#087354", text_color=WHITE, border_width=0),
        }
        return ctk.CTkButton(
            parent, text=text, command=command, width=width, height=height,
            corner_radius=9, font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            **schemes[kind], **kwargs,
        )

    def _section(self, parent, title: str, subtitle: str = ""):
        section = ctk.CTkFrame(parent, fg_color="transparent")
        section.pack(fill="x", padx=16, pady=(15, 2))
        self._label(section, title, size=12, bold=True, color=NAVY).pack(anchor="w")
        if subtitle:
            self._label(section, subtitle, size=11).pack(anchor="w", pady=(1, 0))
        return section

    def _create_layout(self) -> None:
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(self, corner_radius=0, fg_color=WHITE, height=77)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)
        header.grid_columnconfigure(1, weight=1)
        logo = ctk.CTkFrame(header, width=43, height=43, corner_radius=12, fg_color=BLUE)
        logo.grid(row=0, column=0, padx=(24, 14), pady=16)
        logo.grid_propagate(False)
        self._label(logo, "G", color=WHITE, size=23, bold=True).place(relx=0.5, rely=0.5, anchor="center")
        name_area = ctk.CTkFrame(header, fg_color="transparent")
        name_area.grid(row=0, column=1, sticky="w")
        self._label(name_area, "GESTOR DOCUMENTAL", size=19, color=NAVY, bold=True).pack(anchor="w")
        self._label(name_area, "BIHOTZ  /  LOGOPEDIA", size=11, color=MUTED).pack(anchor="w")
        self._label(header, "VISOR PDF · v2.0", size=11, color=MUTED, bold=True).grid(row=0, column=2, padx=16)
        self._button(header, "+ Abrir PDF", self.seleccionar, kind="primary", width=132, height=38).grid(row=0, column=3, padx=(2, 24))

        main = ctk.CTkFrame(self, fg_color="transparent")
        main.grid(row=1, column=0, sticky="nsew", padx=18, pady=(16, 12))
        main.grid_rowconfigure(0, weight=1)
        main.grid_columnconfigure(0, weight=1)
        main.grid_columnconfigure(1, weight=0, minsize=350)

        self._create_viewer(main)
        self._create_form(main)

        bottom = ctk.CTkFrame(self, height=38, fg_color=WHITE, corner_radius=0)
        bottom.grid(row=2, column=0, sticky="ew")
        bottom.grid_propagate(False)
        bottom.grid_columnconfigure(0, weight=1)
        status_area = ctk.CTkFrame(bottom, fg_color="transparent")
        status_area.grid(row=0, column=0, sticky="w", padx=(22, 8), pady=7)
        self._label(status_area, "●", size=12, color=SUCCESS).pack(side="left", padx=(0, 7))
        self.status_label = self._label(status_area, "", size=11, color=MUTED)
        self.status_label.configure(textvariable=self.status_var)
        self.status_label.pack(side="left")
        self._label(bottom, "Procesamiento local · Sin reconocimiento automático", size=10, color=MUTED).grid(row=0, column=1, padx=(8, 22))

    def _create_viewer(self, parent) -> None:
        card = ctk.CTkFrame(parent, fg_color=WHITE, corner_radius=14, border_width=1, border_color=BORDER)
        card.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        card.grid_columnconfigure(0, weight=1)
        card.grid_rowconfigure(3, weight=1)

        headline = ctk.CTkFrame(card, fg_color="transparent")
        headline.grid(row=0, column=0, sticky="ew", padx=18, pady=(15, 7))
        headline.grid_columnconfigure(0, weight=1)
        self._label(headline, "Vista del documento", size=15, color=NAVY, bold=True).grid(row=0, column=0, sticky="w")
        self._label(headline, "PDF original · Solo lectura", size=10, color=MUTED).grid(row=0, column=1, sticky="e")

        toolbar = ctk.CTkFrame(card, fg_color="transparent")
        toolbar.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 7))
        self._button(toolbar, "‹", self.pagina_anterior, width=31, kind="plain").pack(side="left", padx=3)
        self.page_entry = ctk.CTkEntry(toolbar, width=46, height=34, textvariable=self.page_var, justify="center", corner_radius=8, border_color=BORDER)
        self.page_entry.pack(side="left", padx=2)
        self.page_entry.bind("<Return>", self.ir_a_pagina)
        self.page_count_label = self._label(toolbar, "/ —", size=12)
        self.page_count_label.pack(side="left", padx=(2, 8))
        self._button(toolbar, "›", self.pagina_siguiente, width=31, kind="plain").pack(side="left", padx=(0, 6))
        ctk.CTkFrame(toolbar, width=1, height=28, fg_color=BORDER).pack(side="left", padx=4)
        self._button(toolbar, "−", self.zoom_menos, width=31, kind="plain").pack(side="left", padx=3)
        self._label(toolbar, "", size=11, color=NAVY, bold=True, textvariable=self.zoom_var).pack(side="left", padx=4)
        self._button(toolbar, "+", self.zoom_mas, width=31, kind="plain").pack(side="left", padx=3)
        self._button(toolbar, "Ancho", self.ajustar_ancho, width=59).pack(side="left", padx=(7, 2))
        self._button(toolbar, "Página", self.ajustar_documento, width=62).pack(side="left", padx=2)
        self._button(toolbar, "↻ 90°", self.rotar_vista, width=64, kind="plain").pack(side="right", padx=3)

        searchbar = ctk.CTkFrame(card, fg_color="#F7F9FD", corner_radius=10)
        searchbar.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 9))
        searchbar.grid_columnconfigure(0, weight=1)
        self.search_entry = ctk.CTkEntry(
            searchbar, textvariable=self.search_var, placeholder_text="Buscar texto dentro del documento...",
            fg_color=WHITE, border_color=BORDER, corner_radius=8, height=33,
        )
        self.search_entry.grid(row=0, column=0, sticky="ew", padx=(9, 5), pady=8)
        self.search_entry.bind("<Return>", lambda e: self.buscar_texto())
        self._button(searchbar, "Buscar", self.buscar_texto, width=57, kind="primary", height=32).grid(row=0, column=1, padx=2)
        self._button(searchbar, "‹", self.resultado_anterior, width=29, kind="plain", height=32).grid(row=0, column=2, padx=2)
        self._button(searchbar, "›", self.resultado_siguiente, width=29, kind="plain", height=32).grid(row=0, column=3, padx=(2, 8))

        body = ctk.CTkFrame(card, fg_color="transparent")
        body.grid(row=3, column=0, sticky="nsew", padx=12)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)

        thumbs = ctk.CTkFrame(body, fg_color="#F7F9FD", width=155, corner_radius=9)
        thumbs.grid(row=0, column=0, sticky="nsw", padx=(0, 8))
        thumbs.grid_propagate(False)
        thumbs.grid_rowconfigure(1, weight=1)
        thumb_header = ctk.CTkFrame(thumbs, fg_color="transparent")
        thumb_header.grid(row=0, column=0, sticky="ew", padx=8, pady=8)
        self._label(thumb_header, "PÁGINAS", size=10, color=MUTED, bold=True).pack(side="left")
        self.thumb_scroll = ctk.CTkScrollableFrame(thumbs, fg_color="transparent", width=135)
        self.thumb_scroll.grid(row=1, column=0, sticky="nsew", padx=4)
        thumb_controls = ctk.CTkFrame(thumbs, fg_color="transparent")
        thumb_controls.grid(row=2, column=0, padx=4, pady=(6, 9), sticky="ew")
        self._button(thumb_controls, "‹", self.prev_thumb_batch, width=30, height=28, kind="plain").pack(side="left")
        self.thumb_batch_label = self._label(thumb_controls, "0 / 0", size=10, color=MUTED)
        self.thumb_batch_label.pack(side="left", expand=True)
        self._button(thumb_controls, "›", self.next_thumb_batch, width=30, height=28, kind="plain").pack(side="right")

        canvas_wrap = ctk.CTkFrame(body, fg_color=CANVAS_BG, corner_radius=9)
        canvas_wrap.grid(row=0, column=1, sticky="nsew")
        canvas_wrap.grid_columnconfigure(0, weight=1)
        canvas_wrap.grid_rowconfigure(0, weight=1)
        self.canvas = tk.Canvas(canvas_wrap, bg=CANVAS_BG, borderwidth=0, highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky="nsew", padx=(2, 0), pady=(2, 0))
        self.v_scroll = ctk.CTkScrollbar(canvas_wrap, orientation="vertical", command=self.canvas.yview, width=12)
        self.v_scroll.grid(row=0, column=1, sticky="ns", pady=(2, 12))
        self.h_scroll = ctk.CTkScrollbar(canvas_wrap, orientation="horizontal", command=self.canvas.xview, height=12)
        self.h_scroll.grid(row=1, column=0, sticky="ew", padx=(2, 0))
        self.canvas.configure(yscrollcommand=self.v_scroll.set, xscrollcommand=self.h_scroll.set)
        self.canvas.bind("<Configure>", self._canvas_resize)
        self.canvas.bind("<MouseWheel>", self._canvas_mousewheel)
        self.canvas.bind("<Shift-MouseWheel>", self._canvas_hwheel)
        self.canvas.bind("<Button-4>", lambda e: self.canvas.yview_scroll(-3, "units"))
        self.canvas.bind("<Button-5>", lambda e: self.canvas.yview_scroll(3, "units"))
        self.canvas.bind("<ButtonPress-2>", lambda e: self.canvas.scan_mark(e.x, e.y))
        self.canvas.bind("<B2-Motion>", lambda e: self.canvas.scan_dragto(e.x, e.y, gain=1))

        viewer_footer = ctk.CTkFrame(card, fg_color="transparent", height=38)
        viewer_footer.grid(row=4, column=0, sticky="ew", padx=16, pady=(6, 5))
        viewer_footer.grid_columnconfigure(0, weight=1)
        self._label(viewer_footer, "", size=11, color=MUTED, textvariable=self.doc_info_var).grid(row=0, column=0, sticky="w")
        self._label(viewer_footer, "", size=11, color=MUTED, textvariable=self.search_result_var).grid(row=0, column=1, sticky="e")

    def _create_form(self, parent) -> None:
        card = ctk.CTkFrame(parent, fg_color=WHITE, corner_radius=14, border_width=1, border_color=BORDER, width=360)
        card.grid(row=0, column=1, sticky="nsew")
        card.grid_propagate(False)
        card.grid_rowconfigure(0, weight=1)
        card.grid_columnconfigure(0, weight=1)
        form = ctk.CTkScrollableFrame(card, fg_color=WHITE, corner_radius=14, width=320)
        form.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)

        self._label(form, "Datos del expediente", size=17, color=NAVY, bold=True).pack(anchor="w", padx=16, pady=(18, 0))
        self._label(form, "Introduce los datos manualmente", size=11, color=MUTED).pack(anchor="w", padx=16, pady=(1, 13))

        self.drop_frame = ctk.CTkFrame(form, fg_color=BLUE_PALE, border_width=1, border_color="#C4D8FA", corner_radius=12, height=96)
        self.drop_frame.pack(fill="x", padx=16, pady=(0, 11))
        self.drop_frame.pack_propagate(False)
        self.drop_label = self._label(self.drop_frame, "↓   ARRASTRA AQUÍ UN PDF", color=BLUE, size=12, bold=True)
        self.drop_label.pack(pady=(15, 0))
        self._label(self.drop_frame, "o haz clic para seleccionar un archivo", color=MUTED, size=10).pack(pady=(3, 0))
        self.drop_frame.drop_target_register(DND_FILES)
        self.drop_frame.dnd_bind("<<Drop>>", self.al_soltar)
        self.drop_frame.bind("<Button-1>", lambda e: self.seleccionar())
        for child in self.drop_frame.winfo_children():
            child.bind("<Button-1>", lambda e: self.seleccionar())
            try:
                child.drop_target_register(DND_FILES)
                child.dnd_bind("<<Drop>>", self.al_soltar)
            except Exception:
                pass
        self.path_label = self._label(form, "Ningún archivo seleccionado", size=10, color=MUTED, wraplength=295)
        self.path_label.pack(anchor="w", padx=17, pady=(0, 10))

        for text, var in [("NOMBRE", self.nom), ("APELLIDOS", self.ape), ("CIC", self.cic)]:
            self._label(form, text, size=10, color=MUTED, bold=True).pack(anchor="w", padx=16, pady=(9, 3))
            ctk.CTkEntry(
                form, textvariable=var, height=36, corner_radius=8,
                fg_color="#FAFBFF", border_color=BORDER, font=ctk.CTkFont(size=12),
            ).pack(fill="x", padx=16)

        self._section(form, "TIPO DOCUMENTAL")
        ctk.CTkSegmentedButton(
            form, values=["BIHOTZ", "LOGO"], variable=self.tipo,
            command=lambda _value: self.actualizar_paneles(),
            height=34, corner_radius=8, selected_color=BLUE, selected_hover_color=BLUE_HOVER,
            unselected_color="#EAF0F8", unselected_hover_color="#DFE9F5",
            text_color=NAVY, text_color_disabled=MUTED,
        ).pack(fill="x", padx=16, pady=(6, 0))

        self._section(form, "GUARDAR EN")
        dest_frame = ctk.CTkFrame(form, fg_color="transparent")
        dest_frame.pack(fill="x", padx=16)
        for label, value in [("Unidad T: (carpeta del servicio)", "T_DRIVE"), ("Escritorio", "ESCRITORIO")]:
            ctk.CTkRadioButton(
                dest_frame, text=label, variable=self.destino_var, value=value, radiobutton_width=17,
                radiobutton_height=17, border_color="#9DB0CA", fg_color=BLUE, hover_color=BLUE_HOVER,
                font=ctk.CTkFont(size=12), text_color=NAVY,
            ).pack(anchor="w", pady=4)

        self._section(form, "ACCIONES DOCUMENTALES")
        self.btn_generar = self._button(form, "GUARDAR DOCUMENTO", self.generar, kind="primary", height=42)
        self.btn_generar.pack(fill="x", padx=16, pady=(7, 8))
        common = ctk.CTkFrame(form, fg_color="transparent")
        common.pack(fill="x", padx=16)
        common.grid_columnconfigure(0, weight=1)
        common.grid_columnconfigure(1, weight=1)
        self.btn_abrir = self._button(common, "Abrir carpeta", self.abrir_carpeta, kind="plain", width=112, state="disabled")
        self.btn_abrir.grid(row=0, column=0, sticky="ew", padx=(0, 4))
        self.btn_firmado = self._button(common, "Firmado", self.firmado_descargas, kind="soft", width=112, state="disabled")
        self.btn_firmado.grid(row=0, column=1, sticky="ew", padx=(4, 0))
        self.btn_volantes = self._button(form, "Guardar volantes", self.guardar_volantes, kind="plain", height=36)
        self.btn_volantes.pack(fill="x", padx=16, pady=(8, 2))

        self.frame_bihotz = ctk.CTkFrame(form, fg_color="#F7F9FD", corner_radius=10)
        self._label(self.frame_bihotz, "GESTIÓN DIARIA · BIHOTZ", size=11, bold=True, color=NAVY).pack(anchor="w", padx=11, pady=(10, 5))
        self._button(self.frame_bihotz, "Crear carpeta del día", self.crear_carpeta_dia, kind="plain").pack(fill="x", padx=10, pady=3)
        self._button(self.frame_bihotz, "Abrir carpeta del día", self.abrir_carpeta_dia, kind="plain").pack(fill="x", padx=10, pady=3)
        self._button(self.frame_bihotz, "Comprimir día · 7z", self.comprimir_dia, kind="soft").pack(fill="x", padx=10, pady=(3, 10))

        self.frame_logo = ctk.CTkFrame(form, fg_color="#F7F9FD", corner_radius=10)
        self._label(self.frame_logo, "LOGOPEDIA · CENTRO", size=11, color=NAVY, bold=True).pack(anchor="w", padx=11, pady=(10, 5))
        for value, label in [("MATIA", "MATIA"), ("ARANSGI", "ARANSGI")]:
            ctk.CTkRadioButton(
                self.frame_logo, text=label, variable=self.centro_logo_var, value=value,
                radiobutton_width=16, radiobutton_height=16, fg_color=BLUE, text_color=NAVY,
            ).pack(anchor="w", padx=12, pady=4)
        self._button(self.frame_logo, "Comprimir firmado · 7z", self.comprimir_logopedia, kind="soft").pack(fill="x", padx=10, pady=(8, 10))
        self.actualizar_paneles()
        self._label(form, "Los PDF se visualizan sin modificar su contenido.", wraplength=280, size=10).pack(anchor="w", padx=16, pady=(12, 19))

    def actualizar_paneles(self) -> None:
        self.frame_bihotz.pack_forget()
        self.frame_logo.pack_forget()
        if self.tipo.get() == "BIHOTZ":
            self.frame_bihotz.pack(fill="x", padx=16, pady=(12, 4))
        else:
            self.frame_logo.pack(fill="x", padx=16, pady=(12, 4))

    def _keyboard_shortcuts(self) -> None:
        self.bind_all("<Control-o>", lambda _e: self.seleccionar())
        self.bind_all("<Control-f>", lambda _e: self.search_entry.focus_set())
        self.bind_all("<Control-MouseWheel>", self.hacer_zoom)
        self.bind_all("<Control-plus>", lambda _e: self.zoom_mas())
        self.bind_all("<Control-minus>", lambda _e: self.zoom_menos())

    def _draw_empty(self) -> None:
        if self.pdf.is_open:
            return
        self.canvas.delete("all")
        w, h = max(1, self.canvas.winfo_width()), max(1, self.canvas.winfo_height())
        self.canvas.create_text(w/2, h/2 - 35, text="▣", fill="#A1B2C9", font=("Segoe UI", 40))
        self.canvas.create_text(w/2, h/2 + 5, text="Tu documento aparecerá aquí", fill=NAVY, font=("Segoe UI", 15, "bold"))
        self.canvas.create_text(w/2, h/2 + 30, text="Abre un PDF para navegar por todas sus páginas", fill=MUTED, font=("Segoe UI", 11))
        self.canvas.configure(scrollregion=(0, 0, w, h))

    def seleccionar(self) -> None:
        path = filedialog.askopenfilename(title="Seleccionar PDF", filetypes=[("Archivos PDF", "*.pdf")])
        if path:
            self.cargar_nuevo_pdf(path)

    def al_soltar(self, event) -> None:
        try:
            paths = self.tk.splitlist(event.data)
            pdf_paths = [p for p in paths if Path(p).suffix.lower() == ".pdf"]
            if len(pdf_paths) != 1:
                messagebox.showwarning("Archivo no válido", "Arrastra un único archivo PDF.")
                return
            self.cargar_nuevo_pdf(pdf_paths[0])
        except Exception as exc:
            messagebox.showerror("No se pudo importar", str(exc))

    def cargar_nuevo_pdf(self, filepath: str) -> None:
        try:
            self.pdf.open(filepath)
        except PDFViewerError as exc:
            messagebox.showerror("Error al abrir PDF", str(exc))
            return
        self._search_token += 1
        self._searching = False
        self._matches = []
        self._match_index = -1
        self.search_var.set("")
        self.search_result_var.set("Buscar en el PDF")
        self.nom.set(""); self.ape.set(""); self.cic.set("")
        self.pdf_path.set(filepath)
        self.path_label.configure(text=f"PDF: {Path(filepath).name}")
        self.carpeta_generada = None
        self.archivo_firmado_path = None
        self.btn_abrir.configure(state="disabled")
        self.btn_firmado.configure(state="disabled")
        self.page_index = 0
        self.view_rotation = 0
        self.thumb_batch = 0
        self.fit_mode = "page"
        self._update_navigation()
        self._refresh_thumbnails()
        self.after(70, self.ajustar_documento)
        self._status(f"Documento cargado: {Path(filepath).name} · {self.pdf.page_count} página(s)")

    def _update_navigation(self) -> None:
        if self.pdf.is_open:
            self.page_var.set(str(self.page_index+1))
            self.page_count_label.configure(text=f"/ {self.pdf.page_count}")
            self.doc_info_var.set(f"Página {self.page_index+1} de {self.pdf.page_count}  ·  Vista sin cambios en el PDF")
        else:
            self.page_var.set("—")
            self.page_count_label.configure(text="/ —")
            self.doc_info_var.set("Sin documento abierto")

    def ir_a_pagina(self, _event=None) -> None:
        if not self.pdf.is_open:
            return
        try:
            target = int(self.page_var.get()) - 1
        except ValueError:
            self._update_navigation()
            return
        self._set_page(max(0, min(target, self.pdf.page_count - 1)))

    def pagina_anterior(self) -> None:
        self._set_page(self.page_index - 1)

    def pagina_siguiente(self) -> None:
        self._set_page(self.page_index + 1)

    def _set_page(self, index: int) -> None:
        if not self.pdf.is_open or not 0 <= index < self.pdf.page_count:
            return
        self.page_index = index
        self._update_navigation()
        batch = index // THUMBS_PER_BATCH
        if batch != self.thumb_batch:
            self.thumb_batch = batch
            self._refresh_thumbnails()
        else:
            self._highlight_selected_thumb()
        if self.fit_mode == "width":
            self.ajustar_ancho()
        elif self.fit_mode == "page":
            self.ajustar_documento()
        else:
            self.renderizar_pagina()

    def _refresh_thumbnails(self) -> None:
        for child in self.thumb_scroll.winfo_children():
            child.destroy()
        self._thumb_photos.clear()
        if not self.pdf.is_open:
            self.thumb_batch_label.configure(text="0 / 0")
            return
        begin = self.thumb_batch * THUMBS_PER_BATCH
        end = min(begin + THUMBS_PER_BATCH, self.pdf.page_count)
        total = (self.pdf.page_count + THUMBS_PER_BATCH - 1) // THUMBS_PER_BATCH
        self.thumb_batch_label.configure(text=f"{self.thumb_batch+1} / {total}")
        self._thumb_items: list[tuple[int, ctk.CTkFrame]] = []
        for index in range(begin, end):
            selected = index == self.page_index
            tile = ctk.CTkFrame(
                self.thumb_scroll, corner_radius=9, border_width=1,
                border_color=BLUE if selected else BORDER,
                fg_color=BLUE_PALE if selected else WHITE,
            )
            tile.pack(fill="x", padx=4, pady=5)
            try:
                thumbnail = self.pdf.thumbnail(index, 105, 139)
                photo = ImageTk.PhotoImage(thumbnail, master=self)
                self._thumb_photos.append(photo)
                preview = tk.Label(tile, image=photo, borderwidth=0, bg=WHITE, cursor="hand2")
                preview.pack(padx=6, pady=(7, 1))
                preview.bind("<Button-1>", lambda _e, n=index: self._set_page(n))
            except PDFViewerError:
                self._label(tile, "Vista no disponible", size=9).pack(padx=4, pady=9)
            caption = self._label(tile, f"Página {index+1}", size=10, color=NAVY if selected else MUTED)
            caption.pack(pady=(1, 6))
            caption.bind("<Button-1>", lambda _e, n=index: self._set_page(n))
            tile.bind("<Button-1>", lambda _e, n=index: self._set_page(n))
            self._thumb_items.append((index, tile))

    def _highlight_selected_thumb(self) -> None:
        for index, tile in getattr(self, "_thumb_items", []):
            active = index == self.page_index
            tile.configure(border_color=BLUE if active else BORDER, fg_color=BLUE_PALE if active else WHITE)

    def prev_thumb_batch(self) -> None:
        if self.pdf.is_open and self.thumb_batch > 0:
            self.thumb_batch -= 1
            self._refresh_thumbnails()

    def next_thumb_batch(self) -> None:
        if self.pdf.is_open and (self.thumb_batch + 1) * THUMBS_PER_BATCH < self.pdf.page_count:
            self.thumb_batch += 1
            self._refresh_thumbnails()

    def ajustar_ancho(self) -> None:
        if not self.pdf.is_open:
            return
        self.fit_mode = "width"
        page_w, _ = self.pdf.dimensions(self.page_index, self.view_rotation)
        available = max(200, self.canvas.winfo_width() - 48)
        self.zoom = min(MAX_ZOOM, max(MIN_ZOOM, available / page_w))
        self.renderizar_pagina()

    def ajustar_documento(self) -> None:
        if not self.pdf.is_open:
            return
        self.fit_mode = "page"
        w, h = self.pdf.dimensions(self.page_index, self.view_rotation)
        avail_w = max(200, self.canvas.winfo_width() - 48)
        avail_h = max(200, self.canvas.winfo_height() - 48)
        self.zoom = min(MAX_ZOOM, max(MIN_ZOOM, min(avail_w / w, avail_h / h)))
        self.renderizar_pagina()

    def _zoom(self, multiplier: float) -> None:
        if not self.pdf.is_open:
            return
        self.fit_mode = "custom"
        self.zoom = min(MAX_ZOOM, max(MIN_ZOOM, self.zoom * multiplier))
        self.renderizar_pagina()

    def zoom_mas(self) -> None:
        self._zoom(1.2)

    def zoom_menos(self) -> None:
        self._zoom(1/1.2)

    def hacer_zoom(self, event) -> None:
        if self.pdf.is_open:
            self._zoom(1.15 if event.delta > 0 else 1/1.15)

    def rotar_vista(self) -> None:
        if not self.pdf.is_open:
            return
        self.view_rotation = (self.view_rotation + 90) % 360
        if self.fit_mode == "width":
            self.ajustar_ancho()
        elif self.fit_mode == "page":
            self.ajustar_documento()
        else:
            self.renderizar_pagina()
        self._status("Rotación visual aplicada; el archivo original permanece intacto")

    def renderizar_pagina(self) -> None:
        if not self.pdf.is_open:
            self._draw_empty()
            return
        try:
            current = self._matches[self._match_index] if 0 <= self._match_index < len(self._matches) else None
            highlights = [
                (match, match is current)
                for match in self._matches if match.page == self.page_index
            ]
            image = self.pdf.render(self.page_index, self.zoom, self.view_rotation, highlights)
            self._canvas_photo = ImageTk.PhotoImage(image, master=self)
            width = max(self.canvas.winfo_width(), image.width + 45)
            height = max(self.canvas.winfo_height(), image.height + 45)
            x = max(22, (width - image.width) // 2)
            y = max(22, (height - image.height) // 2)
            self.canvas.delete("all")
            self.canvas.create_rectangle(x + 2, y + 3, x + image.width + 5, y + image.height + 5, fill="#D8DFEA", outline="")
            self.canvas.create_image(x, y, image=self._canvas_photo, anchor="nw")
            self.canvas.configure(scrollregion=(0, 0, width, height))
            self.zoom_var.set(f"{round(self.zoom * 100)} %")
            self.canvas.xview_moveto(0)
            self.canvas.yview_moveto(0)
            if current is not None and current.page == self.page_index:
                # Resaltar en el scroll la coincidencia enfocada, también con rotación de la vista.
                self._scroll_to_active(current)
        except PDFViewerError as exc:
            self._status(str(exc))
            messagebox.showwarning("Visor PDF", str(exc))

    def _scroll_to_active(self, match: Match) -> None:
        # El resaltado está en la imagen; enfocamos la zona vertical sin alterar el documento.
        try:
            page_w, page_h = self.pdf.dimensions(self.page_index)
            r = match.rect
            center_x, center_y = (r[0]+r[2])/2, (r[1]+r[3])/2
            pos = {
                0: (center_x/page_w, center_y/page_h),
                90: (1-center_y/page_h, center_x/page_w),
                180: (1-center_x/page_w, 1-center_y/page_h),
                270: (center_y/page_h, 1-center_x/page_w),
            }[self.view_rotation]
            bounds = [float(v) for v in self.canvas.cget("scrollregion").split()]
            vw, vh = self.canvas.winfo_width(), self.canvas.winfo_height()
            scroll_w, scroll_h = bounds[2]-bounds[0], bounds[3]-bounds[1]
            if scroll_w > vw:
                self.canvas.xview_moveto(max(0, min(1, (pos[0]*scroll_w-vw/2)/max(1, scroll_w-vw))))
            if scroll_h > vh:
                self.canvas.yview_moveto(max(0, min(1, (pos[1]*scroll_h-vh/2)/max(1, scroll_h-vh))))
        except (ValueError, KeyError, ZeroDivisionError):
            pass

    def _canvas_resize(self, _event) -> None:
        if self._resize_task:
            self.after_cancel(self._resize_task)
        self._resize_task = self.after(180, self._on_canvas_resized)

    def _on_canvas_resized(self) -> None:
        self._resize_task = None
        if not self.pdf.is_open:
            self._draw_empty()
        elif self.fit_mode == "width":
            self.ajustar_ancho()
        elif self.fit_mode == "page":
            self.ajustar_documento()
        else:
            self.renderizar_pagina()

    def _canvas_mousewheel(self, event):
        if event.state & 0x0004:  # Control: zoom, gestionado por bind_all
            return
        self.canvas.yview_scroll(int(-event.delta / 120) * 3, "units")
        return "break"

    def _canvas_hwheel(self, event):
        self.canvas.xview_scroll(int(-event.delta / 120) * 3, "units")
        return "break"

    def buscar_texto(self) -> None:
        """Búsqueda solo a petición del usuario. No busca ni extrae datos personales automáticamente."""
        if not self.pdf.is_open:
            return
        query = self.search_var.get().strip()
        self._search_token += 1
        token = self._search_token
        self._matches = []
        self._match_index = -1
        if not query:
            self.search_result_var.set("Buscar en el PDF")
            self.renderizar_pagina()
            return
        self._searching = True
        self.search_result_var.set("Buscando...")
        self._search_batch(token, query, 0)

    def _search_batch(self, token: int, query: str, index: int) -> None:
        if token != self._search_token or not self.pdf.is_open:
            return
        end = min(index + 4, self.pdf.page_count)
        try:
            for page in range(index, end):
                self._matches.extend(self.pdf.find_in_page(page, query))
                if len(self._matches) >= 1500:
                    self._finish_search(token, partial=True)
                    return
        except PDFViewerError as exc:
            self._searching = False
            self.search_result_var.set("Error en búsqueda")
            messagebox.showwarning("Búsqueda de texto", str(exc))
            return
        if end < self.pdf.page_count:
            self.search_result_var.set(f"Buscando... {end}/{self.pdf.page_count} páginas")
            self.after(1, lambda: self._search_batch(token, query, end))
        else:
            self._finish_search(token)

    def _finish_search(self, token: int, partial: bool = False) -> None:
        if token != self._search_token:
            return
        self._searching = False
        if not self._matches:
            self.search_result_var.set("Sin coincidencias")
            self.renderizar_pagina()
            return
        self._match_index = 0
        self._update_search_indicator(partial)
        self._set_page(self._matches[0].page)

    def _update_search_indicator(self, partial: bool = False) -> None:
        if not self._matches:
            self.search_result_var.set("Sin coincidencias")
            return
        suffix = "+" if partial or len(self._matches) >= 1500 else ""
        self.search_result_var.set(f"Resultado {self._match_index+1} de {len(self._matches)}{suffix}")

    def resultado_siguiente(self) -> None:
        self._move_search(1)

    def resultado_anterior(self) -> None:
        self._move_search(-1)

    def _move_search(self, step: int) -> None:
        if not self._matches or self._searching:
            return
        self._match_index = (self._match_index + step) % len(self._matches)
        self._update_search_indicator()
        self._set_page(self._matches[self._match_index].page)

    def _status(self, text: str) -> None:
        self.status_var.set(text)

    def _base_dir(self) -> Path:
        if self.destino_var.get() == "ESCRITORIO":
            desktop = Path.home() / "Desktop"
            return desktop if desktop.exists() else Path.home() / "Escritorio"
        folder = "BIHOTZ" if self.tipo.get() == "BIHOTZ" else "LOGOPEDIA"
        return BASE_ROOT / str(datetime.now().year) / folder

    def _day_dir(self) -> Path:
        today = datetime.now().strftime("%d-%m-%Y")
        return BASE_ROOT / str(datetime.now().year) / "BIHOTZ POR DIAS" / f"BIHOTZ {today}"

    @staticmethod
    def _safe_segment(text: str) -> bool:
        # Mantener rutas esperadas sin permitir rutas relativas o caracteres ilegales.
        return bool(text.strip()) and not re.search(r'[<>:"/\\|?*\x00-\x1f]', text) and text.strip() not in (".", "..")

    @staticmethod
    def _copy_with_confirmation(source: Path, target: Path) -> bool:
        if source.resolve() == target.resolve():
            return True
        if target.exists() and not messagebox.askyesno(
            "El archivo ya existe", f"Ya existe este archivo:\n\n{target.name}\n\n¿Quieres reemplazarlo?",
        ):
            return False
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        return True

    def generar(self) -> None:
        if not self.pdf.is_open:
            messagebox.showwarning("Falta el PDF", "Selecciona primero un documento PDF.")
            return
        if not all(self._safe_segment(v.get()) for v in (self.nom, self.ape, self.cic)):
            messagebox.showwarning("Datos incompletos", "Introduce nombre, apellidos y CIC. Evita caracteres no válidos para nombres de archivo.")
            return
        folder = self._base_dir() / f"{self.ape.get().strip()},{self.nom.get().strip()}"
        target = folder / f"{self.tipo.get()} CIC {self.cic.get().strip()}.pdf"
        try:
            if not self._copy_with_confirmation(Path(self.pdf_path.get()), target):
                self._status("Guardado cancelado; el documento existente no se ha modificado")
                return
            self.carpeta_generada = folder
            self.btn_abrir.configure(state="normal")
            self.btn_firmado.configure(state="normal")
            self._status(f"Documento guardado correctamente · {target.name}")
            messagebox.showinfo("Documento guardado", f"El documento se ha guardado en:\n{target}")
        except OSError as exc:
            messagebox.showerror("Error al guardar", f"No se ha podido guardar el documento:\n{exc}\n\nComprueba la unidad T: y los permisos.")

    def abrir_carpeta(self) -> None:
        if self.carpeta_generada and self.carpeta_generada.is_dir():
            os.startfile(str(self.carpeta_generada))

    def _downloads(self) -> Path:
        return Path.home() / "Downloads"

    def _found_files(self) -> list[Path]:
        # Preserva la búsqueda manual por nombre del flujo original.
        path = self._downloads()
        if not path.is_dir():
            raise FileNotFoundError(f"No se encuentra la carpeta de Descargas: {path}")
        pattern = f"{self.tipo.get()} CIC {self.cic.get().strip()}".casefold()
        return [f for f in path.iterdir() if f.is_file() and pattern in f.name.casefold()]

    def firmado_descargas(self) -> None:
        if not self.carpeta_generada or not self.carpeta_generada.is_dir():
            messagebox.showwarning("Expediente", "Primero guarda el documento en su carpeta.")
            return
        try:
            files = self._found_files()
            if not files:
                messagebox.showwarning("Firmado", "No se encontró ningún archivo con el nombre indicado en Descargas.")
                return
            if not messagebox.askyesno("Confirmar documentos", "Se han encontrado estos archivos:\n\n" + "\n".join(f.name for f in files) + "\n\n¿Copiarlos?"):
                return
            successes = 0
            for path in files:
                target = self.carpeta_generada / path.name
                if not self._copy_with_confirmation(path, target):
                    continue
                if self.tipo.get() == "BIHOTZ":
                    day_target = self._day_dir() / path.name
                    if not self._copy_with_confirmation(path, day_target):
                        continue
                self.archivo_firmado_path = target
                successes += 1
            self._status(f"Archivos firmados importados: {successes}")
            messagebox.showinfo("Firmado", f"Se han copiado {successes} documento(s).")
        except (OSError, FileNotFoundError) as exc:
            messagebox.showerror("Error", str(exc))

    def guardar_volantes(self) -> None:
        if not self.cic.get().strip():
            messagebox.showwarning("Falta CIC", "Introduce primero el CIC.")
            return
        try:
            files = self._found_files()
            if not files:
                messagebox.showwarning("Volantes", "No se han encontrado documentos coincidentes en Descargas.")
                return
            if not messagebox.askyesno("Confirmar volantes", "Archivos encontrados:\n\n" + "\n".join(f.name for f in files) + "\n\n¿Guardarlos en Volantes?"):
                return
            successes = sum(1 for path in files if self._copy_with_confirmation(path, VOLANTES_ROOT / path.name))
            self._status(f"Volantes copiados: {successes}")
            messagebox.showinfo("Volantes", f"Se han guardado {successes} documento(s).")
        except OSError as exc:
            messagebox.showerror("Volantes", str(exc))

    def crear_carpeta_dia(self) -> None:
        try:
            path = self._day_dir()
            path.mkdir(parents=True, exist_ok=True)
            self._status(f"Carpeta del día disponible: {path.name}")
            os.startfile(str(path))
        except OSError as exc:
            messagebox.showerror("Carpeta del día", str(exc))

    def abrir_carpeta_dia(self) -> None:
        path = self._day_dir()
        if not path.is_dir():
            messagebox.showwarning("Carpeta del día", "La carpeta del día no existe. Utiliza «Crear carpeta del día».")
            return
        os.startfile(str(path))

    @staticmethod
    def _find_7zip() -> Path | None:
        for path in (Path(r"C:\Program Files\7-Zip\7z.exe"), Path(r"C:\Program Files (x86)\7-Zip\7z.exe")):
            if path.is_file():
                return path
        return None

    def _compress(self, source: Path, archive: Path, title: str) -> None:
        exe = self._find_7zip()
        if not exe:
            messagebox.showerror("7-Zip no disponible", "No se encuentra 7-Zip instalado en este equipo.")
            return
        # Las claves no deben guardarse en el repositorio, el EXE ni los mensajes de error.
        password = simpledialog.askstring("Contraseña del archivo", f"Introduce la contraseña autorizada para {title}:", show="*", parent=self)
        if password is None:
            return
        if not password:
            messagebox.showwarning("Falta la contraseña", "No se ha creado el archivo comprimido.")
            return
        if archive.exists() and not messagebox.askyesno("El comprimido ya existe", f"¿Quieres actualizar el archivo existente?\n{archive.name}"):
            return
        try:
            result = subprocess.run(
                [str(exe), "a", "-t7z", f"-p{password}", "-mhe=on", str(archive), str(source)],
                capture_output=True, text=True, timeout=180,
            )
            if result.returncode != 0:
                # Evitar mostrar stdout/stderr: algunas herramientas incluyen los argumentos.
                raise RuntimeError("La compresión no terminó correctamente. Comprueba el archivo y la ruta de destino.")
            self._status(f"Archivo comprimido: {archive.name}")
            messagebox.showinfo("Compresión completada", f"Se ha creado el archivo:\n{archive}")
        except (OSError, subprocess.TimeoutExpired, RuntimeError) as exc:
            messagebox.showerror("Compresión", str(exc))

    def comprimir_dia(self) -> None:
        path = self._day_dir()
        if not path.is_dir():
            messagebox.showwarning("Comprimir día", "Primero crea la carpeta del día.")
            return
        self._compress(path, path.with_suffix(".7z"), "BIHOTZ")

    def comprimir_logopedia(self) -> None:
        if not self.archivo_firmado_path or not self.archivo_firmado_path.is_file():
            messagebox.showwarning("Comprimir LOGOPEDIA", "Primero incorpora el archivo firmado desde Descargas.")
            return
        self._compress(self.archivo_firmado_path, self.archivo_firmado_path.with_suffix(".7z"), self.centro_logo_var.get())

    def _close(self) -> None:
        self._search_token += 1
        self.pdf.close()
        self.destroy()


def main() -> None:
    App().mainloop()


if __name__ == "__main__":
    main()
