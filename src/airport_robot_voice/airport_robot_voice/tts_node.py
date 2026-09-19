#!/usr/bin/env python3
"""
tts_node.py — Đọc văn bản thành tiếng nói.

3 engine, chọn bằng tham số `engine`:
  - piper  : offline, giọng tiếng Việt tự nhiên nhất  (khuyến nghị)
  - espeak : offline, nhẹ nhất, giọng máy
  - gtts   : online (cần internet), giọng rất hay

Subscribe: /voice/say      (std_msgs/String)
Publish:   /voice/speaking (std_msgs/Bool) -> báo STT tạm ngưng nghe
"""

import os
import queue
import subprocess
import tempfile
import threading

import rclpy
from rclpy.node import Node
from std_msgs.msg import String, Bool


class TtsNode(Node):
    def __init__(self):
        super().__init__('tts_node')

        self.declare_parameter('engine', 'piper')
        self.declare_parameter('piper_bin', 'piper')
        self.declare_parameter('piper_model', '/opt/piper/vi_VN-vais1000-medium.onnx')
        self.declare_parameter('player', 'aplay')     # aplay | paplay | ffplay
        self.declare_parameter('speed', 1.0)

        self.engine = self.get_parameter('engine').value
        self.piper_bin = self.get_parameter('piper_bin').value
        self.piper_model = self.get_parameter('piper_model').value
        self.player = self.get_parameter('player').value
        self.speed = float(self.get_parameter('speed').value)

        self.q = queue.Queue()
        self.pub_speaking = self.create_publisher(Bool, '/voice/speaking', 10)
        self.create_subscription(String, '/voice/say', self.on_say, 10)

        threading.Thread(target=self.worker, daemon=True).start()
        self.get_logger().info(f'TTS sẵn sàng (engine={self.engine}).')

    def on_say(self, msg: String):
        if msg.data.strip():
            self.q.put(msg.data.strip())

    # ------------------------------------------------------------------
    def worker(self):
        while rclpy.ok():
            text = self.q.get()
            self.pub_speaking.publish(Bool(data=True))
            self.get_logger().info(f'NÓI: "{text}"')
            try:
                self.synthesize(text)
            except Exception as e:
                self.get_logger().error(f'Lỗi TTS: {e}')
            finally:
                self.pub_speaking.publish(Bool(data=False))

    # ------------------------------------------------------------------
    def synthesize(self, text: str):
        if self.engine == 'espeak':
            subprocess.run(['espeak-ng', '-v', 'vi',
                            '-s', str(int(160 * self.speed)), text], check=False)
            return

        wav = tempfile.NamedTemporaryFile(suffix='.wav', delete=False).name
        try:
            if self.engine == 'piper':
                subprocess.run(
                    [self.piper_bin, '--model', self.piper_model,
                     '--length_scale', str(round(1.0 / max(self.speed, 0.1), 2)),
                     '--output_file', wav],
                    input=text.encode('utf-8'), check=True)

            elif self.engine == 'gtts':
                from gtts import gTTS
                mp3 = wav.replace('.wav', '.mp3')
                gTTS(text=text, lang='vi').save(mp3)
                subprocess.run(['ffmpeg', '-y', '-loglevel', 'quiet',
                                '-i', mp3, wav], check=True)
                os.remove(mp3)
            else:
                self.get_logger().error(f'Engine không hỗ trợ: {self.engine}')
                return

            if self.player == 'ffplay':
                subprocess.run(['ffplay', '-nodisp', '-autoexit',
                                '-loglevel', 'quiet', wav], check=False)
            else:
                subprocess.run([self.player, '-q', wav], check=False)
        finally:
            if os.path.exists(wav):
                os.remove(wav)


def main(args=None):
    rclpy.init(args=args)
    node = TtsNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
