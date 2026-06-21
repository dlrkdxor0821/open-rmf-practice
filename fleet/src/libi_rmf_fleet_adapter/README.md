# libi_rmf_fleet_adapter  ─ ② RMF ↔ 로봇 통역 ★핵심 (M2 → M5)

- **빌드타입**: `ament_cmake` / **C++** (노트 4-2: EasyFullControl C++ = 원본) · **위치**: `fleet/src/libi_rmf_fleet_adapter`
- **역할**: RMF의 이동 명령을 로봇이 알아듣는 형태로 통역. **이 연습의 핵심 학습 지점.**

## 🎁 결정적 참고: 실제 pinky fleet adapter 예제
`/home/asd/pinky_rmf/rmf_ws/src/rosconkr_rmf/rosconkr_pinky_fleet_adapter` (ROSCon KR) — **pinky + RMF** 실동작 어댑터.
구조·EasyFullControl 사용법·nav2 연동을 거의 그대로 참고/이식할 수 있다. **M2~M5의 1순위 레퍼런스.**

## 들어갈 것 (C++ 레이아웃)
```
src/        fleet_adapter.cpp        ← EasyFullControl 메인
            RobotClientAPI.cpp       ← 로봇 제어 추상 API (백엔드 교체 지점 ★)
            nav2_robot_api.cpp       ← (M5) nav2 NavigateToPose 송신 + amcl_pose/tf 수신
include/libi_rmf_fleet_adapter/      ← 헤더
config/     libi_fleet_config.yaml   ← footprint 반경·최고속도·배터리 (RMF이 읽음)
CMakeLists.txt / package.xml         ← (예정)
```

## slotcar(M2~M4) vs nav2(M5) — 백엔드만 바뀐다
| | M2~M4 (slotcar) | M5 (실 nav2) |
|---|---|---|
| `RobotClientAPI` 백엔드 | **slotcar 토픽** 직접 구동 | **nav2 `NavigateToPose`** 액션 |
| 위치 피드백 | 시뮬에서 직접 | `/amcl_pose`, `/tf` |
| nav2 필요? | ❌ | ✅ |

> scaffold는 그대로 유지되고, **`RobotClientAPI` 백엔드 하나만 교체**되는 게 M2→M5의 본질.

## 📚 학습 팁
- 개념은 **`rmf_demos_fleet_adapter`(Python)** + 위 **rosconkr 예제**를 먼저 읽고 돌려보면 빠르다.
- ⚠️ M5 함정: action을 도메인 경계로 안 넘기려면 이 adapter를 **로봇 도메인 쪽에서 실행** (docs/study-plan.md §6, 노트 5장).
