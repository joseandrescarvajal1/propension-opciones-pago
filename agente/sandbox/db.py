"""Base de datos del sandbox (SQLite).

Simula los sistemas del banco que consulta el agente: clientes, obligaciones (con las 100
variables del modelo), opciones de pago preaprobadas y aplicadas, acuerdos, restricciones,
códigos OTP, mensajes del canal (WhatsApp simulado) y trazas de cada decisión.

Todos los datos son simulados: los identificadores están enmascarados y los nombres, cédulas y
teléfonos son ficticios. Ver crear_sandbox.py.
"""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
# Fecha "de hoy" del sandbox: enero de 2024, el mes fuera de tiempo del modelo
HOY = os.environ.get("SANDBOX_HOY", "2024-01-15")

ESQUEMA = """
CREATE TABLE IF NOT EXISTS clientes (
    cedula TEXT PRIMARY KEY,
    nit_enmascarado INTEGER NOT NULL,
    nombre TEXT NOT NULL,
    telefono TEXT NOT NULL,
    fecha_nacimiento TEXT NOT NULL,
    segmento TEXT,
    escenario TEXT NOT NULL,
    descripcion_escenario TEXT
);
CREATE TABLE IF NOT EXISTS obligaciones (
    id_obligacion TEXT PRIMARY KEY,
    cedula TEXT NOT NULL REFERENCES clientes(cedula),
    producto TEXT NOT NULL,
    saldo_capital REAL NOT NULL,
    valor_cuota REAL NOT NULL,
    valor_vencido REAL NOT NULL,
    dias_mora INTEGER NOT NULL,
    etapa_mora TEXT NOT NULL,
    variables_modelo TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS opciones_preaprobadas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_obligacion TEXT NOT NULL REFERENCES obligaciones(id_obligacion),
    codigo TEXT NOT NULL,
    nombre TEXT NOT NULL,
    descripcion TEXT NOT NULL,
    cuota_nueva REAL,
    plazo_meses INTEGER,
    meses_espera INTEGER NOT NULL,
    vigente_hasta TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS opciones_aplicadas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_obligacion TEXT NOT NULL REFERENCES obligaciones(id_obligacion),
    codigo TEXT NOT NULL,
    nombre TEXT NOT NULL,
    fecha_aplicacion TEXT NOT NULL,
    meses_espera INTEGER NOT NULL,
    canal TEXT NOT NULL DEFAULT 'historico',
    thread_id TEXT
);
CREATE TABLE IF NOT EXISTS acuerdos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_obligacion TEXT NOT NULL REFERENCES obligaciones(id_obligacion),
    fecha_acuerdo TEXT NOT NULL,
    fecha_compromiso TEXT NOT NULL,
    valor REAL NOT NULL,
    estado TEXT NOT NULL,           -- vigente | cumplido | incumplido
    canal TEXT NOT NULL DEFAULT 'historico',
    thread_id TEXT
);
CREATE TABLE IF NOT EXISTS restricciones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cedula TEXT NOT NULL REFERENCES clientes(cedula),
    tipo TEXT NOT NULL,             -- juridica | fraude | fallecido | reclamacion | no_contactar
    detalle TEXT,
    activa INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS otp (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cedula TEXT NOT NULL,
    thread_id TEXT NOT NULL,
    codigo_hash TEXT NOT NULL,
    creado TEXT NOT NULL,
    vence TEXT NOT NULL,
    intentos INTEGER NOT NULL DEFAULT 0,
    usado INTEGER NOT NULL DEFAULT 0,
    bloqueado INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS mensajes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    thread_id TEXT NOT NULL,
    telefono TEXT NOT NULL,
    canal TEXT NOT NULL,            -- whatsapp | sms
    direccion TEXT NOT NULL,        -- entrante (cliente -> banco) | saliente (banco -> cliente)
    tipo TEXT NOT NULL,             -- texto | plantilla | otp
    plantilla TEXT,
    texto TEXT NOT NULL,
    creado TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS trazas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    thread_id TEXT NOT NULL,
    turno INTEGER NOT NULL,
    nodo TEXT NOT NULL,
    evento TEXT NOT NULL,
    detalle TEXT,
    latencia_ms REAL,
    tokens_entrada INTEGER,
    tokens_salida INTEGER,
    creado TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS escalamientos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    thread_id TEXT NOT NULL,
    cedula TEXT,
    motivo TEXT NOT NULL,
    resumen TEXT NOT NULL,
    prioridad TEXT NOT NULL,
    creado TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_mensajes_thread ON mensajes(thread_id, id);
CREATE INDEX IF NOT EXISTS ix_trazas_thread ON trazas(thread_id, id);
"""


def ahora() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def ruta_db(ruta: str | Path | None = None) -> Path:
    r = Path(ruta or os.environ.get("SANDBOX_DB") or "agente/sandbox/sandbox.db")
    return r if r.is_absolute() else ROOT / r


def conectar(ruta: str | Path | None = None) -> sqlite3.Connection:
    con = sqlite3.connect(str(ruta_db(ruta)), check_same_thread=False, timeout=30)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA foreign_keys=ON")
    return con


def crear_esquema(con: sqlite3.Connection) -> None:
    con.executescript(ESQUEMA)
    con.commit()


def filas(con: sqlite3.Connection, sql: str, params: tuple | dict = ()) -> list[dict[str, Any]]:
    return [dict(r) for r in con.execute(sql, params).fetchall()]


def fila(con: sqlite3.Connection, sql: str, params: tuple | dict = ()) -> dict[str, Any] | None:
    r = con.execute(sql, params).fetchone()
    return dict(r) if r else None


def insertar(con: sqlite3.Connection, tabla: str, datos: dict[str, Any]) -> int:
    cols = ", ".join(datos)
    marcas = ", ".join("?" for _ in datos)
    cur = con.execute(f"INSERT INTO {tabla} ({cols}) VALUES ({marcas})", tuple(json.dumps(v) if isinstance(v, (dict, list)) else v for v in datos.values()))
    con.commit()
    return int(cur.lastrowid)


def registrar_traza(con: sqlite3.Connection, thread_id: str, turno: int, nodo: str, evento: str, detalle: Any = None,
                    latencia_ms: float | None = None, tokens_entrada: int | None = None, tokens_salida: int | None = None) -> int:
    return insertar(con, "trazas", {"thread_id": thread_id, "turno": turno, "nodo": nodo, "evento": evento,
                                    "detalle": json.dumps(detalle, ensure_ascii=False, default=str) if not isinstance(detalle, str) and detalle is not None else detalle,
                                    "latencia_ms": latencia_ms, "tokens_entrada": tokens_entrada, "tokens_salida": tokens_salida, "creado": ahora()})
