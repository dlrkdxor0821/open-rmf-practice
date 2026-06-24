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

# 로봇 구동 모드 토글:
#   diffdrive(기본, cmd_vel 주행) | slotcar(RMF 직접 구동, M2~4) | nav2(diffdrive+nav2 실주행, M5a)
#   사용:  MODE=slotcar scripts/libi_sim.sh   /   MODE=nav2 scripts/libi_sim.sh
MODE="${MODE:-diffdrive}"
NAV2="false"                           # nav2 모드면 true → nav2 스택 창 + nav2 rviz (AMCL이 map→odom 담당)
RVIZ="${RVIZ:-true}"                   # OOM 대비: RVIZ=false 면 rviz 창 끔 (메모리 절약, Gazebo로만 관찰)
if [[ "$MODE" == "slotcar" ]]; then
  DESC_FILE="urdf/pinky_slotcar.urdf.xacro"
  ROBOT_NAME="pinky1"                  # config robots.pinky1 과 매칭
  SPAWN_X="-3.8755598845584585"        # pinky1_charger world 좌표 (navgraph 보정값)
  SPAWN_Y="11.209431044558912"
  GZ_SLOTCAR_PLUGIN="/opt/ros/jazzy/lib/rmf_robot_sim_gz_plugins"   # libslotcar.so 경로
  SLOTCAR_TF="true"                    # RViz robot TF 를 /robot_state 에서 발행 (slotcar엔 odom→base 없음)
  SPAWN_ROBOT2="true"; ROBOT2_NAME="pinky2"   # M3: 2번째 로봇 (traffic negotiation)
  SPAWN2_X="0.4807"; SPAWN2_Y="3.2058"        # pinky2_charger world 좌표 (반대편 끝)
elif [[ "$MODE" == "diffdrive" ]]; then
  DESC_FILE="urdf/robot.urdf.xacro"
  ROBOT_NAME="pinky"
  SPAWN_X="0.0"; SPAWN_Y="0.0"
  GZ_SLOTCAR_PLUGIN=""
  SLOTCAR_TF="false"
  SPAWN_ROBOT2="false"; ROBOT2_NAME="pinky2"; SPAWN2_X="0.0"; SPAWN2_Y="0.0"
elif [[ "$MODE" == "nav2" ]]; then
  # M5a: diffdrive pinky + nav2 실주행 (RMF 없음). nav2 AMCL이 map→odom 담당 → 정적 TF 안 씀.
  DESC_FILE="urdf/robot.urdf.xacro"
  ROBOT_NAME="pinky"
  SPAWN_X="-3.8755598845584585"        # pinky1_charger(free 위치) — rviz 초기위치(2D Pose Estimate)도 여기로
  SPAWN_Y="11.209431044558912"
  GZ_SLOTCAR_PLUGIN=""
  SLOTCAR_TF="false"
  SPAWN_ROBOT2="false"; ROBOT2_NAME="pinky2"; SPAWN2_X="0.0"; SPAWN2_Y="0.0"
  NAV2="true"
else
  echo "[libi_sim] 알 수 없는 MODE='$MODE' (diffdrive|slotcar|nav2 중 하나)" >&2; exit 2
fi

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
  "gz_bringup_launch"
  "component_container_isolated"
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
    GZ_EXPORT=""
    if [[ -n "$GZ_SLOTCAR_PLUGIN" ]]; then
      GZ_EXPORT="export GZ_SIM_SYSTEM_PLUGIN_PATH=\"$GZ_SLOTCAR_PLUGIN:\${GZ_SIM_SYSTEM_PLUGIN_PATH:-}\" && "
    fi
    tmux respawn-pane -k -t "$SESSION:gazebo" -c "$REPO_ROOT" \
      "$SOURCE_ENV && ${GZ_EXPORT}exec ros2 launch pinky_gz_sim launch_sim.launch.xml world_name:=$WORLD description_file:=$DESC_FILE robot_name:=$ROBOT_NAME spawn_x:=$SPAWN_X spawn_y:=$SPAWN_Y spawn_robot2:=$SPAWN_ROBOT2 robot2_name:=$ROBOT2_NAME spawn2_x:=$SPAWN2_X spawn2_y:=$SPAWN2_Y"

    # window 1 (nav2 모드만): nav2 스택 — map_server+amcl+planner+controller (우리 library 맵)
    #   + (백그라운드) 15s 뒤 set_initial_pose 로 AMCL 을 charger 로 강제 localize.
    #   (set_initial_pose param 이 타이밍상 안 먹으면 robot 이 map [0,0] 로 떠 RMF 가 위치 오인식 → 이걸로 방지)
    if [[ "$NAV2" == "true" ]]; then
      tmux new-window -t "$SESSION" -n nav2 -c "$REPO_ROOT" \
        "$SOURCE_ENV && { ( sleep 15 && $SCRIPT_DIR/rmf/set_initial_pose.sh ) & } && exec ros2 launch pinky_navigation gz_bringup_launch.xml map:=$MAP use_sim_time:=True"
    fi

    # window: rviz — nav2 모드면 nav2_view.rviz(코스트맵·경로·laser, map은 nav2 map_server, map→odom은 AMCL)
    #                아니면 기존 sim_view(slotcar/diffdrive: navgraph + 정적 map→odom)
    if [[ "$NAV2" == "true" && "$RVIZ" == "true" ]]; then
      NAV2_RVIZ="$REPO_ROOT/controller/libi-drive-controller/src/pinky_pro/pinky_navigation/rviz/nav2_view.rviz"
      # show_navgraph(백그라운드)로 navgraph lane·vertex 마커(/navgraph_markers) 발행 → rviz Navgraph 디스플레이가 표시
      tmux new-window -t "$SESSION" -n rviz -c "$REPO_ROOT" \
        "$SOURCE_ENV && { python3 $SCRIPT_DIR/rmf/show_navgraph.py $NAVGRAPH & } && exec ros2 run rviz2 rviz2 -d $NAV2_RVIZ --ros-args -p use_sim_time:=true"
    elif [[ "$NAV2" == "true" ]]; then
      echo "[libi_sim] RVIZ=false → rviz 생략 (메모리 절약). Gazebo 로 관찰."
    else
      tmux new-window -t "$SESSION" -n rviz -c "$REPO_ROOT" \
        "$SOURCE_ENV && exec ros2 launch $SCRIPT_DIR/rmf/sim_view.launch.py map:=$MAP navgraph:=$NAVGRAPH slotcar_tf:=$SLOTCAR_TF"
    fi

    # 보기 편의: 마우스 + 상태바
    tmux set-option -t "$SESSION" -g mouse on
    tmux set-option -t "$SESSION" -g status-style 'bg=colour235,fg=colour250'
    tmux set-option -t "$SESSION" -g window-status-current-style 'bg=colour33,fg=white,bold'
    tmux set-option -t "$SESSION" -g window-status-format ' #I:#W '
    tmux set-option -t "$SESSION" -g window-status-current-format ' #I:#W '

    tmux select-window -t "$SESSION:gazebo"
    if [[ "$NAV2" == "true" && "$RVIZ" == "true" ]]; then WINS="0:gazebo | 1:nav2 | 2:rviz"
    elif [[ "$NAV2" == "true" ]]; then WINS="0:gazebo | 1:nav2 (rviz off)"
    else WINS="0:gazebo | 1:rviz"; fi
    echo "[libi_sim] 시작 (MODE=$MODE, robot=$ROBOT_NAME) — 창(탭): $WINS.  전환 Ctrl-b n/p, detach Ctrl-b d, 종료 $0 down"
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
