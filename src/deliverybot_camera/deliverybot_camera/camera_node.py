import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
import cv2
from cv_bridge import CvBridge

class CameraNode(Node):
    def __init__(self):
        super().__init__('camera_node')

        # Declare ROS2 parameter for device ID (default 0 for /dev/video0)
        self.declare_parameter('device_id', 0)
        self.device_id = self.get_parameter('device_id').value

        # Publisher setup
        self.publisher_ = self.create_publisher(Image, '/camera/image_raw', 10)
        self.timer = self.create_timer(0.033, self.timer_callback)  # ~30 FPS
        self.bridge = CvBridge()

        # Open camera using V4L2 directly
        self.get_logger().info(f"Opening Konftel Camera on /dev/video{self.device_id} with V4L2 backend...")
        self.cap = cv2.VideoCapture(self.device_id, cv2.CAP_V4L2)

        # Force standard capture resolution and frame rate
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.cap.set(cv2.CAP_PROP_FPS, 30)

        if not self.cap.isOpened():
            self.get_logger().error(f"Failed to open camera on /dev/video{self.device_id}!")
        else:
            self.get_logger().info(f"Konftel Camera initialized successfully on /dev/video{self.device_id}")

    def timer_callback(self):
        if not self.cap.isOpened():
            return

        ret, frame = self.cap.read()
        if ret:
            # Convert OpenCV frame to ROS2 Image message
            msg = self.bridge.cv2_to_imgmsg(frame, encoding='bgr8')
            msg.header.stamp = self.get_clock().now().to_msg()
            msg.header.frame_id = 'camera_frame'
            self.publisher_.publish(msg)
        else:
            self.get_logger().warn("Failed to capture frame from Konftel Cam10")

    def destroy_node(self):
        if hasattr(self, 'cap') and self.cap.isOpened():
            self.cap.release()
            self.get_logger().info("Camera device released.")
        super().destroy_node()

def main(args=None):
    rclpy.init(args=args)
    node = CameraNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()