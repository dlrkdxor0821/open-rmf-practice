#!/usr/bin/env bash
# set_initial_pose.sh — nav2 AMCL 을 charger 위치로 강제 localize (M5b).
#
# 왜: nav2_params 의 set_initial_pose(=charger)가 타이밍상 안 먹을 때가 있다
#     (AMCL 활성화 시 gz odom 미준비 등) → robot 이 map [0,0] 에 떠 RMF 가 위치 오인식.
# 해결: rviz '2D Pose Estimate' 와 동일하게 /initialpose 를 직접 발행해 강제 localize.
#       AMCL 이 막 떴을 때를 놓치지 않도록 몇 번 반복 발행한다.
#
# 사용:  scripts/rmf/set_initial_pose.sh                 # 기본 = pinky1_charger
#        scripts/rmf/set_initial_pose.sh <x> <y> <yaw>   # 다른 위치
#   (터미널1 sim+nav2 가 뜨고 AMCL active 된 뒤 실행. libi_sim MODE=nav2 가 자동 호출도 함.)
set +u
source /opt/ros/jazzy/setup.bash

X="${1:--3.8755598845584585}"   # pinky1_charger world/map 좌표 (libi_sim MODE=nav2 SPAWN 과 일치)
Y="${2:-11.209431044558912}"
YAW="${3:-0.0}"
N="${INITPOSE_TRIES:-4}"        # 반복 횟수 (AMCL 늦게 떠도 잡게)

# yaw → quaternion (z, w)
QZ=$(python3 -c "import math;print(math.sin($YAW/2))")
QW=$(python3 -c "import math;print(math.cos($YAW/2))")

echo "[set_initial_pose] AMCL 초기위치 → ($X, $Y, yaw=$YAW) ${N}회 발행"
for i in $(seq 1 "$N"); do
  ros2 topic pub -1 /initialpose geometry_msgs/msg/PoseWithCovarianceStamped \
"{header: {frame_id: 'map'}, pose: {pose: {position: {x: $X, y: $Y, z: 0.0}, orientation: {x: 0.0, y: 0.0, z: $QZ, w: $QW}}, covariance: [0.25, 0, 0, 0, 0, 0, 0, 0.25, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0.0685]}}" \
    >/dev/null 2>&1
  echo "  ($i/$N) 발행"
  sleep 3
done
echo "[set_initial_pose] 완료 — rviz 에서 로봇이 charger 로 점프 + 레이저 정렬됐는지 확인."
echo "  검증:  ros2 run tf2_ros tf2_echo map base_footprint   → ~($X, $Y) 나와야 함"
