"""M2 시뮬 RViz 뷰 — 맵 + navgraph + 로봇(pinky)을 map 프레임에 함께 띄운다.

`libi_sim.sh` 의 RViz 패널이 호출한다 (Gazebo 패널과 짝).
M1 헬퍼인 view_map.launch.py 는 dst 좌표 읽기 전용이라 건드리지 않고, M2용으로 분리했다.

구성:
- map_server      : new_map.yaml 점유격자를 /map (frame=map, latched) 로 발행
- map→odom static : gz diff-drive 가 발행하는 odom→base_footprint 를 map 프레임에 고정.
                    world≡map 이고 로봇이 world(0,0) 에 스폰되므로 identity 면 로봇이 맵 위 제자리.
- show_navgraph.py: navgraph lane·vertex 마커 (/navgraph_markers, frame=map)
- rviz2           : sim_view.rviz (Map + Navgraph + RobotModel + TF, fixed=map)

사용:
    ros2 launch scripts/rmf/sim_view.launch.py \
        map:=fleet/src/libi_rmf_maps/maps/library/new_map.yaml \
        navgraph:=fleet/src/libi_rmf_maps/maps/library/new_map.navgraph.yaml
"""
import os

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration, PythonExpression
from launch_ros.actions import Node

HERE = os.path.dirname(os.path.abspath(__file__))


def generate_launch_description():
    map_yaml = LaunchConfiguration("map")
    navgraph = LaunchConfiguration("navgraph")
    use_sim_time = LaunchConfiguration("use_sim_time")
    slotcar_tf = LaunchConfiguration("slotcar_tf")
    return LaunchDescription([
        DeclareLaunchArgument(
            "map", description="nav2 map yaml (예: .../library/new_map.yaml)"),
        DeclareLaunchArgument(
            "navgraph", default_value="",
            description="navgraph yaml (선택) — 주면 lane·vertex 를 rviz 마커로 표시"),
        DeclareLaunchArgument(
            "use_sim_time", default_value="true",
            description="Gazebo /clock 사용 (시뮬이면 true)"),
        DeclareLaunchArgument(
            "slotcar_tf", default_value="false",
            description="slotcar 모드: /robot_state→map→base_footprint TF 발행 "
                        "(diff-drive 는 DiffDrive 가 odom→base 를 내므로 false)"),

        # 점유격자 맵 (frame=map, latched).
        # /map 은 RMF building_map_server(BuildingMap)가 쓰므로 평면도는 /floorplan_map 으로 remap
        # (안 그러면 /map 에 OccupancyGrid vs BuildingMap 타입 충돌 → rviz 평면도 안 뜨고 slotcar 레벨인식 깨짐)
        Node(
            package="nav2_map_server", executable="map_server", name="map_server",
            output="screen",
            parameters=[{"yaml_filename": map_yaml, "use_sim_time": use_sim_time}],
            remappings=[("map", "floorplan_map")],
        ),
        Node(
            package="nav2_lifecycle_manager", executable="lifecycle_manager",
            name="lifecycle_manager_sim_view", output="screen",
            parameters=[{"autostart": True,
                         "node_names": ["map_server"],
                         "use_sim_time": use_sim_time}],
        ),

        # map→odom (identity): world≡map + 로봇 world(0,0) 스폰 → 로봇이 맵 위 제자리에
        Node(
            package="tf2_ros", executable="static_transform_publisher",
            name="map_to_odom_static",
            arguments=["--x", "0", "--y", "0", "--z", "0",
                       "--roll", "0", "--pitch", "0", "--yaw", "0",
                       "--frame-id", "map", "--child-frame-id", "odom"],
            parameters=[{"use_sim_time": use_sim_time}],
        ),

        # rviz (Map + Navgraph + RobotModel + TF)
        Node(
            package="rviz2", executable="rviz2", name="rviz2",
            arguments=["-d", os.path.join(HERE, "sim_view.rviz")],
            parameters=[{"use_sim_time": use_sim_time}],
            output="log",
        ),

        # navgraph 마커 (navgraph:= 가 주어지면)
        ExecuteProcess(
            cmd=["python3", os.path.join(HERE, "show_navgraph.py"), navgraph],
            output="screen",
            condition=IfCondition(PythonExpression(["'", navgraph, "' != ''"])),
        ),

        # slotcar 모드 TF: gz 가 발행하는 world→pinky1/base_link (로봇 실제 pose, 항상 나옴) 를
        # map/RobotModel 체인에 연결. /robot_state(레벨판정)에 의존 안 함 → 안정적.
        #   diff-drive 는 DiffDrive 가 odom→base 를 내므로 끄고(false), slotcar 만 켠다(true).
        #   - map ≡ world  (pgm_to_gazebo 월드 프레임 = 맵 프레임)
        #   - pinky1/base_link → base_footprint(URDF 루트) 연결 (z 2.8cm 오프셋은 top-down 에 무시→identity)
        #   * 참고: parameter_bridge 가 gz /tf 를 ROS /tf 로 브리지해야 world→pinky1/base_link 가 들어옴.
        Node(
            package="tf2_ros", executable="static_transform_publisher",
            name="map_to_world_static",
            arguments=["--frame-id", "map", "--child-frame-id", "world"],
            parameters=[{"use_sim_time": use_sim_time}],
            condition=IfCondition(slotcar_tf),
        ),
        Node(
            package="tf2_ros", executable="static_transform_publisher",
            name="gzbaselink_to_footprint_static",
            arguments=["--frame-id", "pinky1/base_link", "--child-frame-id", "base_footprint"],
            parameters=[{"use_sim_time": use_sim_time}],
            condition=IfCondition(slotcar_tf),
        ),
    ])
