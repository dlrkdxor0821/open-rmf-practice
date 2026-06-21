# libi_rmf_bridge  ─ ③ domain_bridge (M5에서만)

- **빌드타입**: `ament_cmake` · **위치**: `fleet/src/libi_rmf_bridge`
- **역할**: 로봇 도메인 ↔ RMF 도메인을 `domain_bridge`로 연결. **M5(실 nav2)에서만 사용.**

## 들어갈 것
```
config/
  robot_to_rmf.yaml   ← 로봇→RMF: /tf, /amcl_pose(위치), map
  rmf_to_robot.yaml   ← RMF→로봇: 필요한 RMF 표준 토픽 (필요 시)
launch/
  bridge.launch.xml
```

## 토폴로지 (노트 5장 · gogoping 계승, CycloneDDS)
```
로봇1: DOMAIN 201 — nav2 풀스택        로봇2: DOMAIN 202 — nav2 풀스택
RMF:   DOMAIN 200 — 코어 + fleet adapter   ↑ domain_bridge로 필요한 것만 포워딩
```
> ROS_DOMAIN_ID는 pingdergarten 컨벤션(201~219 팀 할당)과 정렬.

> ⚠️ 함정: `domain_bridge`는 토픽/서비스는 OK지만 **action(`NavigateToPose`)** 은 까다로움.
> → **우회**: fleet adapter를 *로봇 도메인 쪽*에서 실행 → adapter↔nav2는 같은 도메인(브릿지 불필요),
> RMF↔adapter 사이의 **RMF 표준 토픽만** 브릿지. action을 도메인 경계로 안 넘긴다.
