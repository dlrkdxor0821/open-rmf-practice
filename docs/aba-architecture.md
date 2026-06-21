# ABA — 아키텍처 & 프로젝트 Scaffold 결정 노트

> 작성일: 2026-06-21 · 대상: Team Arte / **ABA (Arte Book Asistance)** — 도서관 책 배달·수거 모바일 매니퓰레이터
> 상태: 설계 결정 메모 (구현 전 합의용)
>
> ℹ️ 이 repo(`open-rmf-practice`)는 ABA 모노레포 구조를 따라 **Open-RMF 부분을 학습**하는 연습장이다.
> 학습 계획·진행은 [`study-plan.md`](./study-plan.md) 참고.
>
> ⚠️ **실제 repo 배치는 pingdergarten 컨벤션으로 재구성됨** (최상위 `controller/ fleet/ service/ app/ web/`,
> ROS 코드만 colcon ws의 `src/`). 실제 배치는 [`../README.md`](../README.md)·[`study-plan.md`](./study-plan.md) 참조.
> 아래 **§3 폴더 구조는 원본 노트 보존용**이며 실제 디렉터리와 다르다 (특히 `fleet_management/libi_rmf` → `fleet/src/libi_rmf_*`).

---

## 1. 시스템 개요

**모바일 매니퓰레이터** = 주행 AMR + 로봇팔. RMF(Open-RMF)를 관제(fleet management)로 얹어 작업을 오케스트레이션.

| 구성 | 역할 | 패키지(예) |
|---|---|---|
| 주행 (mobile) | AMR nav2 주행 | `libi_drive` |
| 팔 (arm) | 매니퓰레이션(상/하차) | `libi_handy` |
| 관제 (fleet) | RMF 교통·태스크 오케스트레이션 | `libi_rmf` |
| UI ×3 | PyQt(`libi_gui`) + 웹(`library_member`, `librarian`) | — |

---

## 2. SW 아키텍처 (3계층)

```
[Client]    Library Member / Librarian 브라우저  ──HTTP──┐
[Server]    ABA Service + ABA DB / Libi Service / AI Service
              │ ROS2(DDS)                         │ UDP(Image→AI)
[Equipment] Libi Drive Board (Controller+GUI)  ──DDS──  Libi Handy Board (Handy Controller)
```
- 통신: HTTP(클라↔서버), ROS2/DDS(서비스↔컨트롤러, drive↔handy), UDP(Image→AI), TCP(서버간)
- RMF 위치: **Libi Service 와 Libi Controller 사이의 "이동 지휘자"** (서버/코디네이터에서 실행, ROS2 로 drive 에 명령)

---

## 3. 폴더 구조 (Scaffold)

README 컨벤션(`fleet_management / robot_arm / mobile_robot / gui`)을 따르되 패키지 단위로 상세화.

```
ABA/                              # monorepo 루트
├── src/
│   ├── mobile_robot/             # [Equipment] 주행 온보드 ROS2
│   │   └── libi_drive/           #   nav2 스택
│   ├── robot_arm/                # [Equipment] 팔 온보드 ROS2
│   │   └── libi_handy/           #   MoveIt 등
│   │
│   ├── fleet_management/         # ★ RMF 관제 (robot 컨트롤러와 분리)
│   │   └── libi_rmf/
│   │       ├── libi_rmf_maps/            building.yaml → world/nav graph   (ament_cmake)
│   │       ├── libi_rmf_fleet_adapter/   RMF↔nav2 통역  ★핵심             (ament_cmake / C++)
│   │       ├── libi_rmf_bridge/          domain_bridge 설정                (ament_cmake)
│   │       ├── libi_rmf_tasks/           태스크 + 팔 perform_action 훅      (ament_python)
│   │       └── libi_rmf_bringup/         launch 조립                       (ament_cmake)
│   │
│   ├── service/                  # [Server] 백엔드
│   │   ├── libi_service/         #   ROS2 ↔ 로봇
│   │   ├── aba_service/          #   웹 백엔드(클라이언트)
│   │   └── ai_service/           #   AI(비전, UDP 수신)
│   │
│   └── gui/                      # [Client] UI
│       ├── libi_gui/             #   PyQt (Drive Board 탑재)
│       ├── library_member/       #   웹 (회원)
│       └── librarian/            #   웹 (사서)
│
├── docs/                         # 문서/이미지/다이어그램
├── scripts/                      # 빌드/운영/테스트
├── db/                           # ABA DB 스키마/마이그레이션
├── tests/
├── pyproject.toml                # 비-ROS Python 의존성 (extras 그룹)
└── docker-compose.yml
```

---

## 4. 핵심 설계 결정

### 4-1. RMF 는 `fleet_management` 에 (컨트롤러와 분리)
- `mobile_robot/`·`robot_arm/` = **로봇 보드 온보드 제어** (로봇 위에서 실행)
- `fleet_management/libi_rmf` = **로봇들을 지휘하는 오케스트레이션** (서버/코디네이터에서 실행)
- 성격이 다르므로 분리. RMF 는 `mobile_robot`/`robot_arm` 에 **코드 의존하지 않고 ROS2 토픽/액션으로만** 통신 → 컨트롤러들이 RMF 없이도 단독 동작.
- RMF 가 직접 지휘하는 건 **주행(libi_drive)**. 팔은 태스크 도착 후 **`perform_action`** 으로 트리거.

### 4-2. 언어 — fleet 는 C++, 나머지는 자유 (혼합 OK)
- RMF fleet adapter 는 **C++ EasyFullControl** 사용 (`rmf_fleet_adapter/agv/EasyFullControl.hpp` + `librmf_fleet_adapter.so`). Python 은 이 C++ 의 바인딩이라, C++ 가 "원본".
- 워크스페이스 레벨 혼합 OK: `fleet`=C++, `tasks`/`service`/`gui`=Python. ROS2 로 통신하므로 무관.
- **패키지 1개 = 빌드타입 1개** 유지 (ament_cmake=C++, ament_python=Python).

### 4-3. 의존성 관리 — pyproject.toml + ROS 분리 (2층)
```
ROS2 패키지 (C++ fleet, Python tasks)  →  package.xml + rosdep + colcon
비-ROS Python (service/gui/scripts)     →  루트 pyproject.toml (+ extras)
```
- `pyproject.toml` 권장 (requirements.txt 단독 ❌). 배포 대상별 extras 로 그룹화:
  ```toml
  [project.optional-dependencies]
  ai  = ["ultralytics", "torch"]   # AI 서버
  gui = ["PyQt5"]                  # drive board
  web = ["fastapi", "uvicorn"]     # 백엔드
  dev = ["pytest", "ruff"]
  ```
  설치: `pip install -e ".[ai]"` 등.
- ⚠️ **주의점**: ROS 노드는 system python3 에서 돔 → ROS 노드가 쓰는 Python 패키지는 **system python 에 설치**, service 용은 pyproject. 두 풀을 섞지 말 것.
- 재현성 필요 시(도커) `pip freeze`/`uv lock` 잠금 파일만 추가. 선언은 pyproject.

---

## 5. RMF ↔ 주행(nav2) 통합 메모

| 항목 | 결정 |
|---|---|
| 주행 스택 | nav2 표준 → RMF EasyFullControl 연동 (우호적) |
| URDF | **변경 불필요**, 기존 로봇 URDF 재사용. RMF 는 footprint 반경만 fleet config 에 |
| nav2 주행권 | RMF=이동/교통, 로컬 행동(추종/도킹)은 분리 → 충돌 방지 |
| 도메인 | 네임스페이스 없이 **domain_bridge** 로 로봇 도메인↔RMF 도메인 연결, CycloneDDS |

⚠️ **함정 2가지** (초반 정리):
1. **action 도메인 브릿지** — domain_bridge 는 토픽/서비스는 OK, NavigateToPose(action)는 까다로움 → **fleet adapter 를 로봇 도메인에서 실행**해 우회 (RMF 표준 토픽만 브릿지).
2. **RMF ↔ 로컬 행동 주행권 충돌** — 둘 다 nav2 를 건드리면 충돌 → 역할 분리.

---

## 6. 권장 진행 순서

1. **시뮬 1대 + 같은 도메인**에서 RMF fleet adapter PoC (domain_bridge 없이, 변수 최소화)
2. **domain_bridge 로 도메인 분리** 추가 (5장 우회법 적용)
3. **다중 로봇** 확장 (traffic negotiation 검증)
4. **팔 작업을 perform_action 으로 통합** (상/하차)
5. **실물 이관** — 시뮬 노드만 교체, RMF/nav graph/태스크 재사용

> 가장 큰 함정은 5장의 2가지. 이것만 초반에 설계로 정리하면 나머지는 rmf_demos 패턴을 따라가면 된다.

---

## 7. Labi Bot — AI 챗봇 서브시스템 & Docker 구성

도서관 AI 가이드 챗봇. **경량 RAG**(정규식 의도 판별 + MariaDB LIKE 검색 + 로컬 LLM 프롬프트 주입)로, 임베딩/벡터DB/Elasticsearch 없이 구현. ROS 로봇과 분리된 AI Service 서브시스템.

처리 흐름:
```
자연어/음성 입력 → 의도 판별(정규식) → 후보 도서 검색(MariaDB LIKE)
→ 컨텍스트 생성 → 로컬 LLM(Ollama) 주입 → 스트리밍 응답 → 도서 카드/서가 위치
```

### 7-1. Docker 구성 — 4 서비스 (DB 1개)

| 서비스 | 역할 | 비고 |
|---|---|---|
| `mariadb` | 데이터 (books + robot_logs) | DB 1개에 테이블만 분리 |
| `ollama` | 로컬 LLM (qwen3:1.7b) | 모델 볼륨 보존, 유동 교체 |
| `backend` | FastAPI (도서/관리 API + STT WS, 8010) | nginx 만 접근 |
| `nginx` | React SPA 서빙 + `/api`·`/ollama` 프록시 | **개발 중엔 생략 가능** |

> 배포: 4개 / 개발: `mariadb`+`ollama`+`backend` 3개 + 프론트 dev 서버. (DB 관리 UI(adminer)는 불필요 → 미포함)

```yaml
# service/labi_bot/docker-compose.yml
services:
  mariadb:
    image: mariadb:11
    container_name: labi-mariadb
    restart: unless-stopped
    environment:
      MARIADB_DATABASE: labi
      MARIADB_USER: labi
      MARIADB_PASSWORD: labi
      MARIADB_ROOT_PASSWORD: change-me
    ports: ["3306:3306"]
    volumes:
      - mariadb_data:/var/lib/mysql
      - ./db/init:/docker-entrypoint-initdb.d:ro   # 최초 1회 스키마/시드 자동 실행
    healthcheck:
      test: ["CMD", "healthcheck.sh", "--connect", "--innodb_initialized"]
      interval: 5s
      timeout: 3s
      retries: 10

  ollama:
    image: ollama/ollama:latest
    container_name: labi-ollama
    restart: unless-stopped
    ports: ["11434:11434"]
    volumes:
      - ollama_models:/root/.ollama        # 받은 모델 보존
    # GPU(NVIDIA) 시 주석 해제 (qwen3:1.7b 는 CPU 도 가능)
    # deploy:
    #   resources:
    #     reservations:
    #       devices: [{ driver: nvidia, count: all, capabilities: [gpu] }]

  backend:
    build: ./service/backend
    container_name: labi-backend
    restart: unless-stopped
    depends_on:
      mariadb: { condition: service_healthy }
      ollama:  { condition: service_started }
    environment:
      DATABASE_URL: mysql+asyncmy://labi:labi@mariadb:3306/labi
      OLLAMA_BASE_URL: http://ollama:11434
      OLLAMA_MODEL: qwen3:1.7b             # 모델 교체는 이 값만 변경
    expose: ["8010"]                       # 외부 직노출 X

  nginx:
    image: nginx:alpine
    container_name: labi-nginx
    restart: unless-stopped
    depends_on: [backend, ollama]
    ports: ["80:80"]
    volumes:
      - ./frontend/dist:/usr/share/nginx/html:ro
      - ./nginx/labi.conf:/etc/nginx/conf.d/default.conf:ro

volumes:
  mariadb_data:
  ollama_models:
```

> Ollama 모델 최초 1회: `docker exec -it labi-ollama ollama pull qwen3:1.7b`

### 7-2. 폴더 구성 (한 세트)

```
service/labi_bot/
├── docker-compose.yml          # 오케스트레이션
├── nginx/labi.conf             # 웹 라우팅 (nginx 마운트)
├── db/init/01_schema.sql       # DB 테이블 (mariadb 최초 기동 시 자동 실행)
├── service/backend/            # FastAPI Dockerfile + 코드
└── frontend/dist/              # 빌드된 React SPA
```

### 7-3. nginx 라우팅 (스트리밍 대응)

```nginx
server {
  listen 80;
  location / { root /usr/share/nginx/html; try_files $uri /index.html; }   # SPA
  location /api/ { proxy_pass http://backend:8010; }
  location /api/speech/ws {                       # 음성 STT WebSocket
    proxy_pass http://backend:8010;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
  }
  location /ollama/ {                              # LLM 스트리밍
    proxy_pass http://ollama:11434/;
    proxy_buffering off;                           # 토큰 즉시 전달
    proxy_read_timeout 600s;                       # 장시간 생성 대응
  }
}
```

### 7-4. DB 스키마 (books + robot_logs, 같은 DB)

```sql
-- 도서: 정보 + 위치 + 재고 (LIKE 검색 + LLM 컨텍스트 주입 대상)
CREATE TABLE books (
  id          INT PRIMARY KEY AUTO_INCREMENT,
  title       VARCHAR(255), author VARCHAR(255),
  summary     TEXT, category VARCHAR(50),
  for_whom_kr VARCHAR(255),
  location    VARCHAR(20),          -- 서가 위치 (예: A-03-02)
  stock       INT DEFAULT 0,        -- 재고 (보유 우선 정렬)
  lang        VARCHAR(10),
  FULLTEXT idx_search (title, author, summary, for_whom_kr)
);

-- 로봇 작업 로그 = rosout 저장 (rcl_interfaces/msg/Log 매핑)
CREATE TABLE robot_logs (
  id        BIGINT PRIMARY KEY AUTO_INCREMENT,
  ts        DATETIME(3) DEFAULT CURRENT_TIMESTAMP(3),  -- stamp (ms)
  level     VARCHAR(10),     -- DEBUG/INFO/WARN/ERROR/FATAL
  node      VARCHAR(120),    -- rosout name
  msg       TEXT,            -- rosout msg
  task_id   VARCHAR(50),     -- 작업(배달/수거) 추적 (선택)
  robot_id  VARCHAR(50),     -- 로봇 식별 (선택)
  INDEX idx_ts (ts), INDEX idx_level (level)
);
```

- `robot_logs`: 작은 **로그 싱크 노드**가 `/rosout` 구독 → INSERT. rosbag 대신 DB 영구 저장으로 웹 조회 가능.
- 로그량 많으면 `level >= WARN` 만 저장하거나 오래된 로그 주기 삭제 고려.
