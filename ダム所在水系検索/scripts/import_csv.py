from __future__ import annotations

import argparse
import csv
import json
import sqlite3
from pathlib import Path

from common import normalize_name, normalize_prefecture, normalize_text
from init_db import init_db


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "db" / "dam_river.sqlite"


def to_float(value):
    if value in (None, ""):
        return None
    try:
        return float(str(value).strip())
    except ValueError:
        return None


def pref_id(conn: sqlite3.Connection, pref_name: str | None) -> int | None:
    pref = normalize_prefecture(pref_name)
    if not pref:
        return None
    row = conn.execute("SELECT id FROM prefectures WHERE prefecture_name=?", (pref,)).fetchone()
    return int(row[0]) if row else None


def get_or_create_system(conn, name, source_name, source_url):
    name = normalize_text(name)
    if not name:
        return None
    conn.execute(
        "INSERT OR IGNORE INTO river_systems(river_system_name, river_system_name_norm, source_name, source_url) VALUES (?, ?, ?, ?)",
        (name, normalize_text(name), source_name, source_url),
    )
    row = conn.execute("SELECT id FROM river_systems WHERE river_system_name_norm=?", (normalize_text(name),)).fetchone()
    return int(row[0]) if row else None


def get_or_create_river(conn, name, system_id, prefecture_id, source_name, source_url):
    name = normalize_text(name)
    if not name:
        return None
    conn.execute(
        """
        INSERT OR IGNORE INTO rivers(river_name, river_name_norm, river_system_id, prefecture_id, source_name, source_url)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (name, normalize_text(name), system_id, prefecture_id, source_name, source_url),
    )
    row = conn.execute(
        """
        SELECT id FROM rivers
        WHERE river_name_norm=? AND IFNULL(river_system_id,-1)=IFNULL(?,-1) AND IFNULL(prefecture_id,-1)=IFNULL(?,-1)
        """,
        (normalize_text(name), system_id, prefecture_id),
    ).fetchone()
    return int(row[0]) if row else None


def import_csv(csv_path: Path, db_path: Path, source_name: str, source_url: str | None) -> int:
    init_db(db_path)
    count = 0
    with sqlite3.connect(db_path) as conn, csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        conn.execute("PRAGMA foreign_keys = ON")
        reader = csv.DictReader(f)
        for rec in reader:
            dam_name = rec.get("dam_name") or rec.get("ダム名")
            if not dam_name:
                continue
            pid = pref_id(conn, rec.get("prefecture") or rec.get("都道府県"))
            sid = get_or_create_system(conn, rec.get("river_system_name") or rec.get("水系名"), source_name, source_url)
            rid = get_or_create_river(conn, rec.get("river_name") or rec.get("河川名"), sid, pid, source_name, source_url)
            conn.execute(
                """
                INSERT OR IGNORE INTO dams(dam_name, dam_name_norm, river_id, river_system_id, prefecture_id, lat, lon, source_name, source_url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    normalize_text(dam_name),
                    normalize_name(dam_name),
                    rid,
                    sid,
                    pid,
                    to_float(rec.get("lat") or rec.get("緯度")),
                    to_float(rec.get("lon") or rec.get("経度")),
                    source_name,
                    source_url,
                ),
            )
            row = conn.execute("SELECT id FROM dams WHERE dam_name_norm=? ORDER BY id LIMIT 1", (normalize_name(dam_name),)).fetchone()
            dam_id = int(row[0]) if row else None
            conn.execute(
                """
                INSERT INTO dam_source_records(dam_id, source_name, source_url, raw_dam_name, raw_river_name, raw_system_name, raw_prefecture, raw_lat, raw_lon, raw_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    dam_id,
                    source_name,
                    source_url,
                    dam_name,
                    rec.get("river_name") or rec.get("河川名"),
                    rec.get("river_system_name") or rec.get("水系名"),
                    rec.get("prefecture") or rec.get("都道府県"),
                    rec.get("lat") or rec.get("緯度"),
                    rec.get("lon") or rec.get("経度"),
                    json.dumps(rec, ensure_ascii=False),
                ),
            )
            if dam_id and (rid or sid):
                conn.execute(
                    "INSERT INTO dam_river_matches(dam_id, river_id, river_system_id, match_method, confidence, note) VALUES (?, ?, ?, 'csv_direct', 0.95, ?)",
                    (dam_id, rid, sid, source_name),
                )
            count += 1
        conn.commit()
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description="Import dam-river records from CSV.")
    parser.add_argument("csv_path")
    parser.add_argument("--db", default=str(DEFAULT_DB))
    parser.add_argument("--source-name", default="manual_csv")
    parser.add_argument("--source-url", default=None)
    args = parser.parse_args()
    count = import_csv(Path(args.csv_path), Path(args.db), args.source_name, args.source_url)
    print(f"Imported CSV records: {count}")


if __name__ == "__main__":
    main()
