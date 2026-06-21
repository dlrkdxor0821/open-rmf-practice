# libi_rmf_tasks  ─ ④ 태스크 + 팔 perform_action 훅 (M4)

- **빌드타입**: `ament_python` · **위치**: `fleet/src/libi_rmf_tasks`
- **rmf_demos 대응**: `rmf_demos_tasks`
- **역할**: 태스크 디스패치 스크립트 + **팔(상/하차)을 `perform_action`으로 트리거하는 훅**.

## 들어갈 것
```
libi_rmf_tasks/
  dispatch_delivery.py   ← 배달 태스크 디스패치 (rmf_demos_tasks 패턴)
  dispatch_patrol.py     ← 순찰
  action_hooks.py        ← perform_action 핸들러 (팔 상/하차 트리거)
setup.py / package.xml   ← (예정)
```

## 팔 상차를 "했다 치고" (학습 목표)
- RMF 태스크가 픽업 지점 도착 → **`perform_action`** 발동 → `action_hooks.py`가
  팔에 신호(또는 가짜 신호)를 보내고 "상차 완료"를 RMF에 보고 → 다음 단계 진행.
- 학습 단계에선 실제 팔(`controller/libi-handy-controller`) 대신 **가짜 신호 + 지연 후 완료**로 대체 가능.
- 핵심: RMF는 팔 코드에 **의존하지 않고** perform_action으로 호출만 한다 (노트 4-1).

## 디스패치 예 (참고 — open-rmf-test/README 3장)
```bash
ros2 run rmf_demos_tasks dispatch_delivery -p pantry -ph coke_dispenser -d hardware_2 -dh coke_ingestor
ros2 run rmf_demos_tasks dispatch_patrol   -p pantry hardware_2 -n 3
```
