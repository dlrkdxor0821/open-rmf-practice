# Open-RMF 연습 — 학습 계획 (ABA · libi_rmf)

> 작성일: 2026-06-21 · **목적: 공부(학습)** — 구현/배포가 아님
> 대상 repo: `open-rmf-practice` (= ABA 모노레포 루트, **pingdergarten 컨벤션**) · 학습 초점: `fleet/src/libi_rmf_*`
> 로봇 URDF: `pinky_pro` · 도착점: **M1~M5** (slotcar → 실 nav2 연동)

이 문서는 "무엇을, 왜, 어떤 순서로 배울지"의 기록이다. 실제 작업은 `fleet/src/libi_rmf_*` 에서 한다.
ABA 전체 아키텍처는 [`aba-architecture.md`](./aba-architecture.md) 참고.

---

## 0. 참고 자산 (이미 보유)

| 경로 | 정체 | 이 연습에서의 역할 |
|---|---|---|
| `/home/asd/open-rmf-test` | 이전 RMF 학습 기록 (rmf_demos office 데모 + traffic_editor 맵 + `building_map_generator`) | **공식 레이아웃/명령어 레퍼런스**. README·트러블슈팅·gogoping 통합문서 포함 |
| `/home/asd/personal_repo/pgm_to_gazebo` | ROS 점유격자(`pgm`+`yaml`) → 자립형 `world.sdf` 변환기 | **M1**: SLAM 맵을 Gazebo world로 변환 |
| `/home/asd/pinky_pro` | 실제 diff-drive 로봇 (URDF + gz 시뮬 + nav2 navigation) | **M2~M5**: RMF에 얹을 로봇 (`pinky_description` URDF) |
| `/home/asd/personal_repo/pingdergarten` | 팀 모노레포 (controller/service/app/db 최상위 분리) | **폴더 컨벤션 원본** (이 repo 배치의 기준) |
| `/home/asd/pinky_rmf/.../rosconkr_rmf/rosconkr_pinky_fleet_adapter` | 실제 pinky용 RMF fleet adapter 예제 (ROSCon KR) | **M2~M5 1순위 코드 참고** (EasyFullControl + nav2 연동) |

> 명명: 패키지는 ABA 프로젝트명 `libi_*`, 로봇 모델은 연습용 `pinky_pro` URDF를 사용한다.

---

## 1. 학습 목적 (가장 중요)

**Open-RMF 전체 flow를 "이해"하는 것**이 목적이다. 제품을 만드는 게 아니다.
그래서 모든 단계는 *변수를 한 번에 하나씩만 늘리는* 사다리(ladder)로 설계했다.

### 가장 큰 깨달음: **nav2 ≠ RMF** (계층이 다르다)

| 계층 | 무엇을 하나 | 비유 | 우리 예시 |
|---|---|---|---|
| **nav2** | **한 대**의 로봇이 A→B 가는 법 (경로계획·장애물회피·코스트맵) | 로봇 한 대의 **운전기사** | `pinky_navigation`, gogoping `nav2_params.yaml` |
| **RMF** | **여러 대**를 지휘 (누가 어떤 일, 교차로 양보, 문/엘베 공유) | 공항 **관제탑** | `open-rmf-test`의 office 데모 |

- **RMF은 장애물 회피 경로계획을 하지 않는다.** 이미 그려진 차선(**nav graph**) 위에서 *교통정리*만 한다.
- 그래서 "RMF = nav2 + params 수정"은 틀렸다. nav2는 *실로봇을 붙일 때* 로봇 쪽 주행스택일 뿐이고, RMF은 그 위 계층이다.
- **증거**: `open-rmf-test`의 office 데모(TinyRobot)는 nav2가 **한 줄도 없다**. 그래도 교통협상·태스크가 다 돈다.

### 시뮬에서 로봇을 움직이는 두 방식

```
[방식 A · slotcar]  RMF ──(직접 구동)──> 로봇 모델                       ← nav2 없음. 학습/데모용 (M2~M4)
[방식 B · 실로봇 ]  RMF ──(EasyFullControl)──> fleet adapter ──(NavigateToPose)──> nav2 ──> 로봇  ← M5
```

### 헷갈리던 `params` 두 종류 (다른 파일·다른 계층)

| 파일 | 누가 읽나 | 내용 |
|---|---|---|
| `libi_fleet_config.yaml` | **RMF** (fleet adapter) | footprint 반경, 최고속도, 배터리 |
| `nav2_params.yaml` | **nav2** (로봇) | 코스트맵, 플래너, BT |

---

## 2. 환경 (확인됨)

| 항목 | 상태 |
|---|---|
| ROS 2 | **Jazzy** ✅ |
| RMF 코어 | `rmf_fleet_adapter`, `rmf_traffic`, `rmf_traffic_editor` 등 설치됨 ✅ |
| Gazebo | **modern `gz sim`** (Harmonic) ✅ |
| `rmf_demos` | 미설치 — apt 바이너리 없음 → **소스 빌드 필요** (jazzy 브랜치). `open-rmf-test/README` 절차 참고 |
| **nav2** | **미설치** — M5 진입 전 설치 필요 |

---

## 3. 학습 사다리 — M1 ~ M5

| 모듈 | 내용 | 원래 step | 쓰는 자산 | nav2? |
|---|---|---|---|---|
| **M1 맵** | SLAM `pgm` → traffic_editor(차선) → `building_map_generator`로 **world + nav graph** 생성 | 1·2·3 | `pgm_to_gazebo`, `traffic_editor` | ❌ |
| **M2 내 로봇** | **pinky URDF를 slotcar로** 1대 등장 (RMF이 직접 구동) | 4 | `pinky_description` | ❌ |
| **M3 다중+교통** | pinky 2~3대 → RMF **traffic negotiation** 관찰 | 5 | — | ❌ |
| **M4 태스크+팔** | delivery 디스패치 + 팔 상차를 **`perform_action` 가짜 신호**로 "했다 치고" | 6 | `rmf_demos_tasks` 패턴 | ❌ |
| **M5 (심화)** | pinky **실제 nav2 + EasyFullControl + domain_bridge** 연동 | — | `pinky_navigation`, `domain_bridge` | ✅ |

> **핵심**: nav2는 **맨 마지막 M5에서만** 등장한다. M1~M4(slotcar)는 nav2를 *안 하려는 게 아니라*, nav2 연동을 안전하게 배우기 위한 **발판**이다.
> M2→M5의 가장 큰 변화는 fleet_adapter 안의 "로봇 API" 백엔드 하나가 **`slotcar 토픽` → `nav2 NavigateToPose`** 로 바뀌는 것뿐. (= 노트 6장 "실물 이관 시 시뮬 노드만 교체, RMF/nav graph/태스크 재사용".)

---

## 4. scaffold — pingdergarten 컨벤션 (최상위 기능별 폴더)

ROS2 코드만 `controller/`·`fleet/` 의 **각각 독립 colcon ws(`src/`)** 에, 비-ROS(service·app·web·db)는
ROS 바깥 최상위에. 학습 작업은 **`fleet/src/libi_rmf_*`** 에서 한다.

```
open-rmf-practice/
├── controller/                          # [Equipment] 로봇 온보드 — 보드별 colcon ws
│   ├── libi-drive-controller/src/libi_drive/   # nav2 주행 (Drive Board) — RMF이 직접 지휘
│   └── libi-handy-controller/src/libi_handy/   # MoveIt 팔 (Handy Board) — perform_action 트리거
│
├── fleet/                               # ★ RMF 관제 (colcon ws) ── 학습 초점
│   └── src/
│       ├── libi_rmf_maps/               # ① 지도            (ament_cmake)  ─ M1
│       │   └── maps/library/                building.yaml + pgm + png
│       ├── libi_rmf_fleet_adapter/      # ② RMF↔로봇 통역 ★ (ament_cmake/C++) ─ M2→M5
│       │   ├── src/  include/               fleet_adapter / RobotClientAPI / nav2_robot_api
│       │   └── config/                      libi_fleet_config.yaml
│       ├── libi_rmf_bridge/             # ③ domain_bridge   (ament_cmake)  ─ M5에서만
│       │   ├── config/                      robot_to_rmf.yaml / rmf_to_robot.yaml
│       │   └── launch/                      bridge.launch.xml
│       ├── libi_rmf_tasks/              # ④ 태스크+팔 훅     (ament_python) ─ M4
│       │   └── libi_rmf_tasks/              dispatch_*.py / action_hooks.py
│       └── libi_rmf_bringup/            # ⑤ launch 조립      (ament_cmake)  ─ M2~
│           ├── launch/include/              common.launch.xml
│           └── config/
│
├── service/ {libi_service, aba_service, ai_service, labi_bot}   # [Server] 비-ROS (자리만)
├── app/ libi_gui/      web/ {library_member, librarian}         # [Client] (자리만)
└── db/  docs/  scripts/  tests/  pyproject.toml  docker-compose.yml
```

| ABA 노트 패키지 | 빌드타입 | 생기는 시점 | slotcar(M2~4) 역할 | nav2(M5) 역할 |
|---|---|---|---|---|
| `libi_rmf_maps` | ament_cmake | M1 | building.yaml → world+navgraph | 동일 (재사용) |
| `libi_rmf_fleet_adapter` | **ament_cmake/C++** | M2 | 로봇 API가 **slotcar 토픽** 구동 | 로봇 API가 **nav2 `NavigateToPose`** 구동 |
| `libi_rmf_bridge` | ament_cmake | M5 | (불필요) | 로봇↔RMF 도메인 연결 |
| `libi_rmf_tasks` | ament_python | M4 | delivery + 팔 `perform_action` | 동일 |
| `libi_rmf_bringup` | ament_cmake | M2 | `sim.launch` | `real.launch`(nav2+bridge) 추가 |

> 노트 4-2: fleet adapter는 **C++ EasyFullControl**이 원본. 단 학습은 **`rmf_demos_fleet_adapter`(Python)** 를 먼저 읽고 패턴 체득 후 C++로 옮기는 순서를 권장.

---

## 5. M1 맵 파이프라인 상세

목표: pinky가 다닐 **world(시각/충돌)** 와 **nav graph(차선)** 를 만든다.

```
SLAM ──> map.pgm + map.yaml ──┬─> pgm_to_gazebo ──> world.sdf        (벽/바닥/충돌 — Gazebo 화면)
                              └─> traffic_editor(배경=pgm) 차선 그리기 ──> building.yaml
                                                          └─> building_map_generator nav ──> nav graph (*.yaml)
```

### `/10` 스케일 처리 (본인 방식 + 대안)
- **본인 방식(주)**: pgm 위에 차선/노드를 그릴 때 실측이 너무 작아 편집이 불편 → **10m×10m로 키워** 작업 → 결과 좌표를 **÷10** 해 실좌표로 환원.
- **대안(권장 보조)**: traffic_editor의 **measurement(측정선)** — 두 점 사이에 선을 긋고 실거리를 입력하면 전체 스케일을 자동 보정. 결과는 같고 실수가 적다.

### ⚠️ M1 최대 난관 — 좌표 정렬 (검증 단계로 못박음)
`pgm_to_gazebo` world의 좌표계(`map.yaml`의 원점·해상도)와 traffic_editor nav graph(÷10 한 좌표)가 **같은 실좌표계로 맞물려야** 로봇이 벽을 안 뚫는다.
- 검증: nav graph의 waypoint 몇 개를 world에 띄워 벽/통로와 일치하는지 눈으로 확인.
- 안 맞으면 traffic_editor 원점/스케일을 `map.yaml`에 맞춰 재조정.

### 🔧 M1 미정 결정 (나중에 택1)
- **A. SLAM 직접**: pinky gz 시뮬에서 `slam_toolbox`로 주행하며 맵 작성 → pgm 저장. (전체 경험 ↔ teleop/slam 셋업 부담)
- **B. 기존 pgm으로 시작**: `pgm_to_gazebo`의 test_map 또는 pinky 기존 맵 pgm 사용. SLAM 메커니즘만 생략. (RMF에 더 빨리 진입)

---

## 6. 핵심 함정 3가지 (초반에 정리 — 노트 5장 계승)

1. **좌표 정렬** (M1) — 위 §5. pgm world ↔ traffic_editor navgraph 실좌표 일치.
2. **action 도메인 브릿지** (M5) — `domain_bridge`는 토픽/서비스는 OK지만 **`NavigateToPose`(action)** 은 까다로움. → **fleet adapter를 로봇 도메인에서 실행**해 우회 (RMF 표준 토픽만 브릿지).
3. **RMF ↔ 로컬행동 주행권 충돌** (M5) — RMF와 로컬 행동(추종/도킹 등)이 둘 다 nav2를 건드리면 충돌. → 역할 분리: RMF=이동/교통, 로컬행동은 `perform_action`으로 호출.

---

## 7. 다음 액션

- [ ] **M1-결정**: SLAM 직접(A) vs 기존 pgm(B) 택1
- [ ] 각 `libi_rmf_*` 패키지의 빌드 파일(`package.xml`/`CMakeLists.txt`/`setup.py`) 채우기
- [ ] `rmf_demos` 소스 빌드 (slotcar 에셋/런치 참고용) — `open-rmf-test/README` 절차
- [ ] M1 착수: pgm → world + traffic_editor nav graph + 좌표 정렬 검증

> 진행 순서 원칙(노트 6장): **시뮬 1대(같은 도메인) → 다중(교통검증) → 태스크/팔 → 그제서야 nav2(M5)**. 한 번에 한 변수만.
