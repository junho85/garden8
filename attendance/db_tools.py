import psycopg2
import pytz
from psycopg2.extras import RealDictCursor, Json

# MongoTools 는 CodecOptions(tz_aware=True, tzinfo=Asia/Seoul) 로 읽어
# datetime 을 KST tz-aware 로 돌려줬다. 화면 출력이 그 값에 의존하므로
# PostgreSQL 경로에서도 같은 모양으로 맞춘다.
KST = pytz.timezone("Asia/Seoul")


class DBTools:
    """
    slack_messages 저장소. 기존 MongoTools 를 대체한다.

    호출부가 mongo 문서(dict)를 그대로 쓰던 코드라, 조회 결과도 dict 로 돌려준다.
    컬럼으로 승격하지 않은 필드(reactions, reply_* 등)는 raw JSONB 에 있으므로,
    조회 시 raw 를 펼쳐 병합해 **mongo 문서와 같은 모양**으로 만든다.

    garden6 의 attendance/db_tools.py 를 참고했으나, garden9 는 author_name 이
    최상위 컬럼이라 attachments 를 뒤질 필요가 없다.
    """

    # 컬럼으로 승격한 필드 (migration/supabase_schema.sql 과 맞춘다)
    COLUMNS = ["ts", "ts_for_db", "author_name", "user", "text", "type",
               "subtype", "bot_id", "app_id", "team", "thread_ts",
               "bot_profile", "attachments"]

    def __init__(self, host, port, database, user, password, schema):
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.schema = schema

    def connect_db(self):
        return psycopg2.connect(
            host=self.host,
            port=self.port,
            database=self.database,
            user=self.user,
            password=self.password,
            sslmode="require",
            gssencmode="disable",
        )

    def get_cursor(self):
        conn = self.connect_db()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(f"SET search_path TO {self.schema}")
        return conn, cursor

    @staticmethod
    def _to_doc(row):
        """DB 행을 mongo 문서와 같은 모양의 dict 로 되돌린다."""
        if row is None:
            return None
        doc = dict(row.get("raw") or {})
        for k in DBTools.COLUMNS:
            if row.get(k) is not None:
                doc[k] = row[k]
        # raw 는 문자열이라 컬럼 값(datetime)을 쓴다.
        # 저장은 naive UTC 이므로 KST tz-aware 로 바꿔 mongo 와 같은 값을 만든다.
        ts = row["ts_for_db"]
        if ts is not None and ts.tzinfo is None:
            ts = pytz.utc.localize(ts)
        doc["ts_for_db"] = ts.astimezone(KST) if ts is not None else None
        return doc

    def find_by_author_name(self, author_name):
        """AttendanceRepository.get_messages_by_author_name 대응. ts 오름차순."""
        conn, cur = self.get_cursor()
        try:
            cur.execute(
                "SELECT * FROM slack_messages WHERE author_name = %s ORDER BY ts ASC",
                (author_name,),
            )
            return [self._to_doc(r) for r in cur.fetchall()]
        finally:
            cur.close()
            conn.close()

    def find_by_ts_for_db_range(self, gte, lt):
        """garden.find_attend 대응. ts_for_db >= gte AND < lt"""
        conn, cur = self.get_cursor()
        try:
            cur.execute(
                "SELECT * FROM slack_messages "
                "WHERE ts_for_db >= %s AND ts_for_db < %s ORDER BY ts_for_db ASC",
                (gte, lt),
            )
            return [self._to_doc(r) for r in cur.fetchall()]
        finally:
            cur.close()
            conn.close()

    def upsert_message(self, message):
        """
        slack 메시지 저장. ts 가 unique 라 이미 있으면 갱신한다.
        mongo 의 update_one(upsert=True) 자리를 대신한다.
        """
        raw = dict(message)
        raw.pop("_id", None)
        values = []
        for c in self.COLUMNS:
            v = message.get(c)
            values.append(Json(v) if c in ("bot_profile", "attachments") and v is not None else v)
        values.append(Json(raw))

        cols = ", ".join(f'"{c}"' for c in self.COLUMNS) + ', "raw"'
        holders = ", ".join(["%s"] * (len(self.COLUMNS) + 1))
        updates = ", ".join(f'"{c}" = EXCLUDED."{c}"' for c in self.COLUMNS if c != "ts") + ', "raw" = EXCLUDED."raw"'

        conn, cur = self.get_cursor()
        try:
            cur.execute(
                f"INSERT INTO slack_messages ({cols}) VALUES ({holders}) "
                f"ON CONFLICT (ts) DO UPDATE SET {updates}",
                values,
            )
            conn.commit()
            return cur.rowcount
        finally:
            cur.close()
            conn.close()

    def delete_all(self):
        """SlackService 의 collection.remove() 자리. 전체 삭제."""
        conn, cur = self.get_cursor()
        try:
            cur.execute("DELETE FROM slack_messages")
            conn.commit()
            return cur.rowcount
        finally:
            cur.close()
            conn.close()

    def count(self):
        conn, cur = self.get_cursor()
        try:
            cur.execute("SELECT count(*) AS c FROM slack_messages")
            return cur.fetchone()["c"]
        finally:
            cur.close()
            conn.close()
