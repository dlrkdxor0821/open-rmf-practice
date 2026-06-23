#!/usr/bin/env python3

# Copyright 2021 Open Source Robotics Foundation, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import argparse
import copy
import json
import math
import sys
import threading
import time
from typing import Optional

from fastapi import FastAPI
import numpy as np
from pydantic import BaseModel
from pyproj import Transformer
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_system_default
from rclpy.qos import QoSDurabilityPolicy as Durability
from rclpy.qos import QoSHistoryPolicy as History
from rclpy.qos import QoSProfile
from rclpy.qos import QoSReliabilityPolicy as Reliability
import rmf_adapter as adpt
import rmf_adapter.geometry as geometry
import rmf_adapter.vehicletraits as traits
from rmf_fleet_msgs.msg import DockSummary
from rmf_fleet_msgs.msg import Location
from rmf_fleet_msgs.msg import ModeRequest
from rmf_fleet_msgs.msg import PathRequest
from rmf_fleet_msgs.msg import RobotMode
from rmf_fleet_msgs.msg import RobotState
# --- nav2 백엔드 (M5b): slotcar PathRequest/robot_state 대신 nav2 직접 구동 ---
from rclpy.action import ActionClient
from nav2_msgs.action import NavigateToPose
from geometry_msgs.msg import PoseWithCovarianceStamped
from geometry_msgs.msg import TwistStamped
from std_msgs.msg import Float32
import tf2_ros
from rclpy.time import Time as RclpyTime
import socketio
import uvicorn
import yaml

app = FastAPI()


class Request(BaseModel):
    map_name: Optional[str] = None
    activity: Optional[str] = None
    label: Optional[str] = None
    destination: Optional[dict] = None
    data: Optional[dict] = None
    speed_limit: Optional[float] = None
    toggle: Optional[bool] = None


class Response(BaseModel):
    data: Optional[dict] = None
    success: bool
    msg: str


# ------------------------------------------------------------------------------
# Fleet Manager
# ------------------------------------------------------------------------------
class State:

    def __init__(self, state: RobotState = None, destination: Location = None):
        self.state = state
        self.destination = destination
        self.last_path_request = None
        self.last_completed_request = None
        self.mode_teleop = False
        self.svy_transformer = Transformer.from_crs('EPSG:4326', 'EPSG:3414')
        self.gps_pos = [0, 0]
        # --- nav2 백엔드 (M5b) ---
        self.position = None       # [x, y, yaw] (from /amcl_pose)
        self.battery = 1.0         # 0~1 (from /battery, 없으면 100%)
        self.map_name = 'L1'
        self.goal_handle = None    # NavigateToPose goal handle (취소용)
        self.cmd_id = None         # 진행 중 cmd_id
        self.nav_active = False    # 주행 중?

    def gps_to_xy(self, gps_json: dict):
        svy21_xy = self.svy_transformer.transform(
            gps_json['lat'], gps_json['lon']
        )
        self.gps_pos[0] = svy21_xy[1]
        self.gps_pos[1] = svy21_xy[0]

    def is_expected_task_id(self, task_id):
        if self.last_path_request is not None:
            if task_id != self.last_path_request.task_id:
                return False
        return True


class FleetManager(Node):

    def __init__(self, config, nav_path):
        self.debug = False
        self.config = config
        self.fleet_name = self.config['rmf_fleet']['name']
        mgr_config = self.config['fleet_manager']

        self.gps = False
        self.offset = [0, 0]
        reference_coordinates_yaml = mgr_config.get('reference_coordinates')
        if reference_coordinates_yaml is not None:
            offset_yaml = reference_coordinates_yaml.get('offset')
            if offset_yaml is not None and len(offset_yaml) > 1:
                self.gps = True
                self.offset = offset_yaml

        super().__init__(f'{self.fleet_name}_fleet_manager')

        self.robots = {}  # Map robot name to state
        self.action_paths = {}  # Map activities to paths

        for robot_name, _ in self.config['rmf_fleet']['robots'].items():
            self.robots[robot_name] = State()
        assert len(self.robots) > 0

        profile = traits.Profile(
            geometry.make_final_convex_circle(
                self.config['rmf_fleet']['profile']['footprint']
            ),
            geometry.make_final_convex_circle(
                self.config['rmf_fleet']['profile']['vicinity']
            ),
        )
        self.vehicle_traits = traits.VehicleTraits(
            linear=traits.Limits(
                *self.config['rmf_fleet']['limits']['linear']
            ),
            angular=traits.Limits(
                *self.config['rmf_fleet']['limits']['angular']
            ),
            profile=profile,
        )
        self.vehicle_traits.differential.reversible = self.config['rmf_fleet'][
            'reversible'
        ]

        fleet_manager_config = self.config['fleet_manager']
        self.action_paths = fleet_manager_config.get('action_paths', {})
        self.sio = socketio.Client()

        @self.sio.on('/gps')
        def message(data):
            try:
                robot = json.loads(data)
                robot_name = robot['robot_id']
                self.robots[robot_name].gps_to_xy(robot)
            except KeyError as e:
                self.get_logger().info(f'Malformed GPS Message!: {e}')

        if self.gps:
            while True:
                try:
                    self.sio.connect('http://0.0.0.0:8080')
                    break
                except Exception:
                    self.get_logger().info(
                        'Trying to connect to sio server at '
                        'http://0.0.0.0:8080..'
                    )
                    time.sleep(1)

        # === nav2 백엔드 (M5b): slotcar 의 /robot_state(구독)·PathRequest(발행) 대신,
        #     로봇별 NavigateToPose 액션클라 + /cmd_vel·/battery + 위치는 TF(map→base_footprint) ===
        # 위치를 /amcl_pose(움직일 때만 희소 발행) 대신 TF(연속)로 → 정지 로봇도 위치 확보.
        self._nav_clients = {}        # robot_name -> ActionClient(NavigateToPose)
        self._cmd_vel_pubs = {}       # robot_name -> cmd_vel publisher (정지용)
        self._robot_base_frames = {}  # robot_name -> (base_frame, map_frame) for TF lookup
        self.tf_buffer = tf2_ros.Buffer()
        self.tf_listener = tf2_ros.TransformListener(self.tf_buffer, self)
        for robot_name in self.robots:
            robot_cfg = self.config['rmf_fleet']['robots'][robot_name]
            ns = robot_cfg.get('namespace', '') if isinstance(robot_cfg, dict) else ''
            prefix = f'/{ns}' if ns else ''   # namespace 없으면 전역(M5b 단일), 있으면 prefix(M5c 다중)
            fprefix = f'{ns}/' if ns else ''
            self._nav_clients[robot_name] = ActionClient(
                self, NavigateToPose, f'{prefix}/navigate_to_pose')
            self._robot_base_frames[robot_name] = (f'{fprefix}base_footprint', 'map')
            self.create_subscription(
                Float32, f'{prefix}/battery',
                lambda msg, rn=robot_name: self.battery_cb(msg, rn), 10)
            self._cmd_vel_pubs[robot_name] = self.create_publisher(
                TwistStamped, f'{prefix}/cmd_vel', 10)
        # 주기적으로 TF 에서 위치 읽어 robot.state 합성 (어댑터 get_data 용)
        self.create_timer(0.1, self._update_positions_from_tf)

        transient_qos = QoSProfile(
            history=History.KEEP_LAST,
            depth=1,
            reliability=Reliability.RELIABLE,
            durability=Durability.TRANSIENT_LOCAL,
        )

        self.create_subscription(
            DockSummary,
            'dock_summary',
            self.dock_summary_cb,
            qos_profile=transient_qos,
        )

        self.path_pub = self.create_publisher(
            PathRequest,
            'robot_path_requests',
            qos_profile=qos_profile_system_default,
        )

        @app.get('/open-rmf/rmf_demos_fm/status/', response_model=Response)
        async def status(robot_name: Optional[str] = None):
            response = {'data': {}, 'success': False, 'msg': ''}
            if robot_name is None:
                response['data']['all_robots'] = []
                for robot_name in self.robots:
                    state = self.robots.get(robot_name)
                    if state is None or state.state is None:
                        return response
                    response['data']['all_robots'].append(
                        self.get_robot_state(state, robot_name)
                    )
            else:
                state = self.robots.get(robot_name)
                if state is None or state.state is None:
                    return response
                response['data'] = self.get_robot_state(state, robot_name)
            response['success'] = True
            return response

        @app.post('/open-rmf/rmf_demos_fm/navigate/', response_model=Response)
        async def navigate(robot_name: str, cmd_id: int, dest: Request):
            response = {'success': False, 'msg': ''}
            if robot_name not in self.robots or len(dest.destination) < 1:
                return response

            robot = self.robots[robot_name]

            target_x = dest.destination['x']
            target_y = dest.destination['y']
            target_yaw = dest.destination['yaw']
            target_map = dest.map_name
            target_speed_limit = dest.speed_limit

            target_x -= self.offset[0]
            target_y -= self.offset[1]

            robot.map_name = target_map if target_map else 'L1'
            _ = target_speed_limit  # nav2 는 자체 속도 제한 사용 (params)

            # nav2 NavigateToPose goal 전송 (slotcar PathRequest 발행 대신)
            client = self._nav_clients[robot_name]
            if not client.wait_for_server(timeout_sec=2.0):
                response['msg'] = 'nav2 action server not ready'
                return response   # 실패 반환 → 어댑터가 재시도(attempt_cmd_until_success)

            goal = NavigateToPose.Goal()
            goal.pose.header.frame_id = 'map'
            goal.pose.header.stamp = self.get_clock().now().to_msg()
            goal.pose.pose.position.x = float(target_x)
            goal.pose.pose.position.y = float(target_y)
            goal.pose.pose.orientation.z = math.sin(target_yaw / 2.0)
            goal.pose.pose.orientation.w = math.cos(target_yaw / 2.0)

            # 진행/완료 추적용 (get_robot_state 가 destination·last_path_request.task_id 사용)
            target_loc = Location()
            target_loc.x = float(target_x)
            target_loc.y = float(target_y)
            target_loc.yaw = float(target_yaw)
            target_loc.level_name = robot.map_name
            fake_req = PathRequest()
            fake_req.task_id = str(cmd_id)
            robot.last_path_request = fake_req
            robot.destination = target_loc
            robot.cmd_id = cmd_id
            robot.nav_active = True

            send_future = client.send_goal_async(goal)
            send_future.add_done_callback(
                lambda fut, rn=robot_name, cid=cmd_id:
                    self._goal_response_cb(fut, rn, cid))

            if self.debug:
                print(f'[nav2] navigate {robot_name} -> '
                      f'({target_x:.2f},{target_y:.2f}) cmd {cmd_id}')

            response['success'] = True
            return response

        @app.get('/open-rmf/rmf_demos_fm/stop_robot/', response_model=Response)
        async def stop(robot_name: str, cmd_id: int):
            response = {'success': False, 'msg': ''}
            if robot_name not in self.robots:
                return response

            robot = self.robots[robot_name]
            # nav2 goal 취소 + cmd_vel 0 (slotcar 제자리 PathRequest 대신)
            if robot.goal_handle is not None:
                robot.goal_handle.cancel_goal_async()
            twist = TwistStamped()
            twist.header.stamp = self.get_clock().now().to_msg()
            twist.header.frame_id = 'base_link'
            self._cmd_vel_pubs[robot_name].publish(twist)

            if self.debug:
                print(f'[nav2] stop {robot_name}: {cmd_id}')
            robot.nav_active = False
            robot.destination = None
            robot.last_completed_request = cmd_id

            response['success'] = True
            return response

        @app.get(
            '/open-rmf/rmf_demos_fm/action_paths/', response_model=Response
        )
        async def action_paths(activity: str, label: str):
            response = {'success': False, 'msg': ''}
            if activity not in self.action_paths:
                return response

            if label not in self.action_paths[activity][label]:
                return response

            response['data'] = self.action_paths[activity][label]
            response['success'] = True
            return response

        @app.post(
            '/open-rmf/rmf_demos_fm/start_activity/', response_model=Response
        )
        async def start_activity(
            robot_name: str, cmd_id: int, request: Request
        ):
            response = {'success': False, 'msg': ''}
            if (
                robot_name not in self.robots
                or request.activity not in self.action_paths
                or request.label not in self.action_paths[request.activity]
            ):
                return response

            # Invalid request
            if robot_name not in self.robots:
                return response
            robot = self.robots[robot_name]

            path_request = PathRequest()
            cur_loc = robot.state.location
            target_loc = Location()
            path_request.path.append(cur_loc)

            activity_path = self.action_paths[request.activity][request.label]
            map_name = activity_path['map_name']
            for wp in activity_path['path']:
                target_loc = Location()
                target_loc.x = wp[0]
                target_loc.y = wp[1]
                target_loc.yaw = wp[2]
                target_loc.level_name = map_name
                path_request.path.append(target_loc)

            path_request.fleet_name = self.fleet_name
            path_request.robot_name = robot_name
            path_request.task_id = str(cmd_id)
            self.path_pub.publish(path_request)

            if self.debug:
                print(
                    f'Sending [{request.activity}] at [{request.label}] '
                    f'request for {robot_name}: {cmd_id}'
                )
            robot.last_path_request = path_request
            robot.destination = target_loc

            response['success'] = True
            response['data'] = {}
            response['data']['path'] = activity_path
            return response

        @app.post(
            '/open-rmf/rmf_demos_fm/toggle_teleop/', response_model=Response
        )
        async def toggle_teleop(robot_name: str, mode: Request):
            response = {'success': False, 'msg': ''}
            if robot_name not in self.robots:
                return response
            # Toggle action mode
            self.robots[robot_name].mode_teleop = mode.toggle
            response['success'] = True
            return response

        @app.post(
            '/open-rmf/rmf_demos_fm/toggle_attach/', response_model=Response
        )
        async def toggle_attach(robot_name: str, cmd_id: int, mode: Request):
            response = {'success': False, 'msg': ''}
            if robot_name not in self.robots:
                return response
            # Toggle action mode
            if mode.toggle:
                # Use robot mode publisher to set it to "attaching cart mode"
                self.get_logger().info('Publishing attaching mode...')
                msg = self._make_mode_request(robot_name, cmd_id,
                                              RobotMode.MODE_PERFORMING_ACTION,
                                              'attach_cart')
            else:
                # Use robot mode publisher to set it to "detaching cart mode"
                self.get_logger().info('Publishing detaching mode...')
                msg = self._make_mode_request(robot_name, cmd_id,
                                              RobotMode.MODE_PERFORMING_ACTION,
                                              'detach_cart')
            self.mode_pub.publish(msg)
            response['success'] = True
            return response

    def _make_mode_request(self, robot_name, cmd_id, mode, action=''):
        mode_msg = ModeRequest()
        mode_msg.fleet_name = self.fleet_name
        mode_msg.robot_name = robot_name
        mode_msg.mode.mode = mode
        mode_msg.mode.mode_request_id = cmd_id
        mode_msg.mode.performing_action = action
        return mode_msg

    def robot_state_cb(self, msg):
        if msg.name in self.robots:
            robot = self.robots[msg.name]
            if (
                not robot.is_expected_task_id(msg.task_id)
                and not robot.mode_teleop
            ):
                # This message is out of date, so disregard it.
                if robot.last_path_request is not None:
                    # Resend the latest task request for this robot, in case
                    # the message was dropped.
                    if self.debug:
                        print(
                            f'Republishing task request for {msg.name}: '
                            f'{robot.last_path_request.task_id}, '
                            f'because it is currently following {msg.task_id}'
                        )
                    self.path_pub.publish(robot.last_path_request)
                return

            robot.state = msg
            # Check if robot has reached destination
            if robot.destination is None:
                return

            if (
                msg.mode.mode == RobotMode.MODE_IDLE
                or msg.mode.mode == RobotMode.MODE_CHARGING
            ) and len(msg.path) == 0:
                robot = self.robots[msg.name]
                robot.destination = None
                completed_request = int(msg.task_id)
                if robot.last_completed_request != completed_request:
                    if self.debug:
                        print(
                            f'Detecting completed request for {msg.name}: '
                            f'{completed_request}'
                        )
                robot.last_completed_request = completed_request

    def dock_summary_cb(self, msg):
        for fleet in msg.docks:
            if fleet.fleet_name == self.fleet_name:
                for dock in fleet.params:
                    self.docks[dock.start] = dock.path

    # === nav2 백엔드 콜백 (M5b) — slotcar 의 robot_state_cb 자리 대체 ===
    def _update_positions_from_tf(self, _=None):
        """주기적으로 TF(map→base_footprint)에서 위치를 읽어 robot.state 합성.
        /amcl_pose(움직일 때만 희소 발행)와 달리 TF는 연속이라 정지 로봇도 위치 확보."""
        for robot_name in self.robots:
            base_frame, map_frame = self._robot_base_frames[robot_name]
            try:
                tf = self.tf_buffer.lookup_transform(
                    map_frame, base_frame, RclpyTime())
            except Exception:
                continue   # TF 아직 없음 (nav2/AMCL 안 떴거나 localize 전)
            t = tf.transform.translation
            q = tf.transform.rotation
            yaw = math.atan2(2.0 * (q.w * q.z + q.x * q.y),
                             1.0 - 2.0 * (q.y * q.y + q.z * q.z))
            self._set_robot_state(robot_name, t.x, t.y, yaw)

    def _set_robot_state(self, robot_name, x, y, yaw):
        """get_robot_state 는 robot.state(RobotState) 를 읽으므로 TF 값으로 합성."""
        robot = self.robots[robot_name]
        robot.position = [x, y, yaw]
        st = RobotState()
        st.name = robot_name
        loc = Location()
        loc.x = float(x)
        loc.y = float(y)
        loc.yaw = float(yaw)
        loc.level_name = robot.map_name
        st.location = loc
        st.battery_percent = float(robot.battery * 100.0)
        st.mode.mode = (RobotMode.MODE_MOVING if robot.nav_active
                        else RobotMode.MODE_IDLE)
        st.task_id = str(robot.cmd_id) if robot.cmd_id is not None else ''
        robot.state = st

    def battery_cb(self, msg, robot_name):
        if robot_name in self.robots:
            self.robots[robot_name].battery = max(0.0, min(1.0, msg.data / 100.0))

    def _goal_response_cb(self, future, robot_name, cmd_id):
        """NavigateToPose goal 수락 여부 → 수락이면 결과 콜백 등록."""
        robot = self.robots[robot_name]
        try:
            gh = future.result()
        except Exception as e:
            self.get_logger().warn(f'[nav2] {robot_name} goal 전송 실패: {e}')
            robot.nav_active = False
            robot.last_completed_request = cmd_id   # 데드락 방지: 실패도 완료처리
            return
        if not gh.accepted:
            self.get_logger().warn(f'[nav2] {robot_name} goal 거부됨 (cmd {cmd_id})')
            robot.nav_active = False
            robot.last_completed_request = cmd_id
            return
        robot.goal_handle = gh
        gh.get_result_async().add_done_callback(
            lambda fut, rn=robot_name, cid=cmd_id:
                self._nav_result_cb(fut, rn, cid))

    def _nav_result_cb(self, future, robot_name, cmd_id):
        """NavigateToPose 완료 → last_completed_request 설정 (어댑터가 도착 감지)."""
        robot = self.robots[robot_name]
        robot.nav_active = False
        robot.destination = None
        robot.goal_handle = None
        robot.last_completed_request = cmd_id
        if self.debug:
            self.get_logger().info(f'[nav2] {robot_name} 도착 (cmd {cmd_id})')

    def get_robot_state(self, robot: State, robot_name):
        data = {}
        if self.gps:
            position = copy.deepcopy(robot.gps_pos)
        else:
            position = [robot.state.location.x, robot.state.location.y]
        angle = robot.state.location.yaw
        data['robot_name'] = robot_name
        data['map_name'] = robot.state.location.level_name
        data['position'] = {'x': position[0], 'y': position[1], 'yaw': angle}
        data['battery'] = robot.state.battery_percent
        if (
            robot.destination is not None
            and robot.last_path_request is not None
        ):
            destination = robot.destination
            # remove offset for calculation if using gps coords
            if self.gps:
                position[0] -= self.offset[0]
                position[1] -= self.offset[1]
            # calculate arrival estimate
            dist_to_target = self.disp(
                position, [destination.x, destination.y]
            )
            ori_delta = abs(abs(angle) - abs(destination.yaw))
            if ori_delta > np.pi:
                ori_delta = ori_delta - (2 * np.pi)
            if ori_delta < -np.pi:
                ori_delta = (2 * np.pi) + ori_delta
            duration = (
                dist_to_target / self.vehicle_traits.linear.nominal_velocity
                + ori_delta / self.vehicle_traits.rotational.nominal_velocity
            )
            cmd_id = int(robot.last_path_request.task_id)
            data['destination_arrival'] = {
                'cmd_id': cmd_id,
                'duration': duration,
            }
        else:
            data['destination_arrival'] = None

        data['last_completed_request'] = robot.last_completed_request
        if (
            robot.state.mode.mode == RobotMode.MODE_WAITING
            or robot.state.mode.mode == RobotMode.MODE_ADAPTER_ERROR
        ):
            # The name of MODE_WAITING is not very intuitive, but the slotcar
            # plugin uses it to indicate when another robot is blocking its
            # path.
            #
            # MODE_ADAPTER_ERROR means the robot received a plan that
            # didn't make sense, i.e. the plan expected the robot was starting
            # very far from its real present location. When that happens we
            # should replan, so we'll set replan to true in that case as well.
            data['replan'] = True
        else:
            data['replan'] = False

        return data

    def disp(self, A, B):
        return math.sqrt((A[0] - B[0]) ** 2 + (A[1] - B[1]) ** 2)


# ------------------------------------------------------------------------------
# Main
# ------------------------------------------------------------------------------
def main(argv=sys.argv):
    # Init rclpy and adapter
    rclpy.init(args=argv)
    adpt.init_rclcpp()
    args_without_ros = rclpy.utilities.remove_ros_args(argv)

    parser = argparse.ArgumentParser(
        prog='fleet_adapter',
        description='Configure and spin up the fleet adapter',
    )
    parser.add_argument(
        '-c',
        '--config_file',
        type=str,
        required=True,
        help='Path to the config.yaml file',
    )
    parser.add_argument(
        '-n',
        '--nav_graph',
        type=str,
        required=True,
        help='Path to the nav_graph for this fleet adapter',
    )
    args = parser.parse_args(args_without_ros[1:])
    print('Starting fleet manager...')

    with open(args.config_file, 'r') as f:
        config = yaml.safe_load(f)

    fleet_manager = FleetManager(config, args.nav_graph)

    spin_thread = threading.Thread(target=rclpy.spin, args=(fleet_manager,))
    spin_thread.start()

    uvicorn.run(
        app,
        host=config['fleet_manager']['ip'],
        port=config['fleet_manager']['port'],
        log_level='warning',
    )


if __name__ == '__main__':
    main(sys.argv)
