import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from geometry_msgs.msg import Twist, Vector3
from std_msgs.msg import Float32MultiArray
from cv_bridge import CvBridge
import cv2
import csv
import os

class DataRecorderNode(Node):
    def __init__(self):
        super().__init__('data_recorder_node')
        self.bridge = CvBridge()
        
        # 1. Declare ROS2 Parameters (with configurable defaults)
        self.declare_parameter('session_name', 'Corridor1')
        self.declare_parameter('base_dir', 'dataset')
        
        # Read parameter values
        self.session_name = self.get_parameter('session_name').get_parameter_value().string_value
        self.base_dir = self.get_parameter('base_dir').get_parameter_value().string_value
        
        # 2. Build folder structure dynamically: dataset/Corridor1/images/
        self.session_dir = os.path.join(self.base_dir, self.session_name)
        self.img_dir = os.path.join(self.session_dir, 'images')
        os.makedirs(self.img_dir, exist_ok=True)
        
        # 3. Create CSV file inside dataset/Corridor1/sensor_data.csv
        self.csv_path = os.path.join(self.session_dir, f'{self.session_name}_sensor_data.csv')
        self.csv_file = open(self.csv_path, 'w', newline='')
        self.writer = csv.writer(self.csv_file)
        self.writer.writerow(['timestamp', 'image_filename', 'us_1', 'us_2', 'us_3', 'yaw', 'cmd_linear_x', 'cmd_angular_z'])

        # Dynamic State Caches
        self.curr_us = [0.0, 0.0, 0.0]
        self.curr_imu = Vector3()
        self.curr_cmd = Twist()
        self.frame_count = 0

        # Subscriptions
        self.create_subscription(Float32MultiArray, '/ultrasonic', self.us_cb, 10)
        self.create_subscription(Vector3, '/imu', self.imu_cb, 10)
        self.create_subscription(Twist, '/cmd_vel', self.cmd_cb, 10)
        self.create_subscription(Image, '/camera/image_raw', self.img_cb, 10)

        self.get_logger().info(f"Data Recorder initialized. Saving to: '{self.session_dir}'")

    def us_cb(self, msg): 
        self.curr_us = msg.data

    def imu_cb(self, msg): 
        self.curr_imu = msg

    def cmd_cb(self, msg): 
        self.curr_cmd = msg

    def img_cb(self, msg):
        stamp = f"{msg.header.stamp.sec}.{msg.header.stamp.nanosec}"
        
        # Custom frame name based on session parameter: Corridor1_frame_000000.jpg
        frame_name = f"{self.session_name}_frame_{self.frame_count:06d}.jpg"
        img_path = os.path.join(self.img_dir, frame_name)

        # Convert ROS2 Image to OpenCV image and save
        cv_img = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        cv2.imwrite(img_path, cv_img)

        # Write synchronized entry to CSV
        us1 = self.curr_us[0] if len(self.curr_us) > 0 else 0.0
        us2 = self.curr_us[1] if len(self.curr_us) > 1 else 0.0
        us3 = self.curr_us[2] if len(self.curr_us) > 2 else 0.0

        self.writer.writerow([
            stamp, 
            frame_name, 
            us1, 
            us2, 
            us3, 
            self.curr_imu.x, 
            self.curr_cmd.linear.x, 
            self.curr_cmd.angular.z
        ])
        
        self.frame_count += 1

    def destroy_node(self):
        self.csv_file.close()
        self.get_logger().info(f"Closed recorder. Total frames saved: {self.frame_count}")
        super().destroy_node()

def main(args=None):
    rclpy.init(args=args)
    node = DataRecorderNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()