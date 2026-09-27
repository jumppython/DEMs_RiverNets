from __future__ import annotations

import argparse
import csv
import html
import json
import re
import sqlite3
import ssl
import time
import urllib.request
from pathlib import Path

from common import normalize_name, normalize_prefecture, normalize_text
from init_db import init_db


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "db" / "dam_river.sqlite"
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"

SOURCES = {
    "mlit_river_system": "https://www.mlit.go.jp/mizukokudo/mizsei/mizukokudo_mizsei_tk2_000024.html",
    "mudam_search": "https://mudam.nilim.go.jp/search",
}

RIVER_SITE_URL = (
    "https://www1.river.go.jp/cgi-bin/SrchSite.exe?"
    "KOMOKU=05&NAME=&SUIKEI=-00001&KASEN=&KEN=-1&CITY=&PAGE={page}"
)


def fetch_url(url: str, out_path: Path, delay_sec: float = 0.5) -> str:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 dam-river-db/0.1"})
    try:
        with urllib.request.urlopen(req, timeout=60) as res:
            data = res.read()
    except Exception as e:
        if url.lower().startswith("https://") and "CERTIFICATE_VERIFY_FAILED" in str(e):
            print(f"Warning: SSL certificate verification failed. Retrying without verification: {url}")
            context = ssl._create_unverified_context()
            with urllib.request.urlopen(req, timeout=60, context=context) as res:
                data = res.read()
        else:
            raise
    text = decode_japanese_html(data)
    out_path.write_text(text, encoding="utf-8")
    time.sleep(delay_sec)
    return text


def decode_japanese_html(data: bytes) -> str:
    candidates = ["utf-8", "cp932", "shift_jis", "euc_jp", "iso2022_jp"]
    best_text = ""
    best_score = -10**9
    for enc in candidates:
        try:
            text = data.decode(enc, errors="replace")
        except LookupError:
            continue
        score = 0
        for token in ("水系", "河川", "ダム", "観測", "都道府県", "検索", "水文"):
            score += text.count(token) * 20
        score -= text.count("�") * 50
        score -= text.count("ｴ") * 2
        if score > best_score:
            best_score = score
            best_text = text
    return best_text


def strip_tags(value: str) -> str:
    value = re.sub(r"<br\s*/?>", " ", value, flags=re.I)
    value = re.sub(r"<[^>]+>", "", value)
    return html.unescape(value).strip()


def parse_html_tables(text: str) -> list[list[list[str]]]:
    tables: list[list[list[str]]] = []
    for table_html in re.findall(r"<table\b.*?</table>", text, flags=re.I | re.S):
        rows: list[list[str]] = []
        for row_html in re.findall(r"<tr\b.*?</tr>", table_html, flags=re.I | re.S):
            cells = re.findall(r"<t[dh]\b.*?</t[dh]>", row_html, flags=re.I | re.S)
            row = [strip_tags(cell) for cell in cells]
            if any(row):
                rows.append(row)
        if rows:
            tables.append(rows)
    return tables


def pref_id(conn: sqlite3.Connection, pref: str | None) -> int | None:
    pref = normalize_prefecture(pref)
    if not pref:
        return None
    row = conn.execute("SELECT id FROM prefectures WHERE prefecture_name=?", (pref,)).fetchone()
    return int(row[0]) if row else None


def get_or_create_system(conn: sqlite3.Connection, name: str | None, source_name: str, source_url: str) -> int | None:
    if not name:
        return None
    name = normalize_text(name)
    if not name:
        return None
    norm = normalize_text(name)
    conn.execute(
        """
        INSERT OR IGNORE INTO river_systems(river_system_name, river_system_name_norm, source_name, source_url)
        VALUES (?, ?, ?, ?)
        """,
        (name, norm, source_name, source_url),
    )
    row = conn.execute("SELECT id FROM river_systems WHERE river_system_name_norm=?", (norm,)).fetchone()
    return int(row[0]) if row else None


def get_or_create_river(conn: sqlite3.Connection, name: str | None, system_id: int | None, prefecture_id: int | None, source_name: str, source_url: str) -> int | None:
    if not name:
        return None
    name = normalize_text(name)
    if not name:
        return None
    norm = normalize_text(name)
    conn.execute(
        """
        INSERT OR IGNORE INTO rivers(river_name, river_name_norm, river_system_id, prefecture_id, source_name, source_url)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (name, norm, system_id, prefecture_id, source_name, source_url),
    )
    row = conn.execute(
        """
        SELECT id FROM rivers
        WHERE river_name_norm=? AND IFNULL(river_system_id,-1)=IFNULL(?,-1) AND IFNULL(prefecture_id,-1)=IFNULL(?,-1)
        """,
        (norm, system_id, prefecture_id),
    ).fetchone()
    return int(row[0]) if row else None


def create_dam_record(conn: sqlite3.Connection, rec: dict, source_name: str, source_url: str) -> int | None:
    dam_name = rec.get("dam_name") or rec.get("ダム名") or rec.get("施設名") or rec.get("観測所名")
    if not dam_name or "ダム" not in dam_name:
        return None
    system_name = rec.get("river_system_name") or rec.get("水系名") or rec.get("水系")
    river_name = rec.get("river_name") or rec.get("河川名") or rec.get("河川")
    pref_name = rec.get("prefecture") or rec.get("都道府県") or rec.get("県名")
    lat = rec.get("lat") or rec.get("緯度")
    lon = rec.get("lon") or rec.get("経度")

    pid = pref_id(conn, pref_name)
    sid = get_or_create_system(conn, system_name, source_name, source_url)
    rid = get_or_create_river(conn, river_name, sid, pid, source_name, source_url)
    norm = normalize_name(dam_name)
    conn.execute(
        """
        INSERT OR IGNORE INTO dams(dam_name, dam_name_norm, river_id, river_system_id, prefecture_id, lat, lon, source_name, source_url)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (normalize_text(dam_name), norm, rid, sid, pid, to_float(lat), to_float(lon), source_name, source_url),
    )
    row = conn.execute(
        "SELECT id FROM dams WHERE dam_name_norm=? ORDER BY id LIMIT 1", (norm,)
    ).fetchone()
    dam_id = int(row[0]) if row else None
    conn.execute(
        """
        INSERT INTO dam_source_records(dam_id, source_name, source_url, raw_dam_name, raw_river_name, raw_system_name, raw_prefecture, raw_lat, raw_lon, raw_data)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (dam_id, source_name, source_url, dam_name, river_name, system_name, pref_name, lat, lon, json.dumps(rec, ensure_ascii=False)),
    )
    if dam_id and (rid or sid):
        conn.execute(
            """
            INSERT INTO dam_river_matches(dam_id, river_id, river_system_id, match_method, confidence, note)
            VALUES (?, ?, ?, 'source_direct', 0.95, ?)
            """,
            (dam_id, rid, sid, source_name),
        )
    return dam_id


def to_float(value):
    if value in (None, ""):
        return None
    m = re.search(r"-?\d+(?:\.\d+)?", str(value))
    return float(m.group(0)) if m else None


def save_table_csv(tables: list[list[list[str]]], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        for i, table in enumerate(tables, start=1):
            writer.writerow([f"# table {i}"])
            writer.writerows(table)
            writer.writerow([])


def import_river_site_pages(conn: sqlite3.Connection) -> int:
    total_records = 0
    for page in range(1, 13):
        url = RIVER_SITE_URL.format(page=page)
        text = fetch_url(url, RAW_DIR / f"river_site_page_{page:02d}.html")
        tables = parse_html_tables(text)
        save_table_csv(tables, PROCESSED_DIR / f"river_site_page_{page:02d}_tables.csv")
        # Conservative generic parser: use header names if a table exposes recognizable columns.
        for table in tables:
            if len(table) < 2:
                continue
            header = [normalize_text(x) for x in table[0]]
            for row in table[1:]:
                if len(row) != len(header):
                    continue
                rec = dict(zip(header, row))
                dam_id = create_dam_record(conn, rec, "水文水質DB", url)
                if dam_id:
                    total_records += 1
    conn.commit()
    return total_records


def fetch_reference_pages() -> None:
    for name, url in SOURCES.items():
        fetch_url(url, RAW_DIR / f"{name}.html")


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch and import initial web sources.")
    parser.add_argument("--db", default=str(DEFAULT_DB))
    parser.add_argument("--fetch-only", action="store_true", help="Only save raw/reference HTML files.")
    args = parser.parse_args()

    db_path = Path(args.db)
    init_db(db_path)
    fetch_reference_pages()
    if args.fetch_only:
        print("Fetched reference pages only.")
        return
    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        count = import_river_site_pages(conn)
    print(f"Imported possible dam records from river site pages: {count}")


if __name__ == "__main__":
    main()
