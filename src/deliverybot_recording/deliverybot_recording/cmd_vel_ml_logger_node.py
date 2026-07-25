#!/usr/bin/env python3

import os
import csv
import cv2
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from geometry_msgs.msg import Twist
from std_msgs.msg import Float32, Float32MultiArray
from cv_bridge import CvBridge

class CmdVelMLLoggerNode(Node):
    def __init__(self):
        super().__init__('cmd_vel_ml_logger_node')
        self.bridge = CvBridge()

        # Node Parameters
        self.declare_parameter('session_name', 'Corridor1_ML')
        self.declare_parameter('base_dir', 'dataset')
        self.declare_parameter('base_power', 220)

        self.session_name = self.get_parameter('session_name').value
        self.base_dir = self.get_parameter('base_dir').value
        self.base_power = self.get_parameter('base_power').value

        # Directories & CSV Setup
        self.session_dir = os.path.join(self.base_dir, self.session_name)
        self.img_dir = os.path.join(self.session_dir, 'images')
        os.makedirs(self.img_dir, exist_ok=True)

        self.csv_path = os.path.join(self.session_dir, f'{self.session_name}_ml_dataset.csv')
        self.csv_file = open(self.csv_path, 'w', newline='')
        self.writer = csv.writer(self.csv_file)

        self.writer.writerow([
            'timestamp_sec',
            'timestamp_nanosec',
            'image_filename',
            'cmd_linear_x',
            'cmd_angular_z',
            'est_left_pwm',
            'est_right_pwm',
            'imu_yaw',
            'us_front',
            'us_left',
            'us_right',
            'us_back'
        ])

        # State Cache
        self.curr_cmd = Twist()
        self.curr_yaw = 0.0
        self.curr_us = [0.0, 0.0, 0.0, 0.0]
        self.frame_count = 0

        # Subscriptions
        self.create_subscription(Twist, '/cmd_vel', self.cmd_cb, 10)
        self.create_subscription(Float32, '/imu/yaw', self.yaw_cb, 10)
        self.create_subscription(Float32MultiArray, '/ultrasonic', self.us_cb, 10)
        self.create_subscription(Image, '/camera/image_raw', self.img_cb, 10)

        self.get_logger().info(f"ML Logger started! Saving to: '{self.session_dir}'")

    def cmd_cb(self, msg: Twist):
        self.curr_cmd = msg

    def yaw_cb(self, msg: Float32):
        self.curr_yaw = msg.data

    def us_cb(self, msg: Float32MultiArray):
        if len(msg.data) >= 4:
            self.curr_us = list(msg.data[:4])

    def img_cb(self, msg: Image):
        stamp = msg.header.stamp
        sec = stamp.sec
        nanosec = stamp.nanosec

        frame_name = f"{self.session_name}_frame_{self.frame_count:06d}.jpg"
        img_path = os.path.join(self.img_dir, frame_name)

        cv_img = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        cv2.imwrite(img_path, cv_img)

        vx = self.curr_cmd.linear.x
        wz = self.curr_cmd.angular.z

        if abs(vx) < 0.01 and abs(wz) < 0.01:
            left_pwm, right_pwm = 0, 0
        elif vx > 0:
            left_pwm = self.base_power + int(wz * 50)
            right_pwm = self.base_power - int(wz * 50)
        elif vx < 0:
            left_pwm = -(self.base_power - int(wz * 50))
            right_pwm = -(self.base_power + int(wz * 50))
        elif wz > 0:
            left_pwm, right_pwm = -200, 200
        else:
            left_pwm, right_pwm = 200, -200

        self.writer.writerow([
            sec,
            nanosec,
            frame_name,
            round(vx, 4),
            round(wz, 4),
            left_pwm,
            right_pwm,
            round(self.curr_yaw, 2),
            self.curr_us[0],
            self.curr_us[1],
            self.curr_us[2],
            self.curr_us[3]
        ])
        self.csv_file.flush()

        self.frame_count += 1

    def destroy_node(self):
        if hasattr(self, 'csv_file') and not self.csv_file.closed:
            self.csv_file.close()
        super().destroy_node()

# -------------------------------------------------------------
# Essential Main Function Required by ROS2 setup.py entry_point
# -------------------------------------------------------------
def main(args=None):
    rclpy.init(args=args)
    node = CmdVelMLLoggerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()