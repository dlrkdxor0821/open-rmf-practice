"""맵을 rviz 에 실좌표(map 프레임)로 띄운다 — pairs.yaml 의 dst 좌표를 읽기 위한 헬퍼.

사용법:
    ros2 launch scripts/rmf/view_map.launch.py \
        map:=fleet/src/libi_rmf_maps/maps/library/new_map.yaml

rviz 가 뜨면 툴바의 'Publish Point' 를 누르고 맵 위를 클릭한다.
→ 클릭한 좌표가 rviz 하단 상태바에 표시되고 /clicked_point 로도 나간다.
   (터미널에서 보려면: ros2 topic echo /clicked_point)
이 좌표가 pairs.yaml 의 dst 값이다.

navgraph:= 를 주면 간선(lane)·vertex 도 마커로 함께 표시한다:
    ros2 launch scripts/rmf/view_map.launch.py \
        map:=.../new_map.yaml navgraph:=/tmp/out/0_fixed.yaml
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
    return LaunchDescription([
        DeclareLaunchArgument(
            "map", description="nav2 map yaml (예: .../library/new_map.yaml)"),
        DeclareLaunchArgument(
            "navgraph", default_value="",
            description="navgraph yaml (선택) — 주면 lane·vertex 를 rviz 마커로 표시"),
        Node(
            package="nav2_map_server", executable="map_server", name="map_server",
            output="screen",
            parameters=[{"yaml_filename": map_yaml, "use_sim_time": False}],
        ),
        Node(
            package="nav2_lifecycle_manager", executable="lifecycle_manager",
            name="lifecycle_manager_view", output="screen",
            parameters=[{"autostart": True,
                         "node_names": ["map_server"],
                         "use_sim_time": False}],
        ),
        Node(
            package="rviz2", executable="rviz2", name="rviz2",
            arguments=["-d", os.path.join(HERE, "view_map.rviz")],
            output="log",
        ),
        # navgraph:= 가 주어지면 lane·vertex 마커 발행 노드 실행
        ExecuteProcess(
            cmd=["python3", os.path.join(HERE, "show_navgraph.py"), navgraph],
            output="screen",
            condition=IfCondition(PythonExpression(["'", navgraph, "' != ''"])),
        ),
    ])
