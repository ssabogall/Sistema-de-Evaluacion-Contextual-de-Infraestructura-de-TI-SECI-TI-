"""Interfaz de almacenamiento de casos.

El resto del sistema solo conoce `CaseRepository`. Hoy lo implementa SQLite
(sqlite_repository.py); si el almacenamiento pasa a un servicio de AWS (DynamoDB, RDS...)
solo hay que escribir otra implementacion de esta interfaz y cambiarla en create_app.
"""

from abc import ABC, abstractmethod

from app.persistence.models import CaseRecord, CaseSummary


class CaseStorageError(Exception):
    """No se pudo guardar o leer un caso (error del almacenamiento o registro ilegible)."""


class CaseRepository(ABC):
    @abstractmethod
    def save(self, record: CaseRecord) -> None:
        """Guarda un caso nuevo. Lanza CaseStorageError si falla o el id ya existe."""

    @abstractmethod
    def get(self, case_id: str) -> CaseRecord | None:
        """Devuelve el caso, o None si no existe."""

    @abstractmethod
    def list_recent(self, limit: int = 50) -> list[CaseSummary]:
        """Los casos mas recientes primero."""
