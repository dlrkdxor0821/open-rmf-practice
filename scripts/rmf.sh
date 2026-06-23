#!/usr/bin/env bash
# rmf.sh — RMF 코어 + libi fleet adapter 띄우기 (M2~M3 의 "터미널2").
#   = rmf_traffic_schedule + blockade + building_map_server + dispatcher + fleet_adapter/manager
#
#   순서:  먼저 sim →  그다음 이거
#     1) MODE=slotcar scripts/libi_sim.sh     # sim (gz + slotcar + rviz)
#     2) scripts/rmf.sh                        # ← 이 스크립트 (RMF 코어 + 어댑터)
#     3) (online 후) scripts/ 또는 dispatch_go_to_place 로 task
#
#   포그라운드 실행 (Ctrl-c 로 종료). 맵 경로(building.yaml/navgraph)는 자동 계산.
#   추가 launch 인자는 그대로 전달됨:  scripts/rmf.sh use_sim_time:=false
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ROS_SETUP="/opt/ros/jazzy/setup.bash"
WS_SETUP="$REPO_ROOT/install/setup.bash"
MAP_DIR="$REPO_ROOT/fleet/src/libi_rmf_maps/maps/library"
BUILDING="$MAP_DIR/new_map.building.yaml"
NAVGRAPH="$MAP_DIR/new_map.navgraph.yaml"

[[ -f "$ROS_SETUP" ]] || { echo "[rmf] ROS Jazzy 없음 ($ROS_SETUP)" >&2; exit 1; }
[[ -f "$WS_SETUP" ]]  || { echo "[rmf] 빌드 산출물 없음 ($WS_SETUP) — 루트에서 colcon build 먼저" >&2; exit 1; }
for f in "$BUILDING" "$NAVGRAPH"; do
  [[ -f "$f" ]] || { echo "[rmf] 파일 없음: $f  (navgraph 면 make_navgraph.sh 로 생성)" >&2; exit 1; }
done

set +u   # ROS setup.bash 가 미정의 변수(AMENT_TRACE_SETUP_FILES 등) 참조 → nounset 잠시 해제
source "$ROS_SETUP"
source "$WS_SETUP"
set -u

echo "[rmf] RMF 코어 + 어댑터 시작 (종료: Ctrl-c)."
echo "[rmf] ※ slotcar sim 이 '먼저' 떠 있어야 로봇이 /map 받아 online 됨 (안 그러면 /robot_state Publisher 0)."
exec ros2 launch libi_rmf_bringup libi_rmf.launch.xml \
  building_yaml:="$BUILDING" \
  nav_graph_file:="$NAVGRAPH" \
  use_sim_time:=true \
  "$@"
