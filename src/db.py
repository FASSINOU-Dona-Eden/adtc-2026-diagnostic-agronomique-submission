"""SQLite storage for the mission history (specification §4.2).

Lightweight, local database, no network dependency. One row = one drone
mission on a plot, with its water stress ratio already computed (NDVI, cf.
§6.2 — nothing is recomputed here, a result is stored).
"""

import sqlite3
from contextlib import contextmanager

from src.config import DB_PATH
from src.models import MissionReading, ParcelleHistorique

SCHEMA = """
CREATE TABLE IF NOT EXISTS missions (
    mission_id      TEXT PRIMARY KEY,
    parcelle_id     TEXT NOT NULL,
    date            TEXT NOT NULL,
    culture         TEXT NOT NULL,
    stress_ratio    REAL NOT NULL,
    zones_stressees INTEGER NOT NULL,
    zones_totales   INTEGER NOT NULL,
    notes           TEXT DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_missions_parcelle ON missions(parcelle_id, date);
"""


@contextmanager
def get_conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with get_conn() as conn:
        conn.executescript(SCHEMA)


def insert_mission(reading: MissionReading) -> None:
    with get_conn() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO missions
               (mission_id, parcelle_id, date, culture, stress_ratio,
                zones_stressees, zones_totales, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                reading.mission_id,
                reading.parcelle_id,
                reading.date.isoformat(),
                reading.culture,
                reading.stress_ratio,
                reading.zones_stressees,
                reading.zones_totales,
                reading.notes,
            ),
        )


def get_historique(parcelle_id: str) -> ParcelleHistorique:
    from datetime import date as date_cls

    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM missions WHERE parcelle_id = ? ORDER BY date ASC",
            (parcelle_id,),
        ).fetchall()

    missions = [
        MissionReading(
            mission_id=r["mission_id"],
            parcelle_id=r["parcelle_id"],
            date=date_cls.fromisoformat(r["date"]),
            culture=r["culture"],
            stress_ratio=r["stress_ratio"],
            zones_stressees=r["zones_stressees"],
            zones_totales=r["zones_totales"],
            notes=r["notes"],
        )
        for r in rows
    ]
    return ParcelleHistorique(parcelle_id=parcelle_id, missions=missions)
