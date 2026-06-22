#!/usr/bin/env bash
# libi_sim.sh — M2 시뮬 환경(Gazebo + RViz)을 tmux 세션에 "창(window)별"로 띄운다.
#
# pingdergarten device-*.sh 컨벤션: 화면 분할(pane) 대신 window 탭을 쓴다.
#   - 프로세스마다 자기 window(탭) 하나 = 각자 전체화면. Ctrl-b n/p/숫자 로 전환.
#   - remain-on-exit on → 프로세스가 죽어도 창은 사라지지 않고 유지(에러 확인 가능, "창개수 유지").
#
#   scripts/libi_sim.sh           # up    : 세션 시작 후 attach (이미 떠있으면 attach)
#   scripts/libi_sim.sh down      # down  : tmux 세션 + 잔여 가제보·브리지 프로세스 정리
#   scripts/libi_sim.sh status    # status: 세션/윈도우 상태
#
# 윈도우(탭):
#   gazebo : pinky_gz_sim launch_sim, new_map world, pinky @ world(0,0)
#   rviz   : sim_view.launch.py (map + navgraph + RobotModel, fixed=map)
#
# 단축키(tmux): Ctrl-b n(다음 창) / p(이전) / 0·1(번호) / d(detach, 세션 유지) / 각 창 Ctrl-c(노드 종료)
set -euo pipefail

SESSION="libi_sim"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ACTION="${1:-up}"

ROS_SETUP="/opt/ros/jazzy/setup.bash"
WS_SETUP="$REPO_ROOT/install/setup.bash"

MAP_DIR="$REPO_ROOT/fleet/src/libi_rmf_maps/maps/library"
MAP="$MAP_DIR/new_map.yaml"
NAVGRAPH="$MAP_DIR/new_map.navgraph.yaml"
WORLD="new_map.sdf"

# down 에서 정리할 잔여 프로세스 패턴.
# gz sim 의 server/gui 자식은 tmux SIGHUP 으로 회수되지 않아 명시 정리한다.
# (스크립트로 실행되므로 부모 argv 에 패턴 문자열이 없어 자기-매칭 위험 없음)
CLEANUP_PATTERNS=(
  "ros2 launch pinky_gz_sim launch_sim"
  "sim_view.launch.py"
  "gz sim"
  "ruby .*gz sim"
  "parameter_bridge"
  "ros_gz_image"
  "robot_state_publisher"
  "joint_state_publisher"
  "show_navgraph.py"
  "static_transform_publisher"
  "nav2_map_server"
  "lifecycle_manager"
)

command -v tmux >/dev/null || { echo "[libi_sim] tmux 미설치 (sudo apt install tmux)" >&2; exit 1; }

case "$ACTION" in
  up|"")
    # 이미 세션이 있으면: gazebo 창이 죽어있으면 정리 후 재시작, 살아있으면 attach
    if tmux has-session -t "$SESSION" 2>/dev/null; then
      _dead=$(tmux list-panes -t "$SESSION:gazebo" -F '#{pane_dead}' 2>/dev/null | head -1)
      if [[ "$_dead" == "1" ]]; then
        echo "[libi_sim] 이전 세션의 창이 죽어있음 — 정리 후 재시작"
        tmux kill-session -t "$SESSION"
      else
        echo "[libi_sim] 이미 실행 중 — attach (종료: $0 down)"
        exec tmux attach -t "$SESSION"
      fi
    fi

    # 사전 점검
    [[ -f "$ROS_SETUP" ]] || { echo "[libi_sim] ROS Jazzy 없음 ($ROS_SETUP)" >&2; exit 1; }
    if [[ ! -f "$WS_SETUP" ]]; then
      echo "[libi_sim] 빌드 산출물 없음: $WS_SETUP" >&2
      echo "           cd $REPO_ROOT && source $ROS_SETUP && colcon build --symlink-install" >&2
      exit 1
    fi
    for f in "$MAP" "$NAVGRAPH"; do
      [[ -f "$f" ]] || { echo "[libi_sim] 파일 없음: $f" >&2; exit 1; }
    done

    SOURCE_ENV="source $ROS_SETUP && source $WS_SETUP && cd $REPO_ROOT"

    # window 0: gazebo
    # tmux 3.4 의 idle 세션 즉시종료 회피: sleep 으로 먼저 띄우고 remain-on-exit 설정 후 respawn.
    tmux new-session -d -s "$SESSION" -x 220 -y 50 -n gazebo -c "$REPO_ROOT" "sleep infinity"
    tmux set-option -t "$SESSION" -g remain-on-exit on
    tmux respawn-pane -k -t "$SESSION:gazebo" -c "$REPO_ROOT" \
      "$SOURCE_ENV && exec ros2 launch pinky_gz_sim launch_sim.launch.xml world_name:=$WORLD"

    # window 1: rviz (map + navgraph + RobotModel)
    tmux new-window -t "$SESSION" -n rviz -c "$REPO_ROOT" \
      "$SOURCE_ENV && exec ros2 launch $SCRIPT_DIR/rmf/sim_view.launch.py map:=$MAP navgraph:=$NAVGRAPH"

    # 보기 편의: 마우스 + 상태바
    tmux set-option -t "$SESSION" -g mouse on
    tmux set-option -t "$SESSION" -g status-style 'bg=colour235,fg=colour250'
    tmux set-option -t "$SESSION" -g window-status-current-style 'bg=colour33,fg=white,bold'
    tmux set-option -t "$SESSION" -g window-status-format ' #I:#W '
    tmux set-option -t "$SESSION" -g window-status-current-format ' #I:#W '

    tmux select-window -t "$SESSION:gazebo"
    echo "[libi_sim] 시작 — 창(탭): 0:gazebo | 1:rviz.  전환 Ctrl-b n/p, detach Ctrl-b d, 종료 $0 down"
    exec tmux attach -t "$SESSION"
    ;;

  down)
    if tmux has-session -t "$SESSION" 2>/dev/null; then
      tmux kill-session -t "$SESSION"
      echo "[libi_sim] 세션 '$SESSION' 종료"
    else
      echo "[libi_sim] 실행 중인 세션 없음"
    fi
    # SIGHUP 으로 안 죽는 gz/bridge 잔여 정리: TERM → (0.5s) → KILL
    for p in "${CLEANUP_PATTERNS[@]}"; do pkill -TERM -f "$p" 2>/dev/null || true; done
    sleep 0.5
    for p in "${CLEANUP_PATTERNS[@]}"; do pkill -KILL -f "$p" 2>/dev/null || true; done
    echo "[libi_sim] 잔여 가제보·브리지 프로세스 정리 완료"
    ;;

  status)
    if tmux has-session -t "$SESSION" 2>/dev/null; then
      echo "[libi_sim] '$SESSION' 실행 중 — 윈도우:"
      tmux list-windows -t "$SESSION"
    else
      echo "[libi_sim] '$SESSION' 없음"
    fi
    ;;

  *)
    echo "usage: $0 [up|down|status]" >&2
    exit 2
    ;;
esac
