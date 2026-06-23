#!/usr/bin/env python3
"""libi 배달 task dispatch — go(shelf) → perform_action(pickup) → go(desk) → perform_action(dropoff).

M4: RMF compose task 로 "책 집기(팔) + 이동 + 내려놓기(팔)" 를 한 task 로 묶어 던진다.
slotcar 단계에선 팔(perform_action)이 fleet_adapter 의 execute_action 에서 mock(로그+딜레이)으로 실행됨.
실물/M5 엔 어댑터 쪽 mock 만 MoveIt 으로 교체 — 이 dispatch 와 task 구조는 그대로 재사용.

사용:
  ros2 run libi_rmf_tasks dispatch_delivery -F libi -R pinky1 \
       --shelf point_a --desk point_b --book book_42 --use_sim_time
"""
import argparse
import asyncio
import json
import sys
import uuid

import rclpy
from rclpy.node import Node
from rclpy.parameter import Parameter
from rclpy.qos import QoSDurabilityPolicy as Durability
from rclpy.qos import QoSHistoryPolicy as History
from rclpy.qos import QoSProfile
from rclpy.qos import QoSReliabilityPolicy as Reliability
from rmf_task_msgs.msg import ApiRequest
from rmf_task_msgs.msg import ApiResponse


class DeliveryRequester(Node):
    def __init__(self, argv=sys.argv):
        super().__init__('libi_delivery_requester')
        p = argparse.ArgumentParser()
        p.add_argument('-F', '--fleet', type=str, help='Fleet name (예: libi)')
        p.add_argument('-R', '--robot', type=str,
                       help='Robot name (지정하면 그 로봇에 직접, 안 하면 경매)')
        p.add_argument('--shelf', required=True, type=str,
                       help='책 집을 위치(navgraph waypoint)')
        p.add_argument('--desk', required=True, type=str,
                       help='책 내려놓을 위치(navgraph waypoint)')
        p.add_argument('--book', default='book', type=str,
                       help='책 라벨 (로그/실물 팔 동작에 사용)')
        p.add_argument('-st', '--start_time', type=int, default=0,
                       help='지금부터 시작까지 초, 기본 0')
        p.add_argument('--use_sim_time', action='store_true')
        p.add_argument('--requester', type=str, default='libi_rmf_tasks')
        self.args = p.parse_args(argv[1:])
        self.response = asyncio.Future()

        qos = QoSProfile(history=History.KEEP_LAST, depth=1,
                         reliability=Reliability.RELIABLE,
                         durability=Durability.TRANSIENT_LOCAL)
        self.pub = self.create_publisher(ApiRequest, 'task_api_requests', qos)

        if self.args.use_sim_time:
            self.get_logger().info('Using Sim Time')
            self.set_parameters(
                [Parameter('use_sim_time', Parameter.Type.BOOL, True)])

        # ---- payload (robot 지정이면 직접, 아니면 경매) ----
        msg = ApiRequest()
        msg.request_id = 'libi_delivery_' + str(uuid.uuid4())
        payload = {}
        if self.args.fleet and self.args.robot:
            payload['type'] = 'robot_task_request'
            payload['robot'] = self.args.robot
            payload['fleet'] = self.args.fleet
        else:
            payload['type'] = 'dispatch_task_request'

        now = self.get_clock().now().to_msg()
        now.sec = now.sec + self.args.start_time
        start_ms = now.sec * 1000 + round(now.nanosec / 10**6)

        # ---- 배달 시퀀스: go → pickup → go → dropoff ----
        def go(waypoint):
            return {'category': 'go_to_place',
                    'description': {'one_of': [{'waypoint': waypoint}]}}

        def arm(action):
            return {'category': 'perform_action',
                    'description': {
                        'unix_millis_action_duration_estimate': 3000,
                        'category': action,            # pickup | dropoff (어댑터가 분기)
                        'description': {'label': self.args.book},
                    }}

        activities = [
            go(self.args.shelf),
            arm('pickup'),
            go(self.args.desk),
            arm('dropoff'),
        ]

        request = {
            'unix_millis_request_time': start_ms,
            'unix_millis_earliest_start_time': start_ms,
            'requester': self.args.requester,
            'category': 'compose',
            'description': {
                'category': 'delivery',
                'phases': [{
                    'activity': {
                        'category': 'sequence',
                        'description': {'activities': activities},
                    }
                }],
            },
        }
        if self.args.fleet:
            request['fleet_name'] = self.args.fleet
        payload['request'] = request
        msg.json_msg = json.dumps(payload)

        def on_response(r: ApiResponse):
            if r.request_id == msg.request_id:
                self.response.set_result(json.loads(r.json_msg))
        self.sub = self.create_subscription(
            ApiResponse, 'task_api_responses', on_response, 10)

        print('배달 task 전송:\n'
              f'{json.dumps(payload, indent=2, ensure_ascii=False)}')
        self.pub.publish(msg)


def main(argv=sys.argv):
    rclpy.init(args=sys.argv)
    args = rclpy.utilities.remove_ros_args(sys.argv)
    node = DeliveryRequester(args)
    rclpy.spin_until_future_complete(node, node.response, timeout_sec=5.0)
    if node.response.done():
        print(f'응답:\n{node.response.result()}')
    else:
        print('응답 없음 — RMF 코어/어댑터(scripts/rmf.sh)가 떠있는지 확인.')
    rclpy.shutdown()


if __name__ == '__main__':
    main(sys.argv)
