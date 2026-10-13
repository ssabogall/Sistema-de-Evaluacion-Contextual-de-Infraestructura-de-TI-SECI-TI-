"""Implementacion de CaseRepository sobre SQLite (libreria estandar, sin dependencias)."""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from pydantic import ValidationError

from app.decision_engine.engine import Recommendation
from app.persistence.models import CaseRecord, CaseSummary
from app.persistence.repository import CaseRepository, CaseStorageError
from app.schemas.business_case import ConfirmedBusinessCase

EXCERPT_LENGTH = 140

_SCHEMA = """
CREATE TABLE IF NOT EXISTS cases (
    id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    architecture TEXT NOT NULL,
    trade_off INTEGER NOT NULL,
    business_case TEXT NOT NULL,
    confirmed_json TEXT NOT NULL,
    recommendation_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_cases_created_at ON cases (created_at DESC);
"""


def _excerpt(text: str) -> str:
    text = " ".join(text.split())
    return text if len(text) <= EXCERPT_LENGTH else text[: EXCERPT_LENGTH - 1].rstrip() + "…"


class SqliteCaseRepository(CaseRepository):
    """Una conexion por operacion: es simple y segura con los hilos de FastAPI.

    El archivo y la tabla se crean la primera vez que se usa, no al construir el objeto,
    para que importar la aplicacion (o correr los tests) no deje archivos en disco.
    """

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            connection = sqlite3.connect(self._path)
        except (OSError, sqlite3.Error) as exc:
            raise CaseStorageError("No se pudo abrir la base de datos") from exc
        try:
            connection.row_factory = sqlite3.Row
            connection.executescript(_SCHEMA)
            yield connection
            connection.commit()
        except sqlite3.Error as exc:
            connection.rollback()
            raise CaseStorageError("Fallo una operacion en la base de datos") from exc
        finally:
            connection.close()

    def save(self, record: CaseRecord) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO cases (id, created_at, architecture, trade_off, business_case,"
                " confirmed_json, recommendation_json) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    record.id,
                    record.created_at.isoformat(),
                    str(record.recommendation.architecture),
                    int(record.recommendation.trade_off),
                    record.confirmed.business_case,
                    record.confirmed.model_dump_json(),
                    record.recommendation.model_dump_json(),
                ),
            )

    def get(self, case_id: str) -> CaseRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT id, created_at, confirmed_json, recommendation_json FROM cases"
                " WHERE id = ?",
                (case_id,),
            ).fetchone()
        if row is None:
            return None
        try:
            return CaseRecord(
                id=row["id"],
                created_at=row["created_at"],
                confirmed=ConfirmedBusinessCase.model_validate_json(row["confirmed_json"]),
                recommendation=Recommendation.model_validate_json(row["recommendation_json"]),
            )
        except ValidationError as exc:
            raise CaseStorageError("El caso guardado no coincide con el esquema actual") from exc

    def list_recent(self, limit: int = 50) -> list[CaseSummary]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT id, created_at, architecture, trade_off, business_case FROM cases"
                " ORDER BY created_at DESC, rowid DESC LIMIT ?",
                (limit,),
            ).fetchall()
        try:
            return [
                CaseSummary(
                    id=row["id"],
                    created_at=row["created_at"],
                    business_case_excerpt=_excerpt(row["business_case"]),
                    architecture=row["architecture"],
                    trade_off=bool(row["trade_off"]),
                )
                for row in rows
            ]
        except ValidationError as exc:
            raise CaseStorageError("Hay casos guardados que no coinciden con el esquema") from exc
