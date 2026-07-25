#!/usr/bin/env python3

import os
import re
import sys
import time
import serial
import threading

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from std_msgs.msg import Float32

# -------------------------------------------------------------
# Dynamic Workspace / ROS Local File Paths
# -------------------------------------------------------------
WORKSPACE_DATA_DIR = os.path.expanduser("~/.ros/deliverybot")
os.makedirs(WORKSPACE_DATA_DIR, exist_ok=True)

DEFAULT_ERROR_FILE = os.path.join(WORKSPACE_DATA_DIR, "lateral_error.txt")
STARTING_YAW_FILE = os.path.join(WORKSPACE_DATA_DIR, "starting_yaw.txt")


class DeliveryBotMotorController:
    """Serial Interface for Arduino Motor Control & Telemetry"""
    def __init__(self, port="/dev/ttyUSB0", baudrate=115200, timeout=1.0, logger=None):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.ser = None
        self.current_yaw = 0.0
        self.logger = logger

    def log(self, msg):
        if self.logger:
            self.logger.info(msg)
        else:
            print(msg)

    def connect(self):
        try:
            self.ser = serial.Serial(port=self.port, baudrate=self.baudrate, timeout=self.timeout)
            self.log("[INFO] Waiting for Arduino boot & IMU calibration (4s)...")
            time.sleep(4.0)
            self.ser.reset_input_buffer()
            self.ser.reset_output_buffer()
            self.log(f"[OK] Connected to Arduino on {self.port}")
            self.read_available_lines()
        except serial.SerialException as e:
            self.log(f"[ERROR] Could not open serial port {self.port}: {e}")

    def close(self):
        if self.ser and self.ser.is_open:
            self.stop()
            time.sleep(0.1)
            self.ser.close()

    def send_command(self, command, read_after=True):
        if not self.ser or not self.ser.is_open:
            return
        command = command.strip() + "\n"
        self.ser.write(command.encode("utf-8"))
        time.sleep(0.002)
        self.ser.flush()
        if read_after:
            time.sleep(0.03)
            self.read_available_lines()

    def read_available_lines(self):
        if not self.ser:
            return
        while self.ser.in_waiting > 0:
            try:
                line = self.ser.readline().decode("utf-8", errors="ignore").strip()
                if line and "IMU yaw=" in line:
                    match = re.search(r"yaw=(-?\d+\.\d+)", line)
                    if match:
                        self.current_yaw = float(match.group(1))
            except Exception:
                break

    @staticmethod
    def clamp_speed(val): return max(0, min(255, int(val)))
    @staticmethod
    def clamp_dur(val): return max(0, int(val))

    def move_forward(self, left, right, dur):
        self.send_command(f"F {self.clamp_speed(left)} {self.clamp_speed(right)} {self.clamp_dur(dur)}", False)

    def move_backward(self, left, right, dur):
        self.send_command(f"B {self.clamp_speed(left)} {self.clamp_speed(right)} {self.clamp_dur(dur)}", False)

    def turn_left(self, left, right, dur):
        self.send_command(f"L {self.clamp_speed(left)} {self.clamp_speed(right)} {self.clamp_dur(dur)}", False)

    def turn_right(self, left, right, dur):
        self.send_command(f"R {self.clamp_speed(right)} {self.clamp_speed(right)} {self.clamp_dur(dur)}", False)

    def reset_yaw(self):
        self.send_command("Z", read_after=True)
        self.current_yaw = 0.0

    def stop(self):
        self.send_command("S", read_after=False)
        time.sleep(0.02)
        self.send_command("S", read_after=True)


class GuidedMotorControlROS2Node(Node):
    def __init__(self):
        super().__init__('guided_motor_control_node')

        # -------------------------------------------------------------
        # ROS2 Node Parameters with Local Workspace Defaults
        # -------------------------------------------------------------
        self.declare_parameter('port', '/dev/ttyUSB0')
        self.declare_parameter('baudrate', 115200)
        self.declare_parameter('base_power', 220)
        self.declare_parameter('chunk_ms', 1000)
        self.declare_parameter('error_file', DEFAULT_ERROR_FILE)
        self.declare_parameter('starting_yaw_file', STARTING_YAW_FILE)

        port = self.get_parameter('port').value
        baudrate = self.get_parameter('baudrate').value
        self.error_file = self.get_parameter('error_file').value
        self.starting_yaw_file = self.get_parameter('starting_yaw_file').value

        # Initialize lateral error file if it doesn't exist
        if not os.path.exists(self.error_file):
            with open(self.error_file, 'w') as f:
                f.write("lateral_error_cm=0.0\n")

        # Initialize starting yaw file if it doesn't exist
        if not os.path.exists(self.starting_yaw_file):
            with open(self.starting_yaw_file, 'w') as f:
                f.write("0.0\n")

        # Core Controller
        self.robot = DeliveryBotMotorController(port=port, baudrate=baudrate, logger=self.get_logger())
        self.robot.connect()

        # Publishers
        self.yaw_pub = self.create_publisher(Float32, '/imu/yaw', 10)

        # Subscribers
        self.cmd_sub = self.create_subscription(Twist, '/cmd_vel', self.cmd_vel_callback, 10)
        self.lateral_err_sub = self.create_subscription(Float32, '/lateral_error', self.lateral_error_callback, 10)

        # Telemetry loop timer
        self.create_timer(0.05, self.telemetry_loop)

        # Dynamic State
        self.lateral_error_cm = 0.0
        self.is_guided_executing = False

        self.get_logger().info(f"Guided Motor Node initialized.")
        self.get_logger().info(f"Using error file: '{self.error_file}'")
        self.get_logger().info(f"Using starting yaw file: '{self.starting_yaw_file}'")

    def telemetry_loop(self):
        self.robot.read_available_lines()
        yaw_msg = Float32()
        yaw_msg.data = self.robot.current_yaw
        self.yaw_pub.publish(yaw_msg)

    def lateral_error_callback(self, msg: Float32):
        self.lateral_error_cm = msg.data
        try:
            with open(self.error_file, 'w') as f:
                f.write(f"lateral_error_cm={self.lateral_error_cm:.2f}\n")
        except Exception as e:
            self.get_logger().error(f"Failed to update error file: {e}")

    def cmd_vel_callback(self, msg: Twist):
        if self.is_guided_executing:
            return

        vx = msg.linear.x
        wz = msg.angular.z

        base_power = self.get_parameter('base_power').value

        if abs(vx) < 0.01 and abs(wz) < 0.01:
            self.robot.stop()
        elif vx > 0:
            left = base_power + int(wz * 50)
            right = base_power - int(wz * 50)
            self.robot.move_forward(left, right, 200)
        elif vx < 0:
            left = base_power - int(wz * 50)
            right = base_power + int(wz * 50)
            self.robot.move_backward(left, right, 200)
        elif wz > 0:
            self.robot.turn_left(200, 200, 200)
        elif wz < 0:
            self.robot.turn_right(200, 200, 200)

    def destroy_node(self):
        self.robot.close()
        super().destroy_node()

def main(args=None):
    rclpy.init(args=args)
    node = GuidedMotorControlROS2Node()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()