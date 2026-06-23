#!/usr/bin/env python3
"""slotcar 모드용 TF 브리지: /robot_state(slotcar 실제 위치) → map→base_footprint TF.

왜 필요한가:
- diff-drive 모드는 gz DiffDrive 플러그인이 odom→base_footprint TF 를 발행 → sim_view 의
  map→odom(static) 과 이어져 RViz RobotModel 이 맵 프레임에 붙는다.
- slotcar 모드엔 DiffDrive 가 없어 odom→base_footprint 가 없다 → TF 트리가 map / base_footprint
  둘로 끊겨 RViz 가 로봇을 못 놓는다. slotcar 는 위치를 /robot_state 로만 보고한다.
- 이 노드가 /robot_state 의 (x, y, yaw) 로 map→base_footprint 를 직접 발행해 그 끊김을 메운다.

사용: ros2 run 이 아니라 standalone (show_navgraph.py 처럼 sim_view.launch.py 가 ExecuteProcess 로 실행).
    python3 robot_state_to_tf.py --ros-args -p use_sim_time:=true [-p robot_name:=pinky1]
"""
import math

import rclpy
from rclpy.node import Node
from rmf_fleet_msgs.msg import RobotState
from geometry_msgs.msg import TransformStamped
from tf2_ros import TransformBroadcaster


class RobotStateToTF(Node):
    def __init__(self):
        super().__init__('robot_state_to_tf')
        # robot_name='' 이면 아무 로봇이나 (단일 로봇 M2 용). 다중 로봇이면 이름 지정.
        self.robot_name = self.declare_parameter('robot_name', '').value
        self.map_frame = self.declare_parameter('map_frame', 'map').value
        self.base_frame = self.declare_parameter('base_frame', 'base_footprint').value
        self.br = TransformBroadcaster(self)
        self.create_subscription(RobotState, '/robot_state', self.cb, 10)
        self.get_logger().info(
            f'robot_state_to_tf: {self.map_frame} -> {self.base_frame} '
            f'(robot_name="{self.robot_name or "*"}")')

    def cb(self, msg: RobotState):
        if self.robot_name and msg.name != self.robot_name:
            return
        loc = msg.location
        tf = TransformStamped()
        tf.header.stamp = self.get_clock().now().to_msg()
        tf.header.frame_id = self.map_frame
        tf.child_frame_id = self.base_frame
        tf.transform.translation.x = float(loc.x)
        tf.transform.translation.y = float(loc.y)
        tf.transform.translation.z = 0.0
        yaw = float(loc.yaw)
        tf.transform.rotation.z = math.sin(yaw / 2.0)
        tf.transform.rotation.w = math.cos(yaw / 2.0)
        self.br.sendTransform(tf)


def main():
    rclpy.init()
    node = RobotStateToTF()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
