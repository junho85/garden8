# garden8 MongoDB → Supabase 마이그레이션 (아카이브)

garden8 의 `slack_messages` 컬렉션을 MongoDB 에서 Supabase PostgreSQL 로 옮긴 기록이다.
**이전은 2026-08-29 에 끝났고 운영은 Supabase 를 쓴다.** 이 디렉터리는 되돌아볼 근거로 남긴다.

> 📌 **`20260830_mongodb_dump/` 는 Vultr 서버를 해지하기 전에 뜬 최종 스냅샷이다.**
> 원본 MongoDB 는 Vultr VPS 안에서만 돌고 있었고 서버가 사라지면 함께 사라진다.
> 그래서 저장소에 함께 보관한다. **다시 만들 수 없는 데이터다.**

## 덤프

| | |
| --- | --- |
| 채취일 | 2026-08-30 |
| 출처 | Vultr VPS (`158.247.226.178`) 의 `docker-garden-db-1` 컨테이너 |
| DB.컬렉션 | `garden8.slack_messages` |
| 문서 수 | **929건** |
| 크기 | 1,595,331 bytes |
| 방식 | `mongodump --db garden8 --collection slack_messages` |

문서 수는 2026-08-29 이전 검증 때의 건수와 같다. **이전 이후 원본에 쓰기가 없었다는 뜻**이다.

### 복원

```bash
mongorestore --db garden8 --collection slack_messages 20260830_mongodb_dump/slack_messages.bson
```

BSON 을 직접 읽으려면 `migrate_to_supabase.py` 가 쓰는 `bson` 패키지를 그대로 쓰면 된다.

## 파일 구조

```
archive/migration/
├── README.md                     # 이 파일
├── requirements.txt              # Python 의존성
├── migration_config.yaml.sample  # 설정 템플릿
├── migration_config.yaml         # 실제 설정 — ★ gitignore, 커밋 금지
├── supabase_schema.sql           # 스키마 DDL
├── migrate_to_supabase.py        # 이전 스크립트
└── 20260830_mongodb_dump/        # ★ Vultr 종료 전 최종 스냅샷
    ├── slack_messages.bson
    └── slack_messages.metadata.json
```

## 스키마 설계에서 신경 쓴 것

**`raw` JSONB 컬럼에 원문을 통째로 보존한다.** garden8 는 garden6 에 없던 필드가 있어
(`app_id`, `author_name` 최상위, 스레드 관련 일부) 컬럼만으로는 유실된다.
자주 쓰는 것은 컬럼으로 빼고 **원문 전체는 `raw` 에 남겨** 나중에 꺼낼 수 있게 했다.

## ⚠️ 이전에서 겪은 함정

**타임존.** `MongoTools` 는 `CodecOptions(tz_aware=True, tzinfo=Asia/Seoul)` 로 읽고 있었는데
PostgreSQL 경로에는 그 변환이 없어 **API 응답 시각이 9시간 어긋났다**
(`13:43:47.371` vs `22:43:47.371+09:00`).

★ **출석부 화면은 멀쩡해 보였다.** `/attendance/api/gets` 응답을 운영과 대조해서야 드러났다.
`db_tools.py` 에 UTC → KST 변환을 넣어 맞췄고, 근거로 남기려고 `mongo_tools.py` 는 지우지 않았다.

## 검증

운영(MongoDB) 대 테스트(Supabase) 를 바이트 단위로 대조했다.

- 문서 수 929건 일치
- `ts` 집합 차집합 0
- 작성자별 건수 불일치 0
- `raw` 원문 누락 필드 0
- 출석부 메인, `api/users`, `api/gets` 일치
- **개인별 커밋 페이지 전원 일치**

## 관련

- 같은 방식의 선행 사례 — [junho85/garden6 archive/migration](https://github.com/junho85/garden6/tree/master/archive/migration)
- Vultr → NAS 이전은 2026-08-30 완료. garden4~10 전부 Synology NAS 에서 돌고 Supabase 를 본다.
