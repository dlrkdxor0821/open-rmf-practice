import os
from os import environ

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, Shutdown
from launch.substitutions import LaunchConfiguration, Command, TextSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from ament_index_python.packages import get_package_share_directory
from launch.substitutions import PathJoinSubstitution, PythonExpression

def generate_launch_description():
    ld = LaunchDescription()

    namespace_arg = DeclareLaunchArgument("namespace", default_value="")
    is_sim = DeclareLaunchArgument("is_sim", default_value="false")
    cam_tilt_deg = DeclareLaunchArgument("cam_tilt_deg", default_value="0")
    # 로봇 모델 xacro 선택: diff-drive(기본) vs slotcar 변형. (share 디렉터리 기준 상대경로)
    description_file = DeclareLaunchArgument(
        "description_file", default_value="urdf/robot.urdf.xacro")

    namespace = PythonExpression([
        "'", LaunchConfiguration('namespace'), "' + ('/' if '", LaunchConfiguration('namespace'), "' != '' else '')"
    ])

    rsp_node = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        namespace=LaunchConfiguration('namespace'),
        parameters=[{
            'ignore_timestamp': False,
            "use_sim_time": LaunchConfiguration('is_sim'),
            'robot_description': ParameterValue(
                Command([
                    'xacro ',
                    PathJoinSubstitution([
                        get_package_share_directory('pinky_description'),
                        LaunchConfiguration('description_file'),
                    ]),
                    ' namespace:=', namespace,
                    ' is_sim:=', LaunchConfiguration('is_sim'),
                    ' cam_tilt_deg:=', LaunchConfiguration('cam_tilt_deg')
                ]), value_type=str),
            'frame_prefix': [namespace],
        }]
    )

    jsp_node = Node(
        package='joint_state_publisher',
        executable='joint_state_publisher',
        name='joint_state_publisher',
        namespace=LaunchConfiguration('namespace'),
        parameters=[{
            "source_list": ['joint_states'],
            "rate": 20.0,
            "use_sim_time": LaunchConfiguration('is_sim'),
        }],
        remappings=[
            ('/robot_descrption', 'robot_descrpition'),
        ],
        output='screen'
    )

    ld.add_action(namespace_arg)
    ld.add_action(is_sim)
    ld.add_action(cam_tilt_deg)
    ld.add_action(description_file)
    ld.add_action(rsp_node)
    ld.add_action(jsp_node)

    return ld