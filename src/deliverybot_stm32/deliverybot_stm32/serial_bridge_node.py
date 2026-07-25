import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist, Vector3
from std_msgs.msg import Float32MultiArray
import serial

class SerialBridgeNode(Node):
    def __init__(self):
        super().__init__('serial_bridge_node')
        
        # Publishers
        self.us_pub = self.create_publisher(Float32MultiArray, '/ultrasonic', 10)
        self.imu_pub = self.create_publisher(Vector3, '/imu', 10)
        
        # Subscriber for motor velocity
        self.cmd_sub = self.create_subscription(Twist, '/cmd_vel', self.cmd_callback, 10)
        
        # Serial setup (adjust port if needed)
        try:
            self.ser = serial.Serial('/dev/ttyUSB0', 115200, timeout=0.05)
        except Exception as e:
            self.get_logger().error(f"Failed to open serial port: {e}")

        # Timer to read incoming sensor data (50 Hz)
        self.timer = self.create_timer(0.02, self.read_sensors)

    def cmd_callback(self, msg: Twist):
        linear_x = msg.linear.x
        angular_z = msg.angular.z
        
        # Format command to microcontroller (trim handled on hardware)
        command_str = f"M,{linear_x:.2f},{angular_z:.2f}\n"
        if hasattr(self, 'ser') and self.ser.is_open:
            self.ser.write(command_str.encode('utf-8'))

    def read_sensors(self):
        if hasattr(self, 'ser') and self.ser.in_waiting:
            try:
                line = self.ser.readline().decode('utf-8').strip()
                # Assuming format: "US,d1,d2,d3|IMU,yaw,pitch,roll"
                if "US" in line:
                    parts = line.split('|')
                    us_data = [float(x) for x in parts[0].split(',')[1:]]
                    imu_data = [float(x) for x in parts[1].split(',')[1:]]
                    
                    # Publish Ultrasonic
                    us_msg = Float32MultiArray(data=us_data)
                    self.us_pub.publish(us_msg)
                    
                    # Publish IMU (Yaw, Pitch, Roll)
                    imu_msg = Vector3(x=imu_data[0], y=imu_data[1], z=imu_data[2])
                    self.imu_pub.publish(imu_msg)
            except Exception:
                pass

def main(args=None):
    rclpy.init(args=args)
    node = SerialBridgeNode()
    rclpy.spin(node)
    rclpy.shutdown()