import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2
import numpy as np
from ultralytics import YOLO
from geometry_msgs.msg import Point
import message_filters

class HumanTrackerNode(Node):
    def __init__(self):
        super().__init__('human_tracker_node')
        self.model = YOLO('yolov8n-pose.pt') 
        self.bridge = CvBridge()
        self.target_id = None
        
        # 1. Khai báo 2 topic Màu và Chiều sâu
        self.color_sub = message_filters.Subscriber(self, Image, '/camera/color/image_raw')
        self.depth_sub = message_filters.Subscriber(self, Image, '/camera/depth/image_raw')
        
        # 2. Đồng bộ hóa khung hình
        self.ts = message_filters.ApproximateTimeSynchronizer(
            [self.color_sub, self.depth_sub], 
            queue_size=10, 
            slop=0.1
        )
        self.ts.registerCallback(self.sync_callback)

        self.get_logger().info("Hệ thống 3D Astra đã bật! Giơ tay quá đầu để khóa.")
        self.target_pub = self.create_publisher(Point, '/target_bbox', 10)
        self.debug_pub = self.create_publisher(Image, '/tracking/debug_view', 10)

    def sync_callback(self, color_msg, depth_msg):
        frame = self.bridge.imgmsg_to_cv2(color_msg, desired_encoding='bgr8')
        depth_frame = self.bridge.imgmsg_to_cv2(depth_msg, desired_encoding='passthrough')
        
        results = self.model.track(frame, persist=True, classes=0, tracker="tracktrack.yaml", verbose=False)
        
        if results[0].boxes is not None and results[0].boxes.id is not None:
            boxes = results[0].boxes.xyxy.cpu().numpy()
            track_ids = results[0].boxes.id.int().cpu().tolist()
            confs = results[0].boxes.conf.cpu().numpy()
            keypoints = results[0].keypoints.xy.cpu().numpy() 
            
            for box, track_id, conf, kpts in zip(boxes, track_ids, confs, keypoints):
                x1, y1, x2, y2 = map(int, box)
                conf_percent = int(conf * 100)
                
                # Tọa độ mũi
                nose_x, nose_y = int(kpts[0][0]), int(kpts[0][1])
                
                # Vẽ các điểm khớp xương
                for kp_x, kp_y in kpts:
                    if kp_x > 0 and kp_y > 0: 
                        cv2.circle(frame, (int(kp_x), int(kp_y)), 4, (0, 255, 255), -1) 

                # Khóa mục tiêu khi giơ tay qua đầu
                if self.target_id is None:
                    l_wrist_y, r_wrist_y = kpts[9][1], kpts[10][1]
                    if nose_y > 0 and ((0 < l_wrist_y < nose_y) or (0 < r_wrist_y < nose_y)):
                        self.target_id = track_id
                        self.get_logger().info(f"LOCKED TARGET: {self.target_id}")

                # Mục tiêu đã khóa
                if self.target_id == track_id:
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 3)
                    
                    # Tính chiều sâu Z tại mũi (lấy trung bình vùng 3x3 để chống nhiễu hạt)
                    nose_depth = 0.0
                    h, w = depth_frame.shape[:2]
                    if 2 <= nose_y < h - 2 and 2 <= nose_x < w - 2:
                        patch = depth_frame[nose_y - 1:nose_y + 2, nose_x - 1:nose_x + 2]
                        valid_pixels = patch[patch > 0]
                        if len(valid_pixels) > 0:
                            nose_depth = float(np.median(valid_pixels))
                    
                    # CHỈ HIỂN THỊ ID VÀ % ĐỘ TIN CẬY (Đã bỏ Z)
                    cv2.putText(frame, f"LOCKED:{track_id} ({conf_percent}%)", 
                                (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    
                    # Vẫn xuất đầy đủ tọa độ X, Y và Chiều sâu Z lên ROS 2 topic
                    target_msg = Point()
                    target_msg.x = float((x1 + x2) / 2)  
                    target_msg.y = float((y1 + y2) / 2)  
                    target_msg.z = nose_depth
                    self.target_pub.publish(target_msg)
                else:
                    # Người chưa khóa
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 1)
                    cv2.putText(frame, f"ID:{track_id} ({conf_percent}%)", 
                                (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)

        # Xuất ảnh debug lên RViz2
        debug_img_msg = self.bridge.cv2_to_imgmsg(frame, encoding="bgr8")
        self.debug_pub.publish(debug_img_msg)

def main(args=None):
    rclpy.init(args=args)
    node = HumanTrackerNode()
    rclpy.spin(node)
    node.destroy_node()
    cv2.destroyAllWindows()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
