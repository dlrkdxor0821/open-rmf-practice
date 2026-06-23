#!/usr/bin/env bash
# libi_kill.sh — open-rmf-practice 의 모든 sim/RMF 프로세스를 강제 종료(KILL)한다. clean slate.
#
#   scripts/libi_kill.sh          # 전부 종료 + tmux 'libi_sim' 세션 정리 + 잔여 개수 출력
#   scripts/libi_kill.sh list     # 종료 안 하고 현재 떠있는 것만 표시
#
# 언제 쓰나: headless 테스트/중복 실행으로 gz 서버·RMF 노드가 좀비로 남아 렉·토픽충돌(여러 /clock·/map) 날 때.
# (libi_sim.sh down 은 sim 만 정리하고 RMF 코어/어댑터 노드는 안 죽인다 — 이 스크립트가 전부 죽인다.)
#
# 자기-kill 회피: 패턴은 이 파일 "안"에 있고 실행 시 argv 는 'bash .../libi_kill.sh' 뿐이라
#                pkill -f <패턴> 이 자기 자신을 매칭하지 않는다.
set -u

PATTERNS=(
  # --- Gazebo / ros_gz ---
  'gz sim' 'gz_sim.launch' 'ros_gz_sim' 'ros_gz_bridge' 'parameter_bridge' 'ros_gz_image' 'image_bridge'
  'launch_sim.launch'
  # --- RMF core ---
  'rmf_traffic_schedule' 'rmf_traffic_blockade' 'rmf_task_dispatcher'
  'building_map_server' 'rmf_building_map_tools'
  # --- libi adapter / bringup ---
  'libi_rmf' 'fleet_adapter' 'fleet_manager'
  # --- robot description / sim view / rviz ---
  'upload_robot.launch' 'robot_state_publisher' 'joint_state_publisher'
  'sim_view.launch' 'show_navgraph' 'nav2_map_server' 'map_server' 'lifecycle_manager' 'rviz2'
)

if [[ "${1:-}" == "list" ]]; then
  echo "[libi_kill] 현재 떠있는 sim/RMF 프로세스:"
  for p in "${PATTERNS[@]}"; do pgrep -af "$p" 2>/dev/null; done | sort -un
  exit 0
fi

# tmux 세션 정리
tmux kill-session -t libi_sim 2>/dev/null && echo "[libi_kill] tmux 'libi_sim' 세션 종료" || true

# 강제 종료 (KILL)
for p in "${PATTERNS[@]}"; do pkill -KILL -f "$p" 2>/dev/null; done
pkill -KILL -x gz 2>/dev/null
pkill -KILL -f 'ruby .*gz sim' 2>/dev/null

echo "[libi_kill] 정리 후 잔여 개수 (전부 0 이어야):"
for p in 'gz sim' 'building_map_server' 'fleet_adapter' 'fleet_manager' \
         'rmf_traffic_schedule' 'parameter_bridge' 'robot_state_publisher' 'rmf_task_dispatcher' 'rviz2'; do
  printf '  %-26s : %s\n' "$p" "$(pgrep -fc "$p" 2>/dev/null)"
done
echo "[libi_kill] 완료."
