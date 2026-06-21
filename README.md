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
│       ├── libi_rmf_fleet_adapter/      #   RMF↔nav2 통역 ★핵심            (ament_cmake/C++)
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
| `pairs.example.yaml` | 대응점(pairs) 작성 예시 |

워크플로우 (루트에서, `source /opt/ros/jazzy/setup.bash` 후):

```bash
# 1) navgraph 생성 + 좌표(src) 보기
scripts/rmf/make_navgraph.sh fleet/src/libi_rmf_maps/maps/library/new_map.building.yaml

# 2) rviz로 맵 띄워 dst 좌표 읽기 ('Publish Point' 클릭 후 맵 클릭)
ros2 launch scripts/rmf/view_map.launch.py map:=fleet/src/libi_rmf_maps/maps/library/new_map.yaml
ros2 topic echo /clicked_point        # point.x, point.y = dst (rviz 하단 상태바에도 표시)

# 3) new_map.pairs.yaml 작성 (맵 폴더에): src=1단계 출력, dst=2단계 클릭. 멀리 떨어진 2쌍+
#    pairs.example.yaml 복사해서 채움

# 4) 보정 실행
scripts/rmf/make_navgraph.sh \
  fleet/src/libi_rmf_maps/maps/library/new_map.building.yaml \
  fleet/src/libi_rmf_maps/maps/library/new_map.pairs.yaml
```

- 결과: `/tmp/out/0_fixed.yaml`. **RMS 잔차 작으면 성공**(scale 달라도 OK). navgraph 재생성 시 4단계를 다시 실행.

## 로봇 / 참고 자산
- 연습 로봇 URDF: `/home/asd/pinky_pro` (`pinky_description`). RMF은 footprint 반경만 fleet config에.
- `/home/asd/personal_repo/pingdergarten` — **폴더 컨벤션 원본** (controller/service/app/db 최상위 분리)
- `/home/asd/pinky_rmf/rmf_ws/src/rosconkr_rmf/rosconkr_pinky_fleet_adapter` — **실제 pinky RMF fleet adapter 예제** (M2~M5 코드 참고)
- `/home/asd/open-rmf-test` — 이전 RMF 학습 (rmf_demos 패턴·building_map_generator 명령)
- `/home/asd/personal_repo/pgm_to_gazebo` — pgm → world.sdf 변환기 (M1)
