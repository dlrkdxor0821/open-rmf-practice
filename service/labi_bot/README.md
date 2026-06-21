# labi_bot  ─ AI 챗봇 서브시스템 (도서관 가이드)

> ⚠️ **RMF 학습 범위 밖.** ABA 전체 구조를 위한 자리(placeholder)다. 이번 연습의 초점은 `fleet/`.
> ROS 바깥(비-ROS)이라 `service/` 아래 둔다 (pingdergarten 컨벤션).

경량 RAG(정규식 의도 판별 + MariaDB LIKE + 로컬 LLM 주입) 기반 도서관 AI 챗봇.
**완성된 설계안(docker-compose / nginx / DB 스키마)은
[`docs/aba-architecture.md` §7](../../docs/aba-architecture.md)** 에 그대로 있다.

## 폴더 (노트 7-2)
```
labi_bot/
├── docker-compose.yml      # 4서비스: mariadb / ollama / backend(FastAPI) / nginx
├── nginx/labi.conf         # SPA + /api·/ollama 프록시 (스트리밍)
├── db/init/01_schema.sql   # books + robot_logs (mariadb 최초 기동 시 자동)
├── service/backend/        # FastAPI Dockerfile + 코드
└── frontend/dist/          # 빌드된 React SPA
```

> 채우려면 docs/aba-architecture.md §7-1/7-3/7-4 의 내용을 각 파일에 옮기면 된다. (지금은 폴더 골격만)
