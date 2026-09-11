"""Contexto de ejecución compartido por las herramientas: conexión a la base y hilo actual.

El grafo fija el hilo (thread_id) y el turno antes de invocar al agente; las herramientas lo leen
de aquí para registrar trazas y mensajes sin que el LLM tenga que pasarlo como argumento (así el
modelo no puede actuar sobre otro hilo).
"""

from __future__ import annotations

import sqlite3
from contextvars import ContextVar

from sandbox.db import conectar

_thread_id: ContextVar[str] = ContextVar("thread_id", default="sin_hilo")
_turno: ContextVar[int] = ContextVar("turno", default=0)
_con: ContextVar[sqlite3.Connection | None] = ContextVar("con", default=None)


def fijar(thread_id: str, turno: int = 0, con: sqlite3.Connection | None = None) -> None:
    _thread_id.set(thread_id)
    _turno.set(turno)
    if con is not None:
        _con.set(con)


def thread_id() -> str:
    return _thread_id.get()


def turno() -> int:
    return _turno.get()


def con() -> sqlite3.Connection:
    c = _con.get()
    if c is None:
        c = conectar()
        _con.set(c)
    return c
