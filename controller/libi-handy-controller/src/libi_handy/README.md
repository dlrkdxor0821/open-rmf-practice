# libi_handy  ─ 팔 온보드 (Handy Board)

- **위치**: `controller/libi-handy-controller/src/libi_handy` (독립 colcon ws)
- **역할**: 매니퓰레이션(상/하차) — **MoveIt 등** (로봇 위/Handy Board에서 실행).
- **RMF와의 관계**: RMF이 직접 구동하지 않음. 태스크 도착 후 **`perform_action`** 으로 트리거됨
  (`fleet/src/libi_rmf_tasks/action_hooks.py` 가 호출).

> 학습 단계에선 실제 팔 대신 **가짜 신호("상차 완료")** 로 대체 가능 (docs/study-plan.md M4).
