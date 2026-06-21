#!/usr/bin/env python3
"""navgraph(yaml)를 rviz 마커로 띄운다 — vertex(점) + lane(선) 시각화.

사용:
    python3 show_navgraph.py /tmp/out/0_fixed.yaml
    (또는 view_map.launch.py 의 navgraph:= 인자로 자동 실행)

rviz 에서 MarkerArray 디스플레이(`/navgraph_markers`, frame=map)로 보인다.
- 노랑 선 = lane(간선), 시안 점 = vertex, 흰 글씨 = vertex 이름(있으면)
"""
import sys

import yaml
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, DurabilityPolicy
from visualization_msgs.msg import Marker, MarkerArray
from geometry_msgs.msg import Point
from std_msgs.msg import ColorRGBA


def build_markers(path):
    data = yaml.safe_load(open(path))
    markers = MarkerArray()
    mid = 0
    for lvl in (data.get("levels") or {}).values():
        verts = lvl.get("vertices", [])
        lanes = lvl.get("lanes", [])

        # lane = 노랑 선 (LINE_LIST: 점을 2개씩 짝지어 선분)
        line = Marker()
        line.header.frame_id = "map"
        line.ns = "lanes"; line.id = mid; mid += 1
        line.type = Marker.LINE_LIST; line.action = Marker.ADD
        line.scale.x = 0.05
        line.color = ColorRGBA(r=1.0, g=0.85, b=0.0, a=0.9)
        line.pose.orientation.w = 1.0
        for lane in lanes:
            for idx in (lane[0], lane[1]):
                v = verts[idx]
                line.points.append(Point(x=float(v[0]), y=float(v[1]), z=0.05))
        markers.markers.append(line)

        # vertex = 시안 점 (SPHERE_LIST)
        pts = Marker()
        pts.header.frame_id = "map"
        pts.ns = "vertices"; pts.id = mid; mid += 1
        pts.type = Marker.SPHERE_LIST; pts.action = Marker.ADD
        pts.scale.x = pts.scale.y = pts.scale.z = 0.25
        pts.color = ColorRGBA(r=0.0, g=0.9, b=1.0, a=1.0)
        pts.pose.orientation.w = 1.0
        for v in verts:
            pts.points.append(Point(x=float(v[0]), y=float(v[1]), z=0.05))
        markers.markers.append(pts)

        # vertex 이름 라벨 (있으면)
        for v in verts:
            name = v[2].get("name", "") if len(v) > 2 and isinstance(v[2], dict) else ""
            if not name:
                continue
            t = Marker()
            t.header.frame_id = "map"
            t.ns = "labels"; t.id = mid; mid += 1
            t.type = Marker.TEXT_VIEW_FACING; t.action = Marker.ADD
            t.scale.z = 0.3
            t.color = ColorRGBA(r=1.0, g=1.0, b=1.0, a=1.0)
            t.pose.position = Point(x=float(v[0]), y=float(v[1]), z=0.4)
            t.pose.orientation.w = 1.0
            t.text = name
            markers.markers.append(t)
    return markers


class ShowNavgraph(Node):
    def __init__(self, path):
        super().__init__("show_navgraph")
        qos = QoSProfile(depth=1)
        qos.durability = DurabilityPolicy.TRANSIENT_LOCAL
        self.pub = self.create_publisher(MarkerArray, "/navgraph_markers", qos)
        self.markers = build_markers(path)
        self.create_timer(2.0, self.tick)
        self.tick()
        n = sum(len(m.points) for m in self.markers.markers if m.ns == "vertices")
        self.get_logger().info(
            f"navgraph 마커 발행 ({path}): vertex {n}개. rviz MarkerArray(/navgraph_markers) 확인")

    def tick(self):
        now = self.get_clock().now().to_msg()
        for m in self.markers.markers:
            m.header.stamp = now
        self.pub.publish(self.markers)


def main():
    if len(sys.argv) < 2:
        sys.exit("사용법: show_navgraph.py <navgraph.yaml>")
    rclpy.init()
    try:
        rclpy.spin(ShowNavgraph(sys.argv[1]))
    except KeyboardInterrupt:
        pass
    finally:
        rclpy.shutdown()


if __name__ == "__main__":
    main()
