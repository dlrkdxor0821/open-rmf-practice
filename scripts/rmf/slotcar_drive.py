#!/usr/bin/env python3
"""slotcar_drive.py — slotcar pinky 수동 주행 검증 도구 (M2 step2).

fleet adapter/RMF 코어 없이 slotcar 플러그인을 직접 구동한다:
  /robot_state(현재 위치) 를 읽어 path[0] 으로, 인자 (x, y) 를 path[1] 로 하는
  rmf_fleet_msgs/PathRequest 를 /robot_path_requests 에 1회 발행 → slotcar 가 그 경로를 따라간다.
발행 후 몇 초간 /robot_state 위치를 샘플링해 실제로 움직였는지(총 이동거리) 보고한다.

사용 (gz + slotcar pinky 가 떠 있는 상태에서; sim time 필수):
    python3 scripts/rmf/slotcar_drive.py 1.5 0.0 --ros-args -p use_sim_time:=true
    python3 scripts/rmf/slotcar_drive.py 0.43 9.87 --robot pinky --fleet libi --yaw 0
"""
import argparse
import math
import sys

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, DurabilityPolicy, ReliabilityPolicy
from builtin_interfaces.msg import Time
from rmf_fleet_msgs.msg import PathRequest, Location, RobotState


class SlotcarDrive(Node):
    def __init__(self, args):
        super().__init__('slotcar_drive')
        self.a = args
        self.cur = None          # 최신 현재 위치 (Location)
        self.start = None        # 발행 시점 위치
        self.sent = False
        self.samples = 0

        # /robot_path_requests: slotcar 가 구독 (reliable, volatile)
        self.pub = self.create_publisher(PathRequest, '/robot_path_requests', 10)
        self.create_subscription(RobotState, '/robot_state', self._on_state, 10)
        self.timer = self.create_timer(0.5, self._tick)
        self.get_logger().info(
            f"target=({args.x}, {args.y}) robot={args.robot} fleet={args.fleet} — /robot_state 대기...")

    def _on_state(self, msg: RobotState):
        if msg.name == self.a.robot:
            self.cur = msg.location

    def _tick(self):
        if self.cur is None:
            return
        if not self.sent:
            self._send()
            return
        # 발행 후: 이동 모니터링
        self.samples += 1
        moved = math.hypot(self.cur.x - self.start.x, self.cur.y - self.start.y)
        self.get_logger().info(
            f"  t+{self.samples*0.5:.1f}s  pos=({self.cur.x:.2f},{self.cur.y:.2f})  이동={moved:.2f}m")
        if self.samples >= 20:  # ~10s
            verdict = "✅ 움직임 확인" if moved > 0.1 else "❌ 안 움직임"
            self.get_logger().info(f"=== 결과: 총 이동 {moved:.2f}m → {verdict} ===")
            rclpy.shutdown()

    def _send(self):
        now = self.get_clock().now().to_msg()
        self.start = self.cur

        l0 = Location()
        l0.t = now
        l0.x, l0.y, l0.yaw = self.cur.x, self.cur.y, self.cur.yaw
        l0.level_name = self.a.level

        dist = math.hypot(self.a.x - self.cur.x, self.a.y - self.cur.y)
        dt = max(2.0, dist / self.a.speed)
        t1 = Time()
        t1.sec = now.sec + int(dt)
        t1.nanosec = now.nanosec

        l1 = Location()
        l1.t = t1
        l1.x, l1.y, l1.yaw = float(self.a.x), float(self.a.y), float(self.a.yaw)
        l1.level_name = self.a.level

        req = PathRequest()
        req.fleet_name = self.a.fleet
        req.robot_name = self.a.robot
        req.path = [l0, l1]
        req.task_id = 'slotcar-drive-1'
        self.pub.publish(req)
        self.sent = True
        self.get_logger().info(
            f"PathRequest 발행: ({self.cur.x:.2f},{self.cur.y:.2f}) → ({self.a.x},{self.a.y})  "
            f"거리 {dist:.2f}m, dt {dt:.1f}s")


def main():
    p = argparse.ArgumentParser(description="slotcar pinky 에 PathRequest 발행")
    p.add_argument('x', type=float, help='목표 x (map 좌표)')
    p.add_argument('y', type=float, help='목표 y (map 좌표)')
    p.add_argument('--yaw', type=float, default=0.0)
    p.add_argument('--robot', default='pinky', help='로봇(=gz 모델) 이름')
    p.add_argument('--fleet', default='libi', help='fleet 이름 (slotcar 단독 검증 시 임의)')
    p.add_argument('--level', default='L1')
    p.add_argument('--speed', type=float, default=0.3, help='경로 평균속도(m/s, dt 계산용)')
    args, _ = p.parse_known_args()  # --ros-args 등은 rclpy 로 넘김

    rclpy.init()
    node = SlotcarDrive(args)
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, SystemExit):
        pass


if __name__ == '__main__':
    main()
