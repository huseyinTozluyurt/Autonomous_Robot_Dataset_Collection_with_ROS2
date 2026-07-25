import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
import sys, select, termios, tty

msg = """
Control DeliveryBot!
---------------------------
Moving around:
   w
a  s  d

space key : force stop
CTRL-C to quit
"""

class ManualDriveNode(Node):
    def __init__(self):
        super().__init__('manual_drive_node')
        self.pub = self.create_publisher(Twist, '/cmd_vel', 10)
        self.speed = 0.2
        self.turn = 0.5

    def getKey(self):
        tty.setraw(sys.stdin.fileno())
        select.select([sys.stdin], [], [], 0.1)
        key = sys.stdin.read(1)
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, termios.tcgetattr(sys.stdin))
        return key

    def run(self):
        print(msg)
        try:
            while rclpy.ok():
                key = self.getKey()
                twist = Twist()
                if key == 'w':
                    twist.linear.x = self.speed
                elif key == 's':
                    twist.linear.x = -self.speed
                elif key == 'a':
                    twist.angular.z = self.turn
                elif key == 'd':
                    twist.angular.z = -self.turn
                elif key == ' ':
                    twist.linear.x = 0.0
                    twist.angular.z = 0.0
                elif key == '\x03':  # Ctrl-C
                    break
                
                self.pub.publish(twist)
        except Exception as e:
            print(e)

def main(args=None):
    settings = termios.tcgetattr(sys.stdin)
    rclpy.init(args=args)
    node = ManualDriveNode()
    node.run()
    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, settings)
    rclpy.shutdown()