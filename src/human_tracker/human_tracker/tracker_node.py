import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2
from ultralytics import YOLO

class HumanTrackerNode(Node):
    def __init__(self):
        super().__init__('human_tracker_node')
        self.model = YOLO('yolov8n-pose.pt') 
        self.bridge = CvBridge()
        self.target_id = None
        
        self.subscription = self.create_subscription(
            Image,
            '/image_raw',
            self.image_callback,
            10)
        self.get_logger().info("Hệ thống đã bật! Hãy giơ tay lên quá đầu để khóa mục tiêu. Bấm 'r' để Reset.")

    def image_callback(self, msg):
        frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        results = self.model.track(frame, persist=True, classes=0, tracker="bytetrack.yaml", verbose=False)
        
        if results[0].boxes is not None and results[0].boxes.id is not None:
            boxes = results[0].boxes.xyxy.cpu().numpy()
            track_ids = results[0].boxes.id.int().cpu().tolist()
            keypoints = results[0].keypoints.xy.cpu().numpy() 
            
            for box, track_id, kpts in zip(boxes, track_ids, keypoints):
                x1, y1, x2, y2 = map(int, box)
                
                # ---- PHẦN MỚI THÊM: VẼ 17 ĐIỂM KHUNG XƯƠNG ----
                for kp_x, kp_y in kpts:
                    if kp_x > 0 and kp_y > 0: # Bỏ qua các điểm bị khuất không thấy
                        # Vẽ các chấm tròn màu vàng tại các khớp
                        cv2.circle(frame, (int(kp_x), int(kp_y)), 5, (0, 255, 255), -1) 
                # -----------------------------------------------

                if self.target_id is None:
                    nose_y = kpts[0][1]
                    l_wrist_y, r_wrist_y = kpts[9][1], kpts[10][1]
                    
                    if nose_y > 0 and ((0 < l_wrist_y < nose_y) or (0 < r_wrist_y < nose_y)):
                        self.target_id = track_id
                        self.get_logger().info(f"LOCKED TARGET: {self.target_id}")

                if self.target_id == track_id:
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 4)
                    cv2.putText(frame, f"LOCKED: {track_id}", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                else:
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 1)

        cv2.imshow("Webcam AI Tracking", frame)
        if cv2.waitKey(1) & 0xFF == ord('r'):
            self.target_id = None
            self.get_logger().info("Đã xóa mục tiêu!")

def main(args=None):
    rclpy.init(args=args)
    node = HumanTrackerNode()
    rclpy.spin(node)
    node.destroy_node()
    cv2.destroyAllWindows()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
