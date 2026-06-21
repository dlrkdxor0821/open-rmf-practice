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

## colcon 워크스페이스 (2개)
- `controller/libi-drive-controller/` · `controller/libi-handy-controller/` · `fleet/` 가 **각각 독립 colcon ws**.
- 각 ws 안에서 `source /opt/ros/jazzy/setup.bash && colcon build`. RMF은 `fleet/` 에서 빌드.
- 비-ROS Python(`service`/`app`/`web`)은 colcon이 안 건드림 → 루트 `pyproject.toml` 로 관리 (노트 4-3).

## 로봇 / 참고 자산
- 연습 로봇 URDF: `/home/asd/pinky_pro` (`pinky_description`). RMF은 footprint 반경만 fleet config에.
- `/home/asd/personal_repo/pingdergarten` — **폴더 컨벤션 원본** (controller/service/app/db 최상위 분리)
- `/home/asd/pinky_rmf/rmf_ws/src/rosconkr_rmf/rosconkr_pinky_fleet_adapter` — **실제 pinky RMF fleet adapter 예제** (M2~M5 코드 참고)
- `/home/asd/open-rmf-test` — 이전 RMF 학습 (rmf_demos 패턴·building_map_generator 명령)
- `/home/asd/personal_repo/pgm_to_gazebo` — pgm → world.sdf 변환기 (M1)
