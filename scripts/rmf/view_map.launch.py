"""맵을 rviz 에 실좌표(map 프레임)로 띄운다 — pairs.yaml 의 dst 좌표를 읽기 위한 헬퍼.

사용법:
    ros2 launch scripts/rmf/view_map.launch.py \
        map:=fleet/src/libi_rmf_maps/maps/library/new_map.yaml

rviz 가 뜨면 툴바의 'Publish Point' 를 누르고 맵 위를 클릭한다.
→ 클릭한 좌표가 rviz 하단 상태바에 표시되고 /clicked_point 로도 나간다.
   (터미널에서 보려면: ros2 topic echo /clicked_point)
이 좌표가 pairs.yaml 의 dst 값이다.
"""
import os

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

HERE = os.path.dirname(os.path.abspath(__file__))


def generate_launch_description():
    map_yaml = LaunchConfiguration("map")
    return LaunchDescription([
        DeclareLaunchArgument(
            "map", description="nav2 map yaml (예: .../library/new_map.yaml)"),
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
    ])
