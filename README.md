# open-rmf-practice

ABA(도서관 책 배달·수거 모바일 매니퓰레이터)의 **Open-RMF 부분을 학습**하기 위한 연습 repo.
폴더 컨벤션은 **pingdergarten** 모노레포를 따른다 — 최상위에 기능별 폴더를 두고, **ROS2 코드만**
`controller/`·`fleet/` 의 colcon 워크스페이스(`src/`)에, 비-ROS(service·app·web·db)는 ROS 바깥에 둔다.

## 문서
- [`docs/study-plan.md`](docs/study-plan.md) — **학습 계획** (목적·nav2↔RMF 구분·M1~M5 사다리·함정)
- [`docs/aba-architecture.md`](docs/aba-architecture.md) — ABA 아키텍처 노트 원본 (구조는 pingdergarten식으로 재배치됨)

## 학습 초점: `fleet/` (RMF 관제)
나머지(`controller`, `service`, `app`, `web`, `db`)는 ABA 전체 구조를 위한 **자리(placeholder)** 이며,
이번 연습의 작업은 `fleet/src/libi_rmf_*` 에서 한다.

```
open-rmf-practice/                       # ABA 모노레포 (pingdergarten 컨벤션)
│
├── controller/                          # [Equipment] 로봇 온보드 ROS2 — 보드별 colcon ws
│   ├── libi-drive-controller/src/libi_drive/   # nav2 주행 (Drive Board)
│   └── libi-handy-controller/src/libi_handy/   # MoveIt 팔 (Handy Board)
│
├── fleet/                               # ★ RMF 관제 (controller와 분리) — colcon ws ── 학습 초점
│   └── src/
│       ├── libi_rmf_maps/               #   building.yaml → world/nav graph  (ament_cmake)
│       ├── libi_rmf_fleet_adapter/      #   RMF↔로봇 통역 ★핵심            (ament_python · EasyFullControl 포팅)
│       ├── libi_rmf_bridge/             #   domain_bridge 설정             (ament_cmake)
│       ├── libi_rmf_tasks/              #   태스크 + 팔 perform_action 훅   (ament_python)
│       └── libi_rmf_bringup/            #   launch 조립                    (ament_cmake)
│
├── service/                             # [Server] 비-ROS 백엔드 (자리만)
│   ├── libi_service/  aba_service/  ai_service/
│   └── labi_bot/                        #   AI 챗봇 (자체 docker-compose, 노트 §7)
├── app/    libi_gui/                    # [Client] PyQt 데스크톱 (자리만)
├── web/    library_member/  librarian/  # [Client] 웹 (자리만)
│
├── db/  docs/  scripts/  tests/
├── pyproject.toml                       # 비-ROS Python 의존성 (extras)
└── docker-compose.yml                   # 전체 스택 (자리만)
```

## colcon 워크스페이스 (3개)
- `controller/libi-drive-controller/` · `controller/libi-handy-controller/` · `fleet/` 가 **각각 독립 colcon ws** (협업·배포 시 보드/서버별 분리용).
- **학습 단계에선 ws를 따로 빌드하지 않고 루트에서 한 번에 빌드한다** (source 한 번으로 전부 잡혀 편함). 보드별 분리 빌드는 실제 하드웨어 배포 때만.
- 비-ROS Python(`service`/`app`/`web`)은 colcon이 안 건드림 → 루트 `pyproject.toml` 로 관리 (노트 4-3).

## 실행 방법 (빌드)

```bash
# ① 밑바탕 ROS
source /opt/ros/jazzy/setup.bash

# ② 의존성 설치 ★빌드 전 필수 — 안 하면 xacro 등이 빠져 빌드 실패
cd ~/personal_repo/open-rmf-practice
rosdep install --from-paths . --ignore-src -r -y

# ③ 루트에서 전체 빌드
colcon build --symlink-install

# ④ 결과 적용
source install/setup.bash
```

- **rosdep 최초 1회**: `command not found` / `no sources list` 가 뜨면 → `sudo rosdep init && rosdep update`.
- **M1~M4(시뮬)만 할 땐** 시뮬에 필요한 2개만 빌드하면 충분 (실물 HW 의존성 회피):
  ```bash
  rosdep install --from-paths controller/libi-drive-controller/src/pinky_pro/pinky_description \
                              controller/libi-drive-controller/src/pinky_pro/pinky_gz_sim \
                 --ignore-src -r -y
  colcon build --symlink-install --packages-select pinky_description pinky_gz_sim
  ```
- **nav2는 M5에서만** 필요. rosdep이 nav2를 무겁게 끌어오는 게 싫으면 `--skip-keys "navigation2 nav2_bringup"` 추가.
- `--symlink-install`: launch·config·python 수정 시 **재빌드 없이** 반영 (학습에 편함).
- ⚠️ 루트 빌드 ↔ ws별 빌드를 **섞지 말 것** (install 공간이 흩어져 헷갈림). 공부 중엔 "항상 루트에서".

## M1 맵 작업 — navgraph 좌표 보정 (`scripts/rmf/`)

가제보 world는 pgm_to_gazebo(pgm 기준), navgraph는 building.yaml(traffic_editor 기준)로 **따로** 생성돼
좌표가 어긋날 수 있다(M1 함정). 대응점 몇 개로 **scale·회전·이동**을 맞춰 navgraph를 world 좌표계로 보정한다.

| 파일 | 역할 |
|---|---|
| `make_navgraph.sh` | building.yaml → navgraph 생성 + (pairs 주면) 보정까지 한 번에 |
| `fix_navgraph.py` | navgraph 보정 핵심 (대응점 → 2D 닮음변환) |
| `view_map.launch.py` · `view_map.rviz` | 맵을 rviz에 **실좌표**로 띄움 (dst 좌표 읽기용) |
| `show_navgraph.py` | navgraph(lane·vertex)를 rviz 마커로 표시 (단독 실행 가능 — gazebo 테스트 때도 사용) |
| `pairs.example.yaml` | 대응점(pairs) 작성 예시 |

워크플로우 (루트에서, `source /opt/ros/jazzy/setup.bash` 후):

```bash
# 1) navgraph 생성 + 좌표(src) 보기
scripts/rmf/make_navgraph.sh fleet/src/libi_rmf_maps/maps/library/new_map.building.yaml

# 2) rviz로 맵 띄워 dst 좌표 읽기 ('Publish Point' 클릭 후 맵 클릭)
#    점 찍은 png를 보려면 new_map.png.yaml 로 띄움 (pgm과 동일 좌표, 좌표읽기 전용)
ros2 launch scripts/rmf/view_map.launch.py map:=fleet/src/libi_rmf_maps/maps/library/new_map.png.yaml
ros2 topic echo /clicked_point        # point.x, point.y = dst (rviz 하단 상태바에도 표시)

# 3) new_map.pairs.yaml 작성 (맵 폴더에): src=1단계 출력, dst=2단계 클릭. 멀리 떨어진 2쌍+
#    pairs.example.yaml 복사해서 채움

# 4) 보정 실행 → new_map.navgraph.yaml 생성
scripts/rmf/make_navgraph.sh \
  fleet/src/libi_rmf_maps/maps/library/new_map.building.yaml \
  fleet/src/libi_rmf_maps/maps/library/new_map.pairs.yaml

# 5) (확인) rviz에 맵 + navgraph(lane·vertex) 띄워 정렬 눈으로 검증
ros2 launch scripts/rmf/view_map.launch.py \
  map:=fleet/src/libi_rmf_maps/maps/library/new_map.yaml \
  navgraph:=fleet/src/libi_rmf_maps/maps/library/new_map.navgraph.yaml
```

- 결과: `new_map.navgraph.yaml` (building.yaml 옆에 저장). **RMS 잔차 작으면 성공**(scale 달라도 OK). 파생물이라 building.yaml/pairs.yaml 바뀌면 4단계 재실행. building.yaml(편집용 원본)은 안 건드림.
- **dst 기준점 보이게**: 점 찍은 `new_map.png` 를 rviz에 띄우려면 2단계처럼 `new_map.png.yaml` 사용. 점은 **빈 공간에 진하게**, traffic_editor 배경과 **같은 png**를 써야 "점=vertex=클릭점"이 일치. 실제 주행 맵은 `new_map.yaml`(pgm) 그대로 사용.
- `new_map.png.yaml` 과 `new_map.yaml` 의 **origin·resolution 은 항상 같게** 유지 (안 그러면 dst 어긋남).
- **navgraph 시각화**: 5단계가 rviz에 lane(노랑 선)·vertex(시안 점)를 띄워준다(내부적으로 `show_navgraph.py` 실행). `show_navgraph.py` 는 독립 노드라 **나중에 gazebo 테스트의 rviz에도** 단독으로 얹을 수 있음: `python3 scripts/rmf/show_navgraph.py <navgraph.yaml>` → rviz에 MarkerArray `/navgraph_markers` 추가.

## M2~M3 시뮬 실행 — RMF가 slotcar 로봇 구동 (`scripts/`)

RMF가 **task를 받아 navgraph 위로 로봇을 자동 주행**시키는 걸 검증한다. M2~M4는 **slotcar**(RMF가 직접
구동하는 가짜 로봇)로 돌린다 (nav2는 M5에서만). 어댑터·bringup·config·navgraph는 그대로 두고 **로봇 백엔드만**
M5에서 nav2+domain_bridge 로 갈아끼우는 게 본질.

### 구동 모드 토글 — `MODE`
`libi_sim.sh` 한 토글로 두 백엔드를 띄운다:
- `MODE=diffdrive` (기본) — gz DiffDrive(`/cmd_vel`) 로봇. **M5/실로봇 경로**.
- `MODE=slotcar` — RMF slotcar(`/robot_path_requests` 구독·`/robot_state` 발행). **M2~M4 RMF 학습용**.
  - **후진 금지** (`reversible: false`) — 뒤로 갈 일이 있으면 **제자리 회전(차동구동, 180° 등) 후 전진**.
    config(RMF 계획) + slotcar 플러그인(sim 동작) 둘 다 `false`.
  - **M3**: slotcar **2대**(pinky1 위 charger·pinky2 아래 charger) 스폰 → 교차로 양보 negotiation 관찰.
    (slotcar 는 `/robot_state` 의 `name` 필드로 로봇을 구분 → 네임스페이스 불필요. 실로봇 다중도메인은 M5 domain_bridge.)
    - RViz: **pinky1 만 RobotModel 로 표시**(gz pose 연결). pinky2 는 **Gazebo 에서** 본다 — 2대 다 RViz 풀표시는
      네임스페이스 + 2번째 RobotModel 이 필요한데, **negotiation 관찰은 Gazebo 가 메인**이라 보류(동작엔 영향 없음).

### 실행 (3 터미널)
```bash
# 0) 초기화 — 좀비 gz/RMF 프로세스 정리
scripts/libi_kill.sh

# 1) 터미널1 — sim (gz + slotcar + rviz). M3 는 slotcar 2대.
MODE=slotcar scripts/libi_sim.sh

# 2) 터미널2 — RMF 코어 + 어댑터 (sim 다 뜬 뒤! 순서 중요 — slotcar 가 fresh /map 받아 레벨 잡음)
scripts/rmf.sh                            # 맵 경로 자동 + 코어+어댑터 (Ctrl-c 종료)
#   로그 'Adding robot [pinky1]/[pinky2]' + `ros2 topic info /robot_state` Publisher>0 이면 online

# 3) 터미널3 — task dispatch (rmf_demos_tasks = 테스트용 CLI, ~/open-rmf-test 워크스페이스)
source /opt/ros/jazzy/setup.bash && source ~/open-rmf-test/rmf_ws/install/setup.bash
ros2 run rmf_demos_tasks dispatch_go_to_place -F libi -R pinky1 -p point_b --use_sim_time
ros2 run rmf_demos_tasks dispatch_go_to_place -F libi -R pinky2 -p point_a --use_sim_time   # M3: 마주보게 → 충돌→양보
```
→ RMF 가 두 로봇을 navgraph 위로 몰고, 경로가 겹치면 **rmf_traffic_schedule + negotiation 으로 한 대를 양보**시킨다.

- **종료/리셋**: `scripts/libi_sim.sh down` + 터미널2·3 `Ctrl-c`. 안 죽으면 `scripts/libi_kill.sh`.
- **막히면** → [`트러블슈팅.md`](트러블슈팅.md): 증상별 매뉴얼 (`/robot_state` Publisher 0, RViz 위치, `/map` 충돌 등).
- 실 프로젝트 task 제출은 CLI 가 아니라 `service`/`app`(미구현). 진짜 배달 task(+팔 `perform_action`)는 **M4** (`libi_rmf_tasks`).

## 로봇 / 참고 자산
- 연습 로봇 URDF: `/home/asd/pinky_pro` (`pinky_description`). RMF은 footprint 반경만 fleet config에.
- `/home/asd/personal_repo/pingdergarten` — **폴더 컨벤션 원본** (controller/service/app/db 최상위 분리)
- `/home/asd/pinky_rmf/rmf_ws/src/rosconkr_rmf/rosconkr_pinky_fleet_adapter` — **실제 pinky RMF fleet adapter 예제** (M2~M5 코드 참고)
- `/home/asd/open-rmf-test` — 이전 RMF 학습 (rmf_demos 패턴·building_map_generator 명령)
- `/home/asd/personal_repo/pgm_to_gazebo` — pgm → world.sdf 변환기 (M1)
