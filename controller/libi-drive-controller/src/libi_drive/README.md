# libi_drive  ─ 주행 온보드 (Drive Board)

- **위치**: `controller/libi-drive-controller/src/libi_drive` (독립 colcon ws)
- **역할**: AMR **nav2 주행 스택** (로봇 위/Drive Board에서 실행).
- **RMF와의 관계**: RMF이 **직접 지휘하는 대상**. fleet adapter가 `NavigateToPose`로 목표를 준다 (M5).
  RMF은 이 코드에 **의존하지 않고** ROS2 토픽/액션으로만 통신 → RMF 없이도 단독 동작.

> 연습에선 `/home/asd/pinky_pro` 의 URDF/nav2 자산을 재사용. URDF 변경 불필요 (RMF은 footprint만 fleet config에).
> M1~M4(slotcar)에선 nav2 미사용. nav2는 M5에서 등장 (docs/study-plan.md).
