"""Gestor PDF 2.6.1 · Visor avanzado con circuitos BIHOTZ, LOGO y POLICLINICA.

Ninguna función reconoce automáticamente pacientes, CIC, nombres ni apellidos.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import uuid
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk
from PIL import ImageTk
from tkinterdnd2 import DND_FILES, TkinterDnD

from pdf_core import Match, PDFDocument, PDFViewerError
from document_routes import expediente_directory, find_matching_downloads, get_route, original_filename
from bihotz_email import (archive_stamp, folder_snapshot, prepare_outlook_draft, validate_daily_archive, RECIPIENT)
from history_store import HistoryStore
from history_window import HistoryWindow
from archive_security import (
    get_service_password, creation_command,
    test_command, list_command,
)


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
        self.title("Gestor documental | BIHOTZ · LOGOPEDIA · POLICLINICA")
        # Ajustar tamaño inicial a la pantalla sin introducir scroll en el panel lateral.
        width = min(1440, max(1090, self.winfo_screenwidth() - 80))
        height = min(875, max(690, self.winfo_screenheight() - 90))
        self.geometry(f"{width}x{height}")
        self.minsize(1090, 690)
        self.configure(bg=BG)

        self.pdf = PDFDocument()
        self.page_index = 0
        self.view_rotation = 0
        self.zoom = 1.0
        self.fit_mode = "page"
        self.thumb_batch = 0
        self._thumbnails_visible = False
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
        self._saved_context: tuple[str, ...] | None = None
        self._last_doc_type = self.tipo.get()
        self._bihotz_ready_archive: Path | None = None
        self._bihotz_snapshot: tuple[tuple[str, int, int], ...] | None = None
        self._bihotz_archive_stamp: tuple[int, int] | None = None
        self._history_store: HistoryStore | None = None
        self._history_window: HistoryWindow | None = None
        self._history_error_notified = False

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
        self._label(name_area, "BIHOTZ  /  LOGOPEDIA  /  POLICLINICA", size=11, color=MUTED).pack(anchor="w")
        self._label(header, "VISOR PDF · v2.6.1", size=11, color=MUTED, bold=True).grid(row=0, column=2, padx=16)
        self._button(header, "◷  Historial", self.abrir_historial, kind="plain", width=120, height=38).grid(row=0, column=3, padx=(2, 9))
        self._button(header, "+ Abrir PDF", self.seleccionar, kind="primary", width=132, height=38).grid(row=0, column=4, padx=(2, 24))

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
        headline.grid(row=0, column=0, sticky="ew", padx=18, pady=(13, 6))
        headline.grid_columnconfigure(0, weight=1)
        self._label(headline, "Vista del documento", size=15, color=NAVY, bold=True).grid(row=0, column=0, sticky="w")
        self.btn_thumbs = self._button(
            headline, "▦  Ver miniaturas", self._toggle_thumbnails, width=120, height=29, kind="soft",
        )
        self.btn_thumbs.grid(row=0, column=1, padx=(4, 15))
        self.btn_thumbs.grid_remove()  # Sin sentido para PDFs de una página.
        self._label(headline, "PDF original · Solo lectura", size=10, color=MUTED).grid(row=0, column=2, sticky="e")

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
        self.search_entry.grid(row=0, column=0, sticky="ew", padx=(9, 5), pady=6)
        self.search_entry.bind("<Return>", lambda e: self.buscar_texto())
        self._button(searchbar, "Buscar", self.buscar_texto, width=57, kind="primary", height=32).grid(row=0, column=1, padx=2)
        self._button(searchbar, "‹", self.resultado_anterior, width=29, kind="plain", height=32).grid(row=0, column=2, padx=2)
        self._button(searchbar, "›", self.resultado_siguiente, width=29, kind="plain", height=32).grid(row=0, column=3, padx=(2, 8))

        # Toda la anchura del visor queda destinada al documento.
        # El canvas también recibe el PDF arrastrado, esté vacío o abierto.
        canvas_wrap = ctk.CTkFrame(card, fg_color=CANVAS_BG, corner_radius=9)
        canvas_wrap.grid(row=3, column=0, sticky="nsew", padx=13)
        canvas_wrap.grid_columnconfigure(0, weight=1)
        canvas_wrap.grid_rowconfigure(0, weight=1)
        self.canvas = tk.Canvas(canvas_wrap, bg=CANVAS_BG, borderwidth=0, highlightthickness=0, cursor="arrow")
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
        self.canvas.bind("<Button-1>", self._on_viewer_click)
        for target in (canvas_wrap, self.canvas):
            target.drop_target_register(DND_FILES)
            target.dnd_bind("<<Drop>>", self.al_soltar)
            target.dnd_bind("<<DragEnter>>", self._drag_enter)
            target.dnd_bind("<<DragLeave>>", self._drag_leave)

        # Tira horizontal opcional: nunca ocupa espacio al abrir un PDF de una página.
        self.thumb_ribbon = ctk.CTkFrame(card, fg_color="#F7F9FD", corner_radius=9)
        self.thumb_ribbon.grid(row=4, column=0, sticky="ew", padx=13, pady=(8, 0))
        self.thumb_ribbon.grid_columnconfigure(0, weight=1)
        self.thumb_ribbon.grid_remove()
        ribbon_header = ctk.CTkFrame(self.thumb_ribbon, fg_color="transparent")
        ribbon_header.grid(row=0, column=0, sticky="ew", padx=11, pady=(5, 0))
        self._label(ribbon_header, "MINIATURAS", size=10, color=MUTED, bold=True).pack(side="left")
        self._button(ribbon_header, "›", self.next_thumb_batch, width=26, height=24, kind="plain").pack(side="right", padx=(2, 0))
        self.thumb_batch_label = self._label(ribbon_header, "0 / 0", size=10, color=MUTED)
        self.thumb_batch_label.pack(side="right", padx=9)
        self._button(ribbon_header, "‹", self.prev_thumb_batch, width=26, height=24, kind="plain").pack(side="right", padx=(0, 2))
        self.thumb_scroll = ctk.CTkScrollableFrame(
            self.thumb_ribbon, fg_color="transparent", height=126, orientation="horizontal",
        )
        self.thumb_scroll.grid(row=1, column=0, sticky="ew", padx=7, pady=(0, 5))

        viewer_footer = ctk.CTkFrame(card, fg_color="transparent", height=32)
        viewer_footer.grid(row=5, column=0, sticky="ew", padx=16, pady=(4, 4))
        viewer_footer.grid_columnconfigure(0, weight=1)
        self._label(viewer_footer, "", size=11, color=MUTED, textvariable=self.doc_info_var).grid(row=0, column=0, sticky="w")
        self._label(viewer_footer, "", size=11, color=MUTED, textvariable=self.search_result_var).grid(row=0, column=1, sticky="e")

    def _create_form(self, parent) -> None:
        # Panel fijo, sin CTkScrollableFrame y sin barra de desplazamiento vertical.
        card = ctk.CTkFrame(parent, fg_color=WHITE, corner_radius=14, border_width=1, border_color=BORDER, width=360)
        card.grid(row=0, column=1, sticky="nsew")
        card.grid_propagate(False)
        card.grid_columnconfigure(0, weight=1)
        card.grid_rowconfigure(0, weight=1)
        form = ctk.CTkFrame(card, fg_color="transparent")
        form.grid(row=0, column=0, sticky="nsew", padx=13, pady=(9, 8))
        form.grid_columnconfigure(0, weight=1)

        self._label(form, "Datos del expediente", size=17, color=NAVY, bold=True).pack(anchor="w", padx=4, pady=(3, 0))
        self._label(form, "Cumplimenta los datos manualmente", size=10, color=MUTED).pack(anchor="w", padx=4, pady=(0, 8))

        file_strip = ctk.CTkFrame(form, fg_color=BLUE_PALE, corner_radius=8, height=32)
        file_strip.pack(fill="x", padx=2, pady=(0, 9))
        file_strip.pack_propagate(False)
        self.path_label = self._label(file_strip, "PDF · Ningún documento abierto", size=11, color=BLUE)
        self.path_label.pack(side="left", padx=10, pady=5)

        # Dos columnas para evitar que los datos personales obliguen a desplazar el panel.
        fields = ctk.CTkFrame(form, fg_color="transparent")
        fields.pack(fill="x", padx=2)
        fields.grid_columnconfigure((0, 1), weight=1, uniform="person")
        for index, (text, var) in enumerate((("NOMBRE", self.nom), ("APELLIDOS", self.ape))):
            field = ctk.CTkFrame(fields, fg_color="transparent")
            field.grid(row=0, column=index, sticky="ew", padx=(0, 5) if index == 0 else (5, 0))
            self._label(field, text, size=10, color=MUTED, bold=True).pack(anchor="w", pady=(0, 2))
            ctk.CTkEntry(
                field, textvariable=var, height=33, corner_radius=8, fg_color="#FAFBFF",
                border_color=BORDER, font=ctk.CTkFont(size=12),
            ).pack(fill="x")
        self._label(form, "CIC", size=10, color=MUTED, bold=True).pack(anchor="w", padx=2, pady=(8, 2))
        ctk.CTkEntry(
            form, textvariable=self.cic, height=33, corner_radius=8,
            fg_color="#FAFBFF", border_color=BORDER, font=ctk.CTkFont(size=12),
        ).pack(fill="x", padx=2)

        # Preferencias compactas, con la misma lógica de negocio que la versión anterior.
        self._label(form, "TIPO DOCUMENTAL", size=10, color=NAVY, bold=True).pack(anchor="w", padx=2, pady=(11, 4))
        ctk.CTkSegmentedButton(
            form, values=["BIHOTZ", "LOGO", "POLICLINICA"], variable=self.tipo,
            command=lambda _value: self.actualizar_paneles(),
            height=31, corner_radius=8, selected_color=BLUE, selected_hover_color=BLUE_HOVER,
            unselected_color="#EAF0F8", unselected_hover_color="#DFE9F5",
            text_color=NAVY, text_color_disabled=MUTED,
        ).pack(fill="x", padx=2)

        self._label(form, "GUARDAR EN", size=10, color=NAVY, bold=True).pack(anchor="w", padx=2, pady=(11, 3))
        dest_frame = ctk.CTkFrame(form, fg_color="transparent")
        dest_frame.pack(fill="x", padx=2)
        for label, value in [("Unidad T:", "T_DRIVE"), ("Escritorio", "ESCRITORIO")]:
            ctk.CTkRadioButton(
                dest_frame, text=label, variable=self.destino_var, value=value,
                radiobutton_width=16, radiobutton_height=16,
                border_color="#9DB0CA", fg_color=BLUE, hover_color=BLUE_HOVER,
                font=ctk.CTkFont(size=11), text_color=NAVY,
            ).pack(side="left", expand=True, anchor="w", pady=(0, 2))

        self._label(form, "ACCIONES DOCUMENTALES", size=10, color=NAVY, bold=True).pack(anchor="w", padx=2, pady=(11, 4))
        self.btn_generar = self._button(form, "GUARDAR DOCUMENTO", self.generar, kind="primary", height=39)
        self.btn_generar.pack(fill="x", padx=2, pady=(0, 6))
        common = ctk.CTkFrame(form, fg_color="transparent")
        common.pack(fill="x", padx=2)
        common.grid_columnconfigure((0, 1, 2), weight=1, uniform="actions")
        self.btn_abrir = self._button(common, "Carpeta", self.abrir_carpeta, kind="plain", width=80, state="disabled", height=31)
        self.btn_abrir.grid(row=0, column=0, sticky="ew", padx=(0, 3))
        self.btn_firmado = self._button(common, "Firmado", self.firmado_descargas, kind="soft", width=80, state="disabled", height=31)
        self.btn_firmado.grid(row=0, column=1, sticky="ew", padx=3)
        self.btn_volantes = self._button(common, "Volantes", self.guardar_volantes, kind="plain", width=80, height=31)
        self.btn_volantes.grid(row=0, column=2, sticky="ew", padx=(3, 0))

        self.frame_bihotz = ctk.CTkFrame(form, fg_color="#F7F9FD", corner_radius=10)
        self._label(self.frame_bihotz, "GESTIÓN DIARIA · BIHOTZ", size=10, bold=True, color=NAVY).pack(anchor="w", padx=9, pady=(7, 4))
        day_actions = ctk.CTkFrame(self.frame_bihotz, fg_color="transparent")
        day_actions.pack(fill="x", padx=8, pady=(0, 8))
        day_actions.grid_columnconfigure((0, 1, 2, 3), weight=1, uniform="days")
        self._button(day_actions, "Crear día", self.crear_carpeta_dia, kind="plain", width=63, height=30).grid(row=0, column=0, sticky="ew", padx=(0, 3))
        self._button(day_actions, "Abrir día", self.abrir_carpeta_dia, kind="plain", width=63, height=30).grid(row=0, column=1, sticky="ew", padx=3)
        self._button(day_actions, "Comprimir", self.comprimir_dia, kind="soft", width=69, height=30).grid(row=0, column=2, sticky="ew", padx=3)
        self.btn_enviar_bihotz = self._button(day_actions, "ENVIAR", self.enviar_bihotz, kind="green", width=65, height=30, state="disabled")
        self.btn_enviar_bihotz.grid(row=0, column=3, sticky="ew", padx=(3, 0))

        self.frame_logo = ctk.CTkFrame(form, fg_color="#F7F9FD", corner_radius=10)
        self._label(self.frame_logo, "LOGOPEDIA · CENTRO", size=10, color=NAVY, bold=True).pack(anchor="w", padx=9, pady=(7, 4))
        logo_actions = ctk.CTkFrame(self.frame_logo, fg_color="transparent")
        logo_actions.pack(fill="x", padx=8, pady=(0, 8))
        center_choice = ctk.CTkFrame(logo_actions, fg_color="transparent")
        center_choice.pack(side="left", fill="x", expand=True)
        # Dos filas compactas para que el panel NO necesite scroll y quepa ASPACE.
        for index, value in enumerate(("MATIA", "ARANSGI", "ASPACE")):
            ctk.CTkRadioButton(
                center_choice, text=value, variable=self.centro_logo_var, value=value,
                radiobutton_width=15, radiobutton_height=15, fg_color=BLUE,
                text_color=NAVY, font=ctk.CTkFont(size=11),
                width=88,
            ).grid(row=index // 2, column=index % 2, sticky="w", pady=2, padx=(0, 3))
        self._button(logo_actions, "Comprimir", self.comprimir_logopedia, kind="soft", width=87, height=30).pack(side="right", padx=(4, 0))

        self.frame_poli = ctk.CTkFrame(form, fg_color="#F7F9FD", corner_radius=10)
        self._label(self.frame_poli, "POLICLINICA · DOCUMENTO FIRMADO", size=10, color=NAVY, bold=True).pack(anchor="w", padx=9, pady=(7, 4))
        poli_actions = ctk.CTkFrame(self.frame_poli, fg_color="transparent")
        poli_actions.pack(fill="x", padx=8, pady=(0, 8))
        self._label(poli_actions, "Clave del servicio asignada", size=10).pack(side="left")
        self._button(poli_actions, "Comprimir", self.comprimir_policlinica, kind="soft", width=92, height=30).pack(side="right")

        self.form_note = self._label(form, "Vista previa en modo lectura · PDF sin modificar", size=10, color=MUTED)
        self.form_note.pack(anchor="w", padx=2, pady=(9, 0))
        self.actualizar_paneles()

    def actualizar_paneles(self) -> None:
        # Nunca reutilizar una carpeta de otro circuito al cambiar la selección.
        if self.tipo.get() != self._last_doc_type:
            self.carpeta_generada = None
            self.archivo_firmado_path = None
            self._saved_context = None
            self.btn_abrir.configure(state="disabled")
            self.btn_firmado.configure(state="disabled")
            self._last_doc_type = self.tipo.get()
            self._status("Tipo documental cambiado · Guarda de nuevo el documento")
        self.frame_bihotz.pack_forget()
        self.frame_logo.pack_forget()
        self.frame_poli.pack_forget()
        selected = self.tipo.get()
        panel = self.frame_bihotz if selected == "BIHOTZ" else self.frame_logo if selected == "LOGO" else self.frame_poli
        panel.pack(fill="x", padx=2, pady=(11, 0), before=self.form_note)

    def _keyboard_shortcuts(self) -> None:
        self.bind_all("<Control-o>", lambda _e: self.seleccionar())
        self.bind_all("<Control-f>", lambda _e: self.search_entry.focus_set())
        self.bind_all("<Control-h>", lambda _e: self.abrir_historial())
        self.bind_all("<Control-MouseWheel>", self.hacer_zoom)
        self.bind_all("<Control-plus>", lambda _e: self.zoom_mas())
        self.bind_all("<Control-minus>", lambda _e: self.zoom_menos())

    def _draw_empty(self) -> None:
        if self.pdf.is_open:
            return
        self.canvas.delete("all")
        w, h = max(1, self.canvas.winfo_width()), max(1, self.canvas.winfo_height())
        if w < 90 or h < 90:
            return
        pad_x, pad_y = max(22, w * 0.085), max(24, h * 0.11)
        self.canvas.create_rectangle(
            pad_x, pad_y, w - pad_x, h - pad_y,
            outline="#B7CBE9", width=2, dash=(7, 6), fill="#F4F8FF", tags="empty",
        )
        self.canvas.create_text(w/2, h/2 - 52, text="▧", fill=BLUE, font=("Segoe UI", 43))
        self.canvas.create_text(w/2, h/2 - 3, text="ARRASTRA AQUÍ TU PDF", fill=NAVY, font=("Segoe UI", 16, "bold"))
        self.canvas.create_text(w/2, h/2 + 27, text="O haz clic en esta zona para abrir un documento", fill=MUTED, font=("Segoe UI", 12))
        self.canvas.create_text(w/2, h/2 + 52, text="También puedes utilizar + Abrir PDF o Ctrl+O", fill=MUTED, font=("Segoe UI", 10))
        self.canvas.configure(scrollregion=(0, 0, w, h), cursor="hand2")

    def _on_viewer_click(self, _event) -> None:
        if not self.pdf.is_open:
            self.seleccionar()

    def _drag_enter(self, _event):
        self.canvas.configure(bg="#DAE8FF")
        self._status("Suelta aquí un archivo PDF para abrirlo en el visor")
        return "copy"

    def _drag_leave(self, _event):
        self.canvas.configure(bg=CANVAS_BG)
        if self.pdf.is_open:
            self._status("Visor preparado · Arrastra otro PDF para abrirlo")
        else:
            self._status("Preparado · Arrastra un PDF al visor")
        return "copy"

    def _toggle_thumbnails(self) -> None:
        if not self.pdf.is_open or self.pdf.page_count <= 1:
            return
        self._thumbnails_visible = not self._thumbnails_visible
        if self._thumbnails_visible:
            self.thumb_ribbon.grid()
            self.btn_thumbs.configure(text="▦  Ocultar miniaturas")
            self._refresh_thumbnails()
        else:
            self.thumb_ribbon.grid_remove()
            self.btn_thumbs.configure(text="▦  Ver miniaturas")
            self._thumb_photos.clear()
        self._on_canvas_resized()

    def _update_thumbnail_control(self) -> None:
        if self.pdf.is_open and self.pdf.page_count > 1:
            self.btn_thumbs.grid()
        else:
            self._thumbnails_visible = False
            self.thumb_ribbon.grid_remove()
            self.btn_thumbs.grid_remove()
            self.btn_thumbs.configure(text="▦  Ver miniaturas")
            self._thumb_photos.clear()

    def seleccionar(self) -> None:
        path = filedialog.askopenfilename(title="Seleccionar PDF", filetypes=[("Archivos PDF", "*.pdf")])
        if path:
            self.cargar_nuevo_pdf(path)

    def al_soltar(self, event) -> None:
        self.canvas.configure(bg=CANVAS_BG)
        try:
            paths = self.tk.splitlist(event.data)
            pdf_paths = [p for p in paths if Path(p).suffix.lower() == ".pdf"]
            if len(pdf_paths) != 1:
                messagebox.showwarning("Archivo no válido", "Arrastra un único archivo PDF.")
                return
            self.cargar_nuevo_pdf(pdf_paths[0])
            return "copy"
        except Exception as exc:
            messagebox.showerror("No se pudo importar", str(exc))
            return "refuse_drop"

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
        filename = Path(filepath).name
        display_name = filename if len(filename) <= 39 else filename[:35] + "…" + Path(filepath).suffix
        self.path_label.configure(text=f"PDF · {display_name}")
        self.carpeta_generada = None
        self.archivo_firmado_path = None
        self._saved_context = None
        self.btn_abrir.configure(state="disabled")
        self.btn_firmado.configure(state="disabled")
        self.page_index = 0
        self.view_rotation = 0
        self.thumb_batch = 0
        self.fit_mode = "page"
        self._update_navigation()
        self._update_thumbnail_control()
        if self._thumbnails_visible:
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
            if self._thumbnails_visible:
                self._refresh_thumbnails()
        elif self._thumbnails_visible:
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
        self._thumb_items = []
        if not self.pdf.is_open or not self._thumbnails_visible:
            self.thumb_batch_label.configure(text="0 / 0")
            return
        begin = self.thumb_batch * THUMBS_PER_BATCH
        end = min(begin + THUMBS_PER_BATCH, self.pdf.page_count)
        total = (self.pdf.page_count + THUMBS_PER_BATCH - 1) // THUMBS_PER_BATCH
        self.thumb_batch_label.configure(text=f"{self.thumb_batch+1} / {total}")
        for index in range(begin, end):
            selected = index == self.page_index
            tile = ctk.CTkFrame(
                self.thumb_scroll, width=90, height=114, corner_radius=8, border_width=1,
                border_color=BLUE if selected else BORDER,
                fg_color=BLUE_PALE if selected else WHITE,
            )
            tile.pack(side="left", padx=4, pady=2)
            tile.pack_propagate(False)
            try:
                thumbnail = self.pdf.thumbnail(index, 64, 82)
                photo = ImageTk.PhotoImage(thumbnail, master=self)
                self._thumb_photos.append(photo)
                preview = tk.Label(tile, image=photo, borderwidth=0, bg=WHITE, cursor="hand2")
                preview.pack(padx=5, pady=(4, 0))
                preview.bind("<Button-1>", lambda _e, n=index: self._set_page(n))
            except PDFViewerError:
                self._label(tile, "Sin vista", size=9).pack(padx=4, pady=8)
            caption = self._label(tile, f"Pág. {index+1}", size=10, color=NAVY if selected else MUTED)
            caption.pack(pady=(1, 4))
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
            self.canvas.configure(cursor="arrow")
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

    def _get_history_store(self) -> HistoryStore:
        if self._history_store is None:
            self._history_store = HistoryStore()
        return self._history_store

    def _record_history(self, action: str, folder: Path, file: Path | None = None, *, kind: str | None = None) -> None:
        """Registrar solo operaciones concluidas. Un fallo del historial no revierte una copia válida."""
        try:
            self._get_history_store().add(kind or self.tipo.get(), action, folder, file)
        except Exception as exc:
            # El error se comunica una vez, pero nunca registra el documento ni la clave en logs.
            if not self._history_error_notified:
                self._history_error_notified = True
                messagebox.showwarning(
                    "Historial no disponible",
                    "La operación documental se ha realizado, pero no ha podido anotarse en el historial local. "
                    f"Revisa permisos y espacio disponible.\n\nDetalle técnico: {type(exc).__name__}",
                )

    def abrir_historial(self) -> None:
        try:
            if self._history_window is not None and self._history_window.winfo_exists():
                self._history_window.lift()
                self._history_window.focus_force()
                self._history_window.refresh()
            else:
                self._history_window = HistoryWindow(self, self._get_history_store(), BASE_ROOT)
                self._history_window.focus_force()
        except Exception as exc:
            messagebox.showerror("Historial", f"No se ha podido abrir el historial: {exc}")

    def _expediente_dir(self) -> Path:
        # Mismo formato en los tres circuitos y destinos: APELLIDOS, NOMBRE.
        return expediente_directory(
            self.tipo.get(), self.destino_var.get(), BASE_ROOT, Path.home(), datetime.now().year,
            self.ape.get(), self.nom.get(),
        )

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
        folder = self._expediente_dir()
        target = folder / original_filename(self.tipo.get(), self.cic.get())
        try:
            if not self._copy_with_confirmation(Path(self.pdf_path.get()), target):
                self._status("Guardado cancelado; el documento existente no se ha modificado")
                return
            self.carpeta_generada = folder
            self.archivo_firmado_path = None
            self._saved_context = self._current_context()
            self.btn_abrir.configure(state="normal")
            self.btn_firmado.configure(state="normal")
            self._record_history("Documento guardado", folder, target)
            self._status(f"Documento guardado correctamente · {target.name}")
            messagebox.showinfo("Documento guardado", f"El documento se ha guardado en:\n{target}")
        except OSError as exc:
            messagebox.showerror("Error al guardar", f"No se ha podido guardar el documento:\n{exc}\n\nComprueba la unidad T: y los permisos.")

    def abrir_carpeta(self) -> None:
        if self.carpeta_generada and self.carpeta_generada.is_dir():
            os.startfile(str(self.carpeta_generada))

    def _downloads(self) -> Path:
        return Path.home() / "Downloads"

    def _current_context(self) -> tuple[str, ...]:
        return (self.tipo.get(), self.cic.get().strip(), self.nom.get().strip(),
                self.ape.get().strip(), self.destino_var.get())

    def _folder_belongs_to_current_document(self) -> bool:
        if (self._saved_context is None or self._saved_context != self._current_context()
                or not self.carpeta_generada or not self.carpeta_generada.is_dir()):
            messagebox.showwarning("Expediente", "Los datos o el destino han cambiado. Guarda primero el documento para continuar.")
            return False
        return True

    def _found_files(self) -> list[Path]:
        # Búsqueda únicamente por nombre y CIC introducido manualmente.
        return find_matching_downloads(self._downloads(), self.tipo.get(), self.cic.get())

    def firmado_descargas(self) -> None:
        if not self._folder_belongs_to_current_document():
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
                self._record_history("Firmado incorporado", self.carpeta_generada, target)
                if get_route(self.tipo.get()).copies_to_day:
                    day_target = self._day_dir() / path.name
                    if not self._copy_with_confirmation(path, day_target):
                        continue
                    self._record_history("Firmado al día", day_target.parent, day_target)
                    self._invalidate_bihotz_archive()
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
            successes = 0
            for path in files:
                target = VOLANTES_ROOT / path.name
                if self._copy_with_confirmation(path, target):
                    successes += 1
                    self._record_history("Volante archivado", VOLANTES_ROOT, target)
            self._status(f"Volantes copiados: {successes}")
            messagebox.showinfo("Volantes", f"Se han guardado {successes} documento(s).")
        except OSError as exc:
            messagebox.showerror("Volantes", str(exc))

    def crear_carpeta_dia(self) -> None:
        try:
            path = self._day_dir()
            path.mkdir(parents=True, exist_ok=True)
            self._record_history("Carpeta diaria preparada", path, kind="BIHOTZ")
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

    def _invalidate_bihotz_archive(self) -> None:
        self._bihotz_ready_archive = None
        self._bihotz_snapshot = None
        self._bihotz_archive_stamp = None
        self.btn_enviar_bihotz.configure(state="disabled")

    def _compress(self, source: Path, archive: Path, service: str,
                  *, replace_archive: bool = False) -> bool:
        exe = self._find_7zip()
        if not exe:
            messagebox.showerror("7-Zip no disponible", "No se encuentra 7-Zip instalado en este equipo.")
            return False
        try:
            password = get_service_password(service)
        except ValueError as exc:
            messagebox.showerror("Servicio no reconocido", str(exc))
            return False
        if archive.exists() and not messagebox.askyesno(
            "El comprimido ya existe", f"¿Quieres reemplazar el archivo existente?\n{archive.name}",
        ):
            return False
        # Siempre construir un comprimido NUEVO (no añadir a uno anterior) y
        # sustituirlo solo si se verifican sus contenidos y su lista de archivos.
        temporary = archive.with_name(f".{archive.stem}-{uuid.uuid4().hex}.7z")
        try:
            result = subprocess.run(
                creation_command(exe, temporary, source, password),
                capture_output=True, text=True, timeout=180,
            )
            if result.returncode != 0:
                raise RuntimeError("La compresión no terminó correctamente. Comprueba archivo y unidad de destino.")
            archive_stamp(temporary)
            integrity = subprocess.run(
                test_command(exe, temporary, password),
                capture_output=True, text=True, timeout=180,
            )
            if integrity.returncode != 0:
                raise RuntimeError("7-Zip no ha podido verificar el archivo. Se conserva el anterior.")
            listing = subprocess.run(
                list_command(exe, temporary),
                capture_output=True, text=True, timeout=180,
            )
            if listing.returncode != 0:
                raise RuntimeError("La lista de archivos no es visible sin clave; se conserva el anterior.")
            os.replace(temporary, archive)
            self._status(f"Archivo comprimido: {archive.name}")
            messagebox.showinfo("Compresión completada", "Se ha creado el archivo cifrado:\n"
                                f"{archive}\n\nLa lista de documentos es visible sin clave."
                                "\nPara abrirlos o extraerlos se necesitará contraseña.")
            return True
        except (OSError, subprocess.TimeoutExpired, RuntimeError, ValueError) as exc:
            # No incorporar el proceso ni sus argumentos a mensajes: contienen la contraseña.
            messagebox.showerror("Compresión", str(exc))
            return False
        finally:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass

    def comprimir_dia(self) -> None:
        self._invalidate_bihotz_archive()
        path = self._day_dir()
        if not path.is_dir():
            messagebox.showwarning("Comprimir día", "Primero crea la carpeta del día.")
            return
        try:
            before = folder_snapshot(path)
        except (ValueError, OSError) as exc:
            messagebox.showwarning("Comprimir día", str(exc))
            return
        archive = path.with_suffix(".7z")
        if not self._compress(path, archive, "BIHOTZ", replace_archive=True):
            return
        self._record_history("Día comprimido", archive.parent, archive, kind="BIHOTZ")
        try:
            # Rechazar el envío si se añadieron archivos mientras se comprimía.
            after = folder_snapshot(path)
            if after != before:
                messagebox.showwarning("Día modificado", "La carpeta ha cambiado durante la compresión. Repite la operación antes de enviar.")
                return
            self._bihotz_snapshot = after
            self._bihotz_archive_stamp = archive_stamp(archive)
            self._bihotz_ready_archive = archive
            self.btn_enviar_bihotz.configure(state="normal")
            self._status("BIHOTZ del día comprimido · Ya puedes preparar el correo con ENVIAR")
        except (ValueError, OSError) as exc:
            messagebox.showerror("Comprimido no verificable", str(exc))

    def enviar_bihotz(self) -> None:
        if self.tipo.get() != "BIHOTZ":
            return
        archive = self._bihotz_ready_archive
        if archive is None or self._bihotz_snapshot is None or self._bihotz_archive_stamp is None:
            messagebox.showwarning("ENVIAR", "Primero comprime la carpeta del día de BIHOTZ.")
            return
        try:
            # Fecha comprobada al pulsar ENVIAR, no al abrir el programa.
            today = datetime.now().date()
            validate_daily_archive(
                self._day_dir(), archive, today,
                self._bihotz_snapshot, self._bihotz_archive_stamp,
            )
            if not messagebox.askyesno(
                "Preparar correo BIHOTZ",
                f"Se abrirá un borrador en Outlook clásico.\n\n"
                f"Para: {RECIPIENT}\n"
                f"Asunto: Volantes {today.strftime('%d-%m-%Y')}\n"
                f"Adjunto: {archive.name}\n\n"
                "Revisa el destinatario, el adjunto y la cuenta de envío antes de pulsar Enviar en Outlook.\n\n"
                "¿Deseas preparar este correo?",
            ):
                return
            prepare_outlook_draft(archive, today)
            # Un borrador preparado NO equivale a un correo enviado.
            self._record_history("Borrador preparado (no enviado)", archive.parent, archive, kind="BIHOTZ")
            self._status("Borrador BIHOTZ preparado en Outlook · Pendiente de enviar manualmente")
            messagebox.showinfo(
                "Correo preparado",
                "Se ha abierto el correo con el .7z adjunto en Outlook clásico.\n"
                "Compruébalo y pulsa Enviar desde Outlook.\n"
                "La aplicación no lo envía automáticamente.",
            )
        except (ValueError, OSError, RuntimeError) as exc:
            if isinstance(exc, ValueError):
                self._invalidate_bihotz_archive()
            messagebox.showerror("ENVIAR BIHOTZ", str(exc))

    def comprimir_logopedia(self) -> None:
        if not self._folder_belongs_to_current_document():
            return
        if not self.archivo_firmado_path or not self.archivo_firmado_path.is_file():
            messagebox.showwarning("Comprimir LOGOPEDIA", "Primero incorpora el archivo firmado desde Descargas.")
            return
        archive = self.archivo_firmado_path.with_suffix(".7z")
        if self._compress(self.archivo_firmado_path, archive, self.centro_logo_var.get()):
            self._record_history("Firmado comprimido", archive.parent, archive, kind="LOGO")

    def comprimir_policlinica(self) -> None:
        if not self._folder_belongs_to_current_document():
            return
        if not self.archivo_firmado_path or not self.archivo_firmado_path.is_file():
            messagebox.showwarning("Comprimir POLICLINICA", "Primero incorpora el archivo firmado desde Descargas.")
            return
        archive = self.archivo_firmado_path.with_suffix(".7z")
        if self._compress(
            self.archivo_firmado_path,
            archive,
            "POLICLINICA",
        ):
            self._record_history("Firmado comprimido", archive.parent, archive, kind="POLICLINICA")

    def _close(self) -> None:
        self._search_token += 1
        self.pdf.close()
        self.destroy()


def main() -> None:
    App().mainloop()


if __name__ == "__main__":
    main()
