#!/usr/bin/env python3
"""
stt_node.py — Nghe micro và chuyển thành text.

Dùng Vosk (offline, nhẹ, chạy realtime trên CPU / Jetson / Raspberry Pi 4).
Publish:  /voice/text   (std_msgs/String)
Subscribe:/voice/speaking (std_msgs/Bool) -> tạm ngưng nghe khi robot đang nói
                                             (tránh robot nghe chính giọng mình)

Chế độ test không cần micro:  ros2 run airport_robot_voice stt_node --ros-args -p mode:=keyboard
"""

import json
import queue
import sys
import threading

import rclpy
from rclpy.node import Node
from std_msgs.msg import String, Bool


class SttNode(Node):
    def __init__(self):
        super().__init__('stt_node')

        # ---- Tham số ----
        self.declare_parameter('mode', 'mic')            # 'mic' hoặc 'keyboard'
        self.declare_parameter('model_path', '/opt/vosk/vosk-model-small-vn-0.4')
        self.declare_parameter('sample_rate', 16000)
        self.declare_parameter('device', -1)             # index micro, -1 = mặc định
        self.declare_parameter('wake_word', '')          # để trống = luôn nghe
        self.declare_parameter('min_chars', 2)           # bỏ qua câu quá ngắn / nhiễu

        self.mode = self.get_parameter('mode').value
        self.model_path = self.get_parameter('model_path').value
        self.sample_rate = int(self.get_parameter('sample_rate').value)
        self.device = int(self.get_parameter('device').value)
        self.wake_word = self.get_parameter('wake_word').value.lower().strip()
        self.min_chars = int(self.get_parameter('min_chars').value)

        # ---- Topic ----
        self.pub_text = self.create_publisher(String, '/voice/text', 10)
        self.create_subscription(Bool, '/voice/speaking', self.on_speaking, 10)

        self.robot_speaking = False
        self.awake = (self.wake_word == '')

        if self.mode == 'keyboard':
            self.get_logger().info('Chế độ KEYBOARD: gõ câu hỏi rồi Enter.')
            threading.Thread(target=self.keyboard_loop, daemon=True).start()
        else:
            threading.Thread(target=self.mic_loop, daemon=True).start()

    # ------------------------------------------------------------------
    def on_speaking(self, msg: Bool):
        """Robot đang phát loa -> ngưng xử lý audio."""
        self.robot_speaking = msg.data

    def publish(self, text: str):
        text = text.strip()
        if len(text) < self.min_chars:
            return

        # Xử lý wake word (nếu có cấu hình)
        if self.wake_word:
            if not self.awake:
                if self.wake_word in text.lower():
                    self.awake = True
                    text = text.lower().replace(self.wake_word, '').strip()
                    self.get_logger().info('Đã kích hoạt bằng wake word.')
                    if not text:
                        self.pub_text.publish(String(data='__wake__'))
                        return
                else:
                    return

        self.get_logger().info(f'NGHE ĐƯỢC: "{text}"')
        self.pub_text.publish(String(data=text))

    # ------------------------------------------------------------------
    def keyboard_loop(self):
        while rclpy.ok():
            try:
                line = sys.stdin.readline()
            except Exception:
                break
            if not line:
                break
            self.publish(line)

    # ------------------------------------------------------------------
    def mic_loop(self):
        try:
            import sounddevice as sd
            from vosk import Model, KaldiRecognizer, SetLogLevel
        except ImportError as e:
            self.get_logger().error(
                f'Thiếu thư viện: {e}. Cài bằng: pip install vosk sounddevice')
            return

        SetLogLevel(-1)

        try:
            model = Model(self.model_path)
        except Exception as e:
            self.get_logger().error(
                f'Không nạp được model Vosk tại {self.model_path}: {e}')
            return

        rec = KaldiRecognizer(model, self.sample_rate)
        rec.SetWords(False)

        q = queue.Queue()

        def callback(indata, frames, time_info, status):
            if status:
                self.get_logger().warn(str(status))
            q.put(bytes(indata))

        dev = None if self.device < 0 else self.device
        self.get_logger().info('Micro đã sẵn sàng. Bắt đầu nghe...')

        with sd.RawInputStream(samplerate=self.sample_rate, blocksize=8000,
                               device=dev, dtype='int16',
                               channels=1, callback=callback):
            while rclpy.ok():
                data = q.get()

                # Robot đang nói -> nuốt audio, không nhận dạng
                if self.robot_speaking:
                    rec.Reset()
                    continue

                if rec.AcceptWaveform(data):
                    result = json.loads(rec.Result())
                    self.publish(result.get('text', ''))


def main(args=None):
    rclpy.init(args=args)
    node = SttNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
