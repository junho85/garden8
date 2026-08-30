#!/usr/bin/env python3
"""
garden9 (그리고 garden8) MongoDB slack_messages → Supabase PostgreSQL 이전.

garden6 의 archive/migration/migrate_to_supabase.py 를 참고하되,
BSON 덤프 파일 대신 MongoDB 에서 직접 읽는다(덤프 단계가 하나 줄어든다).

사용법:
    python migrate_to_supabase.py --config migration_config.yaml [--dry-run]
"""
import argparse
import json
import sys
from datetime import datetime, date

import psycopg2
import pymongo
import yaml
from bson import ObjectId
from psycopg2.extras import execute_values

# 컬럼으로 승격하는 필드. 나머지는 raw 에만 담긴다.
COLUMNS = ["ts", "ts_for_db", "author_name", "user", "text", "type",
           "subtype", "bot_id", "app_id", "team", "thread_ts",
           "bot_profile", "attachments", "raw"]
JSON_FIELDS = {"bot_profile", "attachments", "raw"}


def jsonable(v):
    """BSON 타입을 JSON 으로 직렬화 가능하게 변환."""
    if isinstance(v, ObjectId):
        return str(v)
    if isinstance(v, (datetime, date)):
        return v.isoformat()
    if isinstance(v, dict):
        return {k: jsonable(x) for k, x in v.items()}
    if isinstance(v, list):
        return [jsonable(x) for x in v]
    return v


def to_row(doc):
    raw = jsonable(doc)
    row = []
    for c in COLUMNS:
        if c == "raw":
            row.append(json.dumps(raw, ensure_ascii=False))
        elif c in JSON_FIELDS:
            v = doc.get(c)
            row.append(json.dumps(jsonable(v), ensure_ascii=False) if v is not None else None)
        else:
            row.append(doc.get(c))
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="migration_config.yaml")
    ap.add_argument("--dry-run", action="store_true", help="읽기만 하고 쓰지 않는다")
    args = ap.parse_args()

    cfg = yaml.safe_load(open(args.config, encoding="utf-8"))
    m, p = cfg["mongo"], cfg["postgres"]
    schema = p["schema"]

    mc = pymongo.MongoClient(m["uri"])
    coll = mc[m["database"]]["slack_messages"]
    total = coll.count_documents({})
    print(f"MongoDB {m['database']}.slack_messages : {total}건")

    rows = [to_row(d) for d in coll.find().sort("ts", 1)]
    print(f"변환 완료 : {len(rows)}건")

    if args.dry_run:
        print("--dry-run 이므로 여기서 멈춘다.")
        print("샘플 ts :", rows[0][0] if rows else "(없음)")
        return

    conn = psycopg2.connect(p["dsn"])
    conn.autocommit = False
    cur = conn.cursor()
    cur.execute(f'SET search_path TO {schema}')

    cols = ", ".join(f'"{c}"' for c in COLUMNS)
    execute_values(
        cur,
        f"INSERT INTO slack_messages ({cols}) VALUES %s ON CONFLICT (ts) DO NOTHING",
        rows, page_size=200,
    )
    conn.commit()

    cur.execute("SELECT count(*) FROM slack_messages")
    n = cur.fetchone()[0]
    print(f"PostgreSQL {schema}.slack_messages : {n}건")
    print("일치" if n == total else f"★ 불일치 (mongo {total} vs pg {n})")
    conn.close()


if __name__ == "__main__":
    sys.exit(main())
