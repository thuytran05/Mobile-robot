#!/usr/bin/env python3
"""
intent_node.py — "Bộ não" hiểu ý định. KHÔNG dùng LLM.

Toàn bộ logic nằm trong nlu.py (thuần Python, test được offline).
Node này chỉ làm nhiệm vụ nối lõi NLU vào ROS 2.

Subscribe: /voice/text    (std_msgs/String)  <- từ stt_node
Publish:   /voice/say     (std_msgs/String)  -> tts_node đọc
           /voice/intent  (std_msgs/String chứa JSON) -> nav_command_node
"""

import json
import os

import rclpy
from rclpy.node import Node
from std_msgs.msg import String

from airport_robot_voice.nlu import NluEngine


class IntentNode(Node):
    def __init__(self):
        super().__init__('intent_node')

        share = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config')
        self.declare_parameter('intents_file', os.path.join(share, 'intents.json'))
        self.declare_parameter('places_file', os.path.join(share, 'places.json'))
        self.declare_parameter('context_timeout', 15.0)

        self.engine = NluEngine(self.get_parameter('intents_file').value,
                                self.get_parameter('places_file').value)
        self.engine.ctx_timeout = float(self.get_parameter('context_timeout').value)

        self.pub_say = self.create_publisher(String, '/voice/say', 10)
        self.pub_intent = self.create_publisher(String, '/voice/intent', 10)
        self.create_subscription(String, '/voice/text', self.on_text, 10)

        self.get_logger().info(
            f'NLU sẵn sàng: {len(self.engine.cfg["intents"])} intent, '
            f'{len(self.engine.places)} địa điểm.')

    def on_text(self, msg: String):
        raw = msg.data.strip()
        if not raw:
            return
        if raw == '__wake__':
            self.pub_say.publish(String(data='Vâng, tôi nghe đây.'))
            return

        r = self.engine.process(raw)
        self.get_logger().info(
            f'"{raw}" -> {r["intent"]} ({r["score"]:.0f}) '
            f'slots={r["slots"]} action={r["action"]}')

        self.pub_say.publish(String(data=r['text']))
        self.pub_intent.publish(String(data=json.dumps(
            {'intent': r['intent'], 'raw': raw, 'slots': r['slots'],
             'action': r['action'], 'target': r['target'],
             'score': round(r['score'], 1)}, ensure_ascii=False)))


def main(args=None):
    rclpy.init(args=args)
    node = IntentNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
