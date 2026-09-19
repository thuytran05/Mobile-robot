#!/usr/bin/env python3
"""
nav_command_node.py — Biến ý định thành hành động của robot (Nav2).

Subscribe: /voice/intent  (std_msgs/String chứa JSON từ intent_node)
Action:    /navigate_to_pose (nav2_msgs/action/NavigateToPose)
Publish:   /voice/say  -> báo cáo kết quả bằng giọng nói

action = "navigate" -> gửi goal tới toạ độ của target trong places.json
action = "stop"     -> huỷ goal đang chạy
"""

import json
import math
import os

import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node
from std_msgs.msg import String
from geometry_msgs.msg import PoseStamped
from nav2_msgs.action import NavigateToPose


def yaw_to_quat(yaw: float):
    return (0.0, 0.0, math.sin(yaw / 2.0), math.cos(yaw / 2.0))


class NavCommandNode(Node):
    def __init__(self):
        super().__init__('nav_command_node')

        default_cfg = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config')
        self.declare_parameter('places_file', os.path.join(default_cfg, 'places.json'))
        self.declare_parameter('frame_id', 'map')

        with open(self.get_parameter('places_file').value, 'r', encoding='utf-8') as f:
            self.places = json.load(f).get('places', {})
        self.frame_id = self.get_parameter('frame_id').value

        self.client = ActionClient(self, NavigateToPose, 'navigate_to_pose')
        self.goal_handle = None

        self.pub_say = self.create_publisher(String, '/voice/say', 10)
        self.create_subscription(String, '/voice/intent', self.on_intent, 10)

        self.get_logger().info('Nav command node sẵn sàng.')

    # ------------------------------------------------------------------
    def say(self, text):
        self.pub_say.publish(String(data=text))

    def on_intent(self, msg: String):
        try:
            data = json.loads(msg.data)
        except json.JSONDecodeError:
            return

        action = data.get('action')
        if action == 'navigate':
            self.send_goal(data.get('target'))
        elif action == 'stop':
            self.cancel_goal()

    # ------------------------------------------------------------------
    def send_goal(self, key):
        place = self.places.get(key)
        if not place:
            self.say('Xin lỗi, tôi chưa biết đường tới nơi đó.')
            return

        if not self.client.wait_for_server(timeout_sec=3.0):
            self.get_logger().error('Không kết nối được Nav2.')
            self.say('Hệ thống điều hướng chưa sẵn sàng.')
            return

        pose = PoseStamped()
        pose.header.frame_id = self.frame_id
        pose.header.stamp = self.get_clock().now().to_msg()
        pose.pose.position.x = float(place['x'])
        pose.pose.position.y = float(place['y'])
        qx, qy, qz, qw = yaw_to_quat(float(place.get('yaw', 0.0)))
        pose.pose.orientation.x = qx
        pose.pose.orientation.y = qy
        pose.pose.orientation.z = qz
        pose.pose.orientation.w = qw

        goal = NavigateToPose.Goal()
        goal.pose = pose

        self._target_name = place.get('name', key)
        self.get_logger().info(f'Gửi goal tới {self._target_name} ({place["x"]}, {place["y"]})')
        self.client.send_goal_async(goal).add_done_callback(self.on_goal_response)

    def on_goal_response(self, future):
        self.goal_handle = future.result()
        if not self.goal_handle.accepted:
            self.say('Tôi không thể di chuyển tới đó lúc này.')
            return
        self.goal_handle.get_result_async().add_done_callback(self.on_result)

    def on_result(self, future):
        status = future.result().status
        if status == 4:      # SUCCEEDED
            self.say(f'Chúng ta đã tới {getattr(self, "_target_name", "nơi cần đến")}. '
                     f'Chúc bạn đi may mắn!')
        elif status == 5:    # CANCELED
            pass
        else:
            self.say('Tôi gặp trở ngại trên đường đi. Bạn vui lòng đi theo biển chỉ dẫn giúp tôi.')
        self.goal_handle = None

    # ------------------------------------------------------------------
    def cancel_goal(self):
        if self.goal_handle is not None:
            self.goal_handle.cancel_goal_async()
            self.get_logger().info('Đã huỷ goal điều hướng.')


def main(args=None):
    rclpy.init(args=args)
    node = NavCommandNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
