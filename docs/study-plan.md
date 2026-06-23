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
| `rmf_demos` | **소스 빌드 완료** (jazzy) — `~/open-rmf-test/rmf_ws` 에 있음. `source ~/open-rmf-test/rmf_ws/install/setup.bash` 후 `ros2 launch rmf_demos_gz office.launch.xml`. slotcar 플러그인(`libslotcar.so`)은 apt로 시스템 설치됨 → 추가 빌드 불필요 (2026-06-22 확인) |
| **nav2** | **미설치** — M5 진입 전 설치 필요 |

---

## 3. 학습 사다리 — M1 ~ M6

| 모듈 | 내용 | 원래 step | 쓰는 자산 | nav2? |
|---|---|---|---|---|
| **M1 맵** | SLAM `pgm` → traffic_editor(차선) → `building_map_generator`로 **world + nav graph** 생성 | 1·2·3 | `pgm_to_gazebo`, `traffic_editor` | ❌ |
| **M2 내 로봇** | **pinky URDF를 slotcar로** 1대 등장 (RMF이 직접 구동) | 4 | `pinky_description` | ❌ |
| **M3 다중+교통** | pinky 2~3대 → RMF **traffic negotiation** 관찰 | 5 | — | ❌ |
| **M4 태스크+팔** | delivery 디스패치 + 팔 상차를 **`perform_action` 가짜 신호**로 "했다 치고" | 6 | `rmf_demos_tasks` 패턴 | ❌ |
| **M5 (심화)** | pinky **실제 nav2 + EasyFullControl + domain_bridge** 연동 | — | `pinky_navigation`, `domain_bridge` | ✅ |
| **M6 웹** (선택·개발용) | **rmf-web** 대시보드 = 브라우저에서 **task 제출 + 모니터링**. 실 프로젝트는 자체 `web/` 구축하지만, 개발단계엔 rmf-web 활용 | — | `rmf-web` (open-rmf) | — |

> **핵심**: nav2는 **맨 마지막 M5에서만** 등장한다. M1~M4(slotcar)는 nav2를 *안 하려는 게 아니라*, nav2 연동을 안전하게 배우기 위한 **발판**이다.
> M2→M5의 가장 큰 변화는 fleet_adapter 안의 "로봇 API" 백엔드 하나가 **`slotcar 토픽` → `nav2 NavigateToPose`** 로 바뀌는 것뿐. (= 노트 6장 "실물 이관 시 시뮬 노드만 교체, RMF/nav graph/태스크 재사용".)
>
> **M6(웹·선택)**: `rmf-web`(open-rmf) 대시보드로 브라우저에서 **task 제출 + 모니터링**. **RMF 계층이 아니라 그 위 UI/운영 계층** — 우리 `libi_rmf_tasks`(CLI submitter)의 **GUI 버전 + 모니터링**이다. "task 단위 제어"(배달/순찰 명령)지 직접 운전(teleop)이 아니다. **실 ABA는 `web/`·`service/`를 자체 구축**하지만, **개발·디버깅 단계엔 rmf-web을 붙여** 빠르게 task 던지고 상태 확인하는 용도로 유용. (rmf-web = 프론트 React + api-server가 RMF task API와 연동.)

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
                              └─> traffic_editor(배경=png) 차선 그리기 ──> building.yaml
                                          └─> building_map_generator nav ──> nav graph (어긋남)
                                                          └─> fix_navgraph(pairs 보정) ──> navgraph (실좌표 정렬)
```

### `/10` 스케일 처리 (본인 방식 + 대안)
- **본인 방식(주)**: pgm 위에 차선/노드를 그릴 때 실측이 너무 작아 편집이 불편 → **10m×10m로 키워** 작업 → 결과 좌표를 **÷10** 해 실좌표로 환원.
- **대안(권장 보조)**: traffic_editor의 **measurement(측정선)** — 두 점 사이에 선을 긋고 실거리를 입력하면 전체 스케일을 자동 보정. 결과는 같고 실수가 적다.

### ⚠️ M1 최대 난관 — 좌표 정렬 (대응점 보정으로 해결 ✅ 구현됨)
`pgm_to_gazebo` world(원점=`map.yaml`)와 traffic_editor navgraph는 **출처가 달라** 좌표가 어긋난다. traffic_editor 원점/스케일을 손으로 맞추는 대신, **대응점(pairs)으로 변환을 자동 계산**해 navgraph를 world 좌표계로 보정한다 (도구 `scripts/rmf/`, 상세 흐름은 루트 README "M1 맵 작업").

흐름:
1. `building_map_generator nav` 로 navgraph 생성(어긋난 상태) — 좌표 = `src`
2. rviz에 맵 띄우고 `Publish Point` 로 waypoint 실위치 클릭 → 좌표 = `dst` (`view_map.launch.py` + `ros2 topic echo /clicked_point`)
   - png에 점을 찍어두면 `new_map.png.yaml`(png를 map으로 로드)로 띄워 클릭 정밀도↑
3. `pairs.yaml`(src↔dst) 작성 → `fix_navgraph.py` 가 **2D 닮음변환(scale·회전·이동)** 을 최소제곱으로 계산·적용
   - 대응점 2~3쌍이면 충분(나머지 waypoint는 자동 환산). 클릭 순서를 몰라도 기하로 매칭 가능.
4. 검증: `show_navgraph.py` 로 rviz에 lane·vertex 띄워 통로와 일치 확인 + **RMS 잔차**로 정량 확인.

> 실측: library 맵에서 9쌍 대응점으로 **RMS ≈ 1cm** 달성. offset x ≈ pgm 원점(-10.004)과 일치 → 프레임 정확 복원 확인.
> navgraph는 파생물 → `building.yaml`(편집 원본)은 안 건드리고, `make_navgraph.sh` 로 `new_map.navgraph.yaml` 재생성.

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

- [x] **M1 완료** (2026-06-22): 기존 pgm(B) → world(pgm_to_gazebo) + building.yaml→navgraph + **대응점 보정**(`scripts/rmf/`, RMS≈1cm) + rviz 시각화 검증
- [ ] 각 `libi_rmf_*` 패키지의 빌드 파일(`package.xml`/`CMakeLists.txt`/`setup.py`) 채우기 (M2에서 navgraph 빌드 연동 포함)
- [x] **`rmf_demos` 소스 빌드 확인 완료** (2026-06-22): `~/open-rmf-test/rmf_ws` 에 jazzy 빌드 존재 + slotcar 플러그인 apt 설치본 사용. office 데모 = slotcar 패턴 1순위 참고 (`TinyRobot/model.sdf`)
- [x] **M2-2 pinky→slotcar 전환 + 수동 주행 검증 완료** (2026-06-22): `drive` 스위치(diffdrive↔slotcar)로 pinky에 slotcar 플러그인 장착. headless e2e에서 PathRequest 1발로 pinky가 navgraph 정점 (0.43,9.87)→(0.43,11.11) **1.23m 실주행 확인**.
  - 신규/수정: `pinky_gz_slotcar.urdf.xacro`(slotcar 매크로) · `pinky.urdf.xacro`/`robot.urdf.xacro`(drive 분기) · `upload_robot.launch.py`(robot_description `ParameterValue(str)` fix — 주석 `: ` 가 YAML 파싱 깨던 버그) · `launch_sim.launch.xml`(drive 인자+slotcar 플러그인 경로) · `scripts/rmf/slotcar_drive.py`(PathRequest 발행 검증툴).
  - ⚠️ **함정 발견**: slotcar는 RMF 0으로 못 돈다 — **`building_map_server` 필요**(building.yaml로 level 인식, 없으면 `/robot_state` 미발행). 즉 "수동 주행"도 `building_map_server`(RMF 코어의 작은 조각)는 떠 있어야 함. fleet adapter(step3)보다 가벼운 최소 인프라.
- [~] **M2-3 fleet adapter — 코드 정독 완료, 포팅 시작 전** (2026-06-23): `rmf_demos_fleet_adapter` 파이썬 3종 정독 (`~/open-rmf-test/rmf_ws/src/rmf_demos/rmf_demos_fleet_adapter/rmf_demos_fleet_adapter/`).
  - **구조 이해 = 3겹**: ① `fleet_adapter.py`(RMF 쪽 — `add_easy_fleet`=EasyFullControl 파이썬판, 콜백 navigate/stop/execute_action, `update_robot`이 로봇상태 폴링→RMF 주입) ② `RobotClientAPI.py`(HTTP 클라이언트=다리, **M5에서 갈아끼우는 경계선**) ③ `fleet_manager.py`(FastAPI 서버+ROS노드 — `/robot_state` 구독, `/navigate`→`PathRequest`를 `/robot_path_requests`에 발행).
  - **★아하**: ③ `fleet_manager.py`의 `/navigate`가 곧 우리가 M2-2에서 손으로 한 `slotcar_drive.py`(PathRequest 발행)의 자동화판. 즉 어댑터 = 그 위에 [RMF task→navigate 콜백→HTTP→PathRequest→slotcar 주행→cmd_id 매칭으로 도착감지→`execution.finished()`] 한 바퀴를 얹은 것.
  - **포팅 시 바뀌는 것 2개뿐**: ⓐ `config.yaml`(fleet명 `libi`, 로봇 `pinky`, footprint/limits를 slotcar 파라미터 base_width 0.0961·nominal_drive_speed 0.5에 맞춤) ⓑ `nav_graph`=**M1 보정 navgraph**(안 쓰면 좌표 어긋나 RMF 계획 깨짐). 코드 3파일은 slotcar 백엔드가 이미 있어 거의 복붙+정리.
  - **다음 작업 순서 = B → A** (사용자 합의): **B)** `tinyRobot_config.yaml`(`~/.../config/office/`) 한 줄씩 뜯어 우리 `libi_fleet_config.yaml` 설계 먼저 → **A)** `libi_rmf_fleet_adapter` 패키지 포팅(3파일+config+setup.py). M5에서 ②③만 nav2로 교체.
- [ ] **M2 남은 일**: ① 각 `libi_rmf_*` 빌드파일 채우기 ② `libi_rmf_fleet_adapter`(위 B→A) ③ `libi_rmf_bringup` sim.launch (gz+building_map_server+adapter+navgraph 조립; slotcar GUI 브링업 포함)

> 진행 순서 원칙(노트 6장): **시뮬 1대(같은 도메인) → 다중(교통검증) → 태스크/팔 → 그제서야 nav2(M5)**. 한 번에 한 변수만.
