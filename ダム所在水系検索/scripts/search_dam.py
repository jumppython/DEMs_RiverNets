from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

from common import normalize_name


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "db" / "dam_river.sqlite"


def search(db_path: Path, dam_name: str, limit: int = 20) -> list[sqlite3.Row]:
    q = normalize_name(dam_name)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """
            SELECT
                d.id AS dam_id,
                d.dam_name,
                rs.river_system_name,
                r.river_name,
                p.prefecture_name,
                d.lat,
                d.lon,
                COALESCE(MAX(m.confidence), 0.0) AS confidence,
                d.source_name,
                d.source_url
            FROM dams d
            LEFT JOIN river_systems rs ON d.river_system_id = rs.id
            LEFT JOIN rivers r ON d.river_id = r.id
            LEFT JOIN prefectures p ON d.prefecture_id = p.id
            LEFT JOIN dam_river_matches m ON d.id = m.dam_id
            WHERE d.dam_name_norm = ? OR d.dam_name_norm LIKE ?
            GROUP BY d.id
            ORDER BY CASE WHEN d.dam_name_norm = ? THEN 0 ELSE 1 END, confidence DESC, d.dam_name
            LIMIT ?
            """,
            (q, f"%{q}%", q, limit),
        ).fetchall()
        return rows
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Search dam relationship by dam name.")
    parser.add_argument("dam_name", help="ダム名。部分一致も可。")
    parser.add_argument("--db", default=str(DEFAULT_DB))
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()

    rows = search(Path(args.db), args.dam_name, args.limit)
    if not rows:
        print("No records found.")
        return
    for row in rows:
        print("-" * 60)
        print(f"dam_id: {row['dam_id']}")
        print(f"dam_name: {row['dam_name']}")
        print(f"river_system_name: {row['river_system_name'] or ''}")
        print(f"river_name: {row['river_name'] or ''}")
        print(f"prefecture_name: {row['prefecture_name'] or ''}")
        print(f"lat/lon: {row['lat'] or ''}, {row['lon'] or ''}")
        print(f"confidence: {row['confidence']:.2f}")
        print(f"source: {row['source_name'] or ''} {row['source_url'] or ''}")


if __name__ == "__main__":
    main()
