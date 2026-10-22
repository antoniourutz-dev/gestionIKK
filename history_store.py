"""Historial local de operaciones documentales.

Solo guarda referencias (rutas) y metadatos de operaciones; nunca copias de
PDF, contraseñas, contenido de documentos ni texto extraído. SQLite queda
separado del ejecutable, por usuario de Windows, en LOCALAPPDATA.
"""
from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

ALLOWED_KINDS = frozenset({"BIHOTZ", "LOGO", "POLICLINICA"})


@dataclass(frozen=True)
class HistoryRecord:
    id: int
    timestamp: str
    kind: str
    action: str
    folder: Path
    file: Path | None


def database_location() -> Path:
    """No crear la base de datos en el ZIP, junto al EXE ni en una ruta pública."""
    root = os.environ.get("LOCALAPPDATA")
    if root:
        return Path(root) / "GestorPDF" / "historial.sqlite3"
    # Alternativa para ejecución de pruebas/desarrollo fuera de Windows.
    return Path(os.environ.get("XDG_STATE_HOME", str(Path.home() / ".local" / "state"))) / "GestorPDF" / "historial.sqlite3"


class HistoryStore:
    def __init__(self, path: Path | None = None):
        self.path = Path(path) if path else database_location()
        self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        # ACL del perfil Windows: se hereda del directorio de usuario. Unix: solo propietario.
        if os.name != "nt":
            try:
                os.chmod(self.path.parent, 0o700)
            except OSError:
                pass
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS actions (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  timestamp TEXT NOT NULL,
                  kind TEXT NOT NULL,
                  action TEXT NOT NULL,
                  folder TEXT NOT NULL,
                  file TEXT
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_actions_time ON actions(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_actions_kind_time ON actions(kind, timestamp)")
        if os.name != "nt":
            try:
                os.chmod(self.path, 0o600)
            except OSError:
                pass

    @contextmanager
    def _connect(self):
        # Cerrar explícitamente las conexiones para no retener el archivo SQLite.
        conn = sqlite3.connect(self.path, timeout=5)
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def add(self, kind: str, action: str, folder: Path, file: Path | None = None,
            *, when: datetime | None = None) -> int:
        if kind not in ALLOWED_KINDS:
            raise ValueError("Tipo documental no válido")
        if not action.strip() or not str(folder).strip():
            raise ValueError("La operación y la carpeta son obligatorias")
        stamp = (when or datetime.now()).isoformat(timespec="seconds")
        with self._connect() as conn:
            cursor = conn.execute(
                "INSERT INTO actions(timestamp, kind, action, folder, file) VALUES (?, ?, ?, ?, ?)",
                (stamp, kind, action.strip(), str(folder), str(file) if file is not None else None),
            )
            return int(cursor.lastrowid)

    def list(self, on_date: date | None, kind: str | None = None, *, limit: int = 2000) -> list[HistoryRecord]:
        if kind is not None and kind not in ALLOWED_KINDS:
            raise ValueError("Tipo documental no válido")
        if not 1 <= limit <= 10000:
            raise ValueError("Límite no válido")
        conditions = []
        values: list[str | int] = []
        if on_date is not None:
            # Prefijo ISO que puede usar el índice y no depende del formato regional.
            conditions.append("timestamp >= ? AND timestamp < ?")
            start = on_date.isoformat()
            from datetime import timedelta
            end = (on_date + timedelta(days=1)).isoformat()
            values.extend([start, end])
        if kind is not None:
            conditions.append("kind = ?")
            values.append(kind)
        sql = "SELECT id, timestamp, kind, action, folder, file FROM actions"
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += " ORDER BY timestamp DESC, id DESC LIMIT ?"
        values.append(limit)
        with self._connect() as conn:
            rows = conn.execute(sql, values).fetchall()
        return [HistoryRecord(int(row[0]), row[1], row[2], row[3], Path(row[4]), Path(row[5]) if row[5] else None) for row in rows]


def bihotz_day_directory(root: Path, on_date: date) -> Path:
    """Permite consultar una carpeta histórica existente sin crearla ni mover nada."""
    return root / str(on_date.year) / "BIHOTZ POR DIAS" / f"BIHOTZ {on_date.strftime('%d-%m-%Y')}"


def folder_documents(folder: Path) -> list[Path]:
    """Solo archivos de la carpeta elegida, sin búsquedas recursivas ni abrir ejecutables."""
    if not folder.is_dir():
        return []
    return sorted((p for p in folder.iterdir() if p.is_file() and p.suffix.casefold() in (".pdf", ".7z")),
                  key=lambda p: p.name.casefold())
