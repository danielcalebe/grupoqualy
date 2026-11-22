"""Camada de acesso a dados SQLite — Sistema de Logística Grupo Qualy."""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Iterable, Optional

from config import DATABASE_PATH, DATA_DIR

SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


def _connect(db_path: Optional[Path] = None) -> sqlite3.Connection:
    path = Path(db_path) if db_path else DATABASE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


class Database:
    """Abre conexões sob demanda; aceita caminho customizado para testes."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = Path(db_path) if db_path else DATABASE_PATH

    def connect(self) -> sqlite3.Connection:
        return _connect(self.db_path)

    def init_db(self) -> None:
        """Cria tabelas a partir do schema.sql (idempotente)."""
        sql = SCHEMA_PATH.read_text(encoding="utf-8")
        conn = self.connect()
        try:
            conn.executescript(sql)
            conn.commit()
        finally:
            conn.close()

    def query(self, sql: str, params: Iterable[Any] = ()) -> list[dict[str, Any]]:
        conn = self.connect()
        try:
            cur = conn.execute(sql, tuple(params))
            rows = [dict(r) for r in cur.fetchall()]
            return rows
        finally:
            conn.close()

    def query_one(self, sql: str, params: Iterable[Any] = ()) -> Optional[dict[str, Any]]:
        rows = self.query(sql, params)
        return rows[0] if rows else None

    def execute(self, sql: str, params: Iterable[Any] = ()) -> int:
        """Executa INSERT/UPDATE/DELETE; retorna lastrowid (ou rowcount)."""
        conn = self.connect()
        try:
            cur = conn.execute(sql, tuple(params))
            conn.commit()
            return cur.lastrowid if cur.rowcount == -1 else cur.lastrowid
        finally:
            conn.close()

    def execute_many(self, sql: str, seq: list[tuple]) -> None:
        conn = self.connect()
        try:
            conn.executemany(sql, seq)
            conn.commit()
        finally:
            conn.close()


# Instância padrão da aplicação
db = Database()


def get_db() -> Database:
    return db
