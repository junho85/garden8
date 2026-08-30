-- garden8: MongoDB slack_messages → Supabase PostgreSQL
-- garden6 의 이전 패턴을 따르되, garden8 의 추가 필드를 유실 없이 담는다.
--   garden6 대비 차이: app_id / author_name 이 최상위에 있고,
--   스레드 관련 필드(thread_ts, reply_*, root, subtype 등)가 일부 문서에 있다.
--   → 자주 쓰는 필드는 컬럼으로 두고, 원문 전체는 raw JSONB 로 보존한다.

CREATE SCHEMA IF NOT EXISTS garden8;
SET search_path TO garden8;

CREATE TABLE IF NOT EXISTS slack_messages (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ts           VARCHAR(20) UNIQUE NOT NULL,   -- MongoDB 와 동일하게 unique
    ts_for_db    TIMESTAMP NOT NULL,
    author_name  VARCHAR(100),                  -- ★ garden8 는 최상위에 있다
    "user"       VARCHAR(20),                   -- user 는 예약어
    text         TEXT,
    type         VARCHAR(20),
    subtype      VARCHAR(30),
    bot_id       VARCHAR(20),
    app_id       VARCHAR(20),
    team         VARCHAR(20),
    thread_ts    VARCHAR(20),
    bot_profile  JSONB,
    attachments  JSONB,
    raw          JSONB NOT NULL,                -- ★ 원본 문서 전체 (무손실)
    created_at   TIMESTAMP DEFAULT NOW()
);

-- 앱이 실제로 쓰는 쿼리 두 개에 맞춘 인덱스
--   1) AttendanceRepository.get_messages_by_author_name: author_name 조회 + ts 정렬
--   2) garden.find_attend: ts_for_db 범위 조회
CREATE INDEX IF NOT EXISTS idx_g8_author_ts   ON slack_messages (author_name, ts);
CREATE INDEX IF NOT EXISTS idx_g8_ts_for_db   ON slack_messages (ts_for_db);
CREATE INDEX IF NOT EXISTS idx_g8_attachments ON slack_messages USING GIN (attachments);

-- garden6 과 동일한 커밋 뷰 (attachments 를 커밋 단위로 펼침)
CREATE OR REPLACE VIEW commit_messages AS
SELECT
    sm.id,
    sm.ts,
    sm.ts_for_db,
    attachment->>'author_name' AS github_username,
    attachment->>'text'        AS commit_message,
    attachment->>'fallback'    AS fallback,
    attachment->>'footer'      AS repository,
    sm.created_at
FROM slack_messages sm,
     LATERAL jsonb_array_elements(sm.attachments) AS attachment
WHERE sm.attachments IS NOT NULL;
