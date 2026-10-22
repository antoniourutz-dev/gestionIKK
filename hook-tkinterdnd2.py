"""Incluye los binarios TkDnD al empaquetar la aplicación en Windows."""
from PyInstaller.utils.hooks import collect_data_files

datas = collect_data_files("tkinterdnd2")
