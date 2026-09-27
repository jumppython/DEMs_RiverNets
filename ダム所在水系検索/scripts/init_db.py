from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

from common import PREFECTURES


SCHEMA = r"""
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS prefectures (
    id INTEGER PRIMARY KEY,
    prefecture_name TEXT NOT NULL UNIQUE,
    prefecture_code TEXT NOT NULL UNIQUE,
    region_name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS river_systems (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    river_system_name TEXT NOT NULL,
    river_system_name_norm TEXT NOT NULL,
    river_system_kana TEXT,
    class_type TEXT,
    source_name TEXT,
    source_url TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(river_system_name_norm, class_type)
);

CREATE TABLE IF NOT EXISTS rivers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    river_name TEXT NOT NULL,
    river_name_norm TEXT NOT NULL,
    river_kana TEXT,
    river_system_id INTEGER,
    prefecture_id INTEGER,
    river_rank TEXT,
    source_name TEXT,
    source_url TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(river_system_id) REFERENCES river_systems(id),
    FOREIGN KEY(prefecture_id) REFERENCES prefectures(id),
    UNIQUE(river_name_norm, river_system_id, prefecture_id)
);

CREATE TABLE IF NOT EXISTS dams (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dam_name TEXT NOT NULL,
    dam_name_norm TEXT NOT NULL,
    dam_kana TEXT,
    river_id INTEGER,
    river_system_id INTEGER,
    prefecture_id INTEGER,
    lat REAL,
    lon REAL,
    address TEXT,
    operator_name TEXT,
    dam_type TEXT,
    purpose TEXT,
    source_name TEXT,
    source_url TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(river_id) REFERENCES rivers(id),
    FOREIGN KEY(river_system_id) REFERENCES river_systems(id),
    FOREIGN KEY(prefecture_id) REFERENCES prefectures(id)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_dams_unique_basic
ON dams(dam_name_norm, IFNULL(prefecture_id, -1), IFNULL(river_id, -1));

CREATE TABLE IF NOT EXISTS dam_source_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dam_id INTEGER,
    source_name TEXT NOT NULL,
    source_url TEXT,
    raw_dam_name TEXT,
    raw_river_name TEXT,
    raw_system_name TEXT,
    raw_prefecture TEXT,
    raw_lat TEXT,
    raw_lon TEXT,
    raw_data TEXT,
    collected_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(dam_id) REFERENCES dams(id)
);

CREATE TABLE IF NOT EXISTS dam_river_matches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dam_id INTEGER NOT NULL,
    river_id INTEGER,
    river_system_id INTEGER,
    match_method TEXT NOT NULL,
    confidence REAL NOT NULL DEFAULT 0.0,
    note TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(dam_id) REFERENCES dams(id),
    FOREIGN KEY(river_id) REFERENCES rivers(id),
    FOREIGN KEY(river_system_id) REFERENCES river_systems(id)
);

CREATE INDEX IF NOT EXISTS idx_dams_name_norm ON dams(dam_name_norm);
CREATE INDEX IF NOT EXISTS idx_rivers_name_norm ON rivers(river_name_norm);
CREATE INDEX IF NOT EXISTS idx_systems_name_norm ON river_systems(river_system_name_norm);
"""


def init_db(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.executescript(SCHEMA)
        conn.executemany(
            """
            INSERT INTO prefectures(id, prefecture_name, prefecture_code, region_name)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                prefecture_name=excluded.prefecture_name,
                prefecture_code=excluded.prefecture_code,
                region_name=excluded.region_name
            """,
            PREFECTURES,
        )
        conn.commit()


def main() -> None:
    parser = argparse.ArgumentParser(description="Initialize dam-river SQLite database.")
    parser.add_argument("--db", default=str(Path(__file__).resolve().parents[1] / "db" / "dam_river.sqlite"))
    args = parser.parse_args()
    init_db(Path(args.db))
    print(f"Initialized DB: {args.db}")


if __name__ == "__main__":
    main()
