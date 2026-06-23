# libi_rmf_fleet_adapter ─ ② RMF ↔ 로봇 통역 ★핵심 (M2~)

- **빌드타입**: `ament_python` / **Python** — open-rmf `rmf_demos_fleet_adapter`(EasyFullControl) **직역 포팅**.
  C++ 정본화는 **실 프로젝트 때** (지금은 공부 목적 → Python이 그때 C++의 작동 명세가 됨).
- **역할**: RMF의 이동 명령을 로봇이 알아듣는 형태로 통역. **이 연습의 핵심 학습 지점.**

## 구성 (rmf_demos_fleet_adapter 직역 — 패키지명/config 경로만 변경)
```
libi_rmf_fleet_adapter/
  fleet_adapter.py    ← ① EasyFullControl 메인. config+navgraph 읽어 add_easy_fleet, navigate/stop/action 콜백
  RobotClientAPI.py   ← ② 로봇 API HTTP 다리 (백엔드 교체 지점 ★ — M5에 nav2로)
  fleet_manager.py    ← ③ slotcar 백엔드. /robot_path_requests(PathRequest) 발행 + /robot_state 구독
  manage_lane.py      ← 차선 open/close 헬퍼
config/  libi_fleet_config.yaml   ← name/limits/footprint/battery/task_capabilities (RMF이 읽음)
launch/  fleet_adapter.launch.xml ← fleet_manager + fleet_adapter 동시 실행 (config_file, nav_graph_file 인자)
package.xml / setup.py            ← ament_python
```
실행 노드: `fleet_adapter`, `fleet_manager`, `manage_lane`.

## slotcar(M2~M4) vs nav2(M5) — 백엔드만 바뀐다
| | M2~M4 (slotcar) | M5 (실 nav2) |
|---|---|---|
| `RobotClientAPI`/`fleet_manager` 백엔드 | **slotcar 토픽** (PathRequest/robot_state) | **nav2 `NavigateToPose`** 액션 |
| 위치 피드백 | slotcar `/robot_state` | `/amcl_pose`, `/tf` |
| nav2 필요? | ❌ | ✅ |

> M2→M5의 본질 = **②③ 백엔드를 slotcar 토픽 → nav2로 교체.** ①(fleet_adapter)·config·navgraph는 재사용.

## 참고
- 원본: `rmf_demos_fleet_adapter` (open-rmf, Python EasyFullControl). 좌표/설정만 libi로 바꿔 직역.
- 실 pinky+nav2 C++ 예제: rosconkr `rosconkr_pinky_fleet_adapter` (M5/C++ 정본화 때 1순위 참고).
- ⚠️ M5 함정: action을 도메인 경계로 안 넘기려면 이 adapter를 로봇 도메인 쪽에서 실행 (docs/study-plan.md §6).
