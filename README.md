# Indoor Autonomous Delivery Robot (ROS 2 Workspace)

[![ROS 2](https://img.shields.io/badge/ROS2-Humble%20%7C%20Jazzy-blue?logo=ros&logoColor=white)](https://docs.ros.org/)
[![Python](https://img.shields.io/badge/Python-3.10%2B-green?logo=python&logoColor=white)](https://www.python.org/)
[![C++ / Embedded](https://img.shields.io/badge/Microcontrollers-Arduino%20%2F%20STM32-orange?logo=arduino&logoColor=white)](https://www.arduino.cc/)
[![License](https://img.shields.io/badge/License-MIT-brightgreen.svg)](LICENSE)

An industrial, event-driven **ROS 2 modular architecture** designed for indoor autonomous navigation, sensor fusion, real-time safety filtering, and synchronized multi-modal data collection for **Machine Learning (Behavioral Cloning & Imitation Learning)**.

The system runs on a **Raspberry Pi 4** central compute node, communicating asynchronously with an **Arduino Uno** (differential motor driver & MPU6050 IMU telemetry), an **STM32F103** microcontroller (4-channel HC-SR04 ultrasonic array), and a **Konftel Cam10 USB camera** streaming via V4L2.

---

## System Overview & Hardware Architecture

```text
                     +-----------------------------------+
                     |  Raspberry Pi 4 (Ubuntu / ROS 2)  |
                     +-----------------+-----------------+
                                       |
         +-----------------------------+-----------------------------+
         |                             |                             |
    USB Serial                    USB Serial                     USB Video
  (/dev/ttyUSB0)                (/dev/ttyUSB1)             (/dev/video0 via V4L2)
         |                             |                             |
         v                             v                             v
+------------------+          +------------------+          +------------------+
|   Arduino Uno    |          |    STM32F103     |          |  Konftel Cam10   |
| (Motor Controller|          | (Distance Array) |          |  (30 FPS Webcam) |
|   + MPU6050)     |          +------------------+          +------------------+
+--------+---------+                   |
         |                             |
         v                             v
  2x L298N Drivers            4x HC-SR04 Sensors
 + 4x DC Motors               (Front, Left, Right, Back)
```

## Hardware Architecture

| Component | Hardware Specification | Function / Interface |
| :--- | :--- | :--- |
| **Central Compute** | Raspberry Pi 4 Model B (4GB/8GB) | High-level orchestration, ROS 2 middleware, dataset generation |
| **Primary Vision** | Konftel Cam10 USB Camera | 640x480 @ 30 FPS (`/dev/video0` via standard V4L2) |
| **Motor Controller** | Arduino Uno + 2x L298N H-Bridges | 4x DC motors driven via continuous speed ASCII serial commands |
| **Inertial Unit** | MPU6050 6-DOF Gyro/Accel | Reads yaw angle onboard, streams continuous `IMU yaw=...` telemetry |
| **Proximity Perception** | STM32F103 ("Blue Pill") | Hardware TIM2 (1µs resolution) polling 4x HC-SR04 sensors |


## 📁 Package Architecture

| Package Name | Description & Functionality |
| :--- | :--- |
| **`deliverybot_bringup`** | System launch files and parameter YAML configs |
| **`deliverybot_camera`** | V4L2 USB camera stream publisher (`/camera/image_raw`) |
| **`deliverybot_description`** | Robot URDF models and spatial transformations |
| **`deliverybot_interfaces`** | Custom ROS 2 `.msg` and `.srv` interface definitions |
| **`deliverybot_manual_control`** | Non-blocking terminal keyboard teleop driver |
| **`deliverybot_navigation`** | Autonomous trajectory and path planning nodes |
| **`deliverybot_perception`** | Computer vision and segmentation algorithms |
| **`deliverybot_recording`** | Multi-modal machine learning dataset recorder |
| **`deliverybot_safety`** | Dynamic ultrasonic obstacle avoidance layer |
| **`deliverybot_stm32`** | Serial bridges for Arduino motor driver & STM32 hardware |


## 🕹️ Core ROS 2 Nodes & Architecture

### 1. `guided_motor_control_node`
* **Package:** `deliverybot_stm32`
* **Hardware Interface:** `/dev/ttyUSB0` (Arduino Uno @ 115200 baud)
* **Subscribed Topics:** `/cmd_vel` (`geometry_msgs/msg/Twist`)
* **Published Topics:** `/imu/yaw` (`std_msgs/msg/Float32`)
* **Description:** Translates high-level ROS 2 velocity commands into ASCII motor drive frames for the Arduino motor controller. Reads onboard MPU6050 telemetry, publishes continuous yaw heading feedback, and executes closed-loop drift corrections using local state calibration files (`~/.ros/deliverybot/lateral_error.txt`).

---

### 2. `serial_bridge_node`
* **Package:** `deliverybot_stm32`
* **Hardware Interface:** `/dev/ttyUSB1` (STM32F103 "Blue Pill")
* **Published Topics:** `/ultrasonic` (`std_msgs/msg/Float32MultiArray`)
* **Description:** Asynchronously polls the STM32 microcontroller to parse 4-channel HC-SR04 ultrasonic time-of-flight measurements. Publishes structured distance arrays (`[front, left, right, back]`) in centimeters at high frequency.

---

### 3. `camera_node`
* **Package:** `deliverybot_camera`
* **Hardware Interface:** `/dev/video0` (Konftel Cam10 via V4L2)
* **Published Topics:** `/camera/image_raw` (`sensor_msgs/msg/Image`)
* **Description:** Captures high-definition webcam frames at 640x480 resolution (30 FPS) using OpenCV's V4L2 backend and converts raw frames into standardized ROS 2 `Image` messages via `cv_bridge`.

---

### 4. `cmd_vel_ml_logger_node`
* **Package:** `deliverybot_recording`
* **Subscribed Topics:** * `/camera/image_raw` (`sensor_msgs/msg/Image`)
  * `/cmd_vel` (`geometry_msgs/msg/Twist`)
  * `/imu/yaw` (`std_msgs/msg/Float32`)
  * `/ultrasonic` (`std_msgs/msg/Float32MultiArray`)
* **Description:** Multi-modal data acquisition engine for Imitation Learning and Behavioral Cloning. Captures synchronized 30 FPS camera frames alongside nanosecond-timestamped CSV records of velocity requests, wheel PWMs, heading angles, and proximity measurements.

---

### 5. `obstacle_avoidance_node`
* **Package:** `deliverybot_safety`
* **Subscribed Topics:** * `/cmd_vel_input` (`geometry_msgs/msg/Twist`)
  * `/ultrasonic` (`std_msgs/msg/Float32MultiArray`)
* **Published Topics:** `/cmd_vel` (`geometry_msgs/msg/Twist`)
* **Description:** Active safety multiplexer node. Evaluates incoming velocity requests against real-time ultrasonic sensor measurements from the STM32. Enforces dynamic speed reduction or emergency stopping (< 25 cm) before publishing safe commands to the motor controller.

---

### 6. `manual_drive_node`
* **Package:** `deliverybot_manual_control`
* **Published Topics:** `/cmd_vel_input` (`geometry_msgs/msg/Twist`)
* **Description:** Non-blocking terminal keyboard teleoperation interface (`W/A/S/D/Space`). Converts user keypresses into standard linear and angular velocity command inputs.




## 📊 Dataset & Machine Learning Logging Format

Data collected via `cmd_vel_ml_logger_node` is organized inside `dataset/` for direct model ingestion (e.g., PyTorch / TensorFlow End-to-End Behavioral Cloning or Imitation Learning):

```text
dataset/
└── Corridor1_ML/
    ├── Corridor1_ML_ml_dataset.csv
    └── images/
        ├── Corridor1_ML_frame_000000.jpg
        ├── Corridor1_ML_frame_000001.jpg
        └── Corridor1_ML_frame_000002.jpg
```
## Logged CSV File Structure
```text
timestamp_sec,timestamp_nanosec,image_filename,cmd_linear_x,cmd_angular_z,est_left_pwm,est_right_pwm,imu_yaw,us_front,us_left,us_right,us_back
1784822405,123456789,Corridor1_ML_frame_000000.jpg,0.2000,0.0000,220,220,12.45,150.0,35.2,38.1,210.0
```
**Precision Timestamping:** Both timestamp_sec and timestamp_nanosec are synchronized directly from ROS 2 clock headers to enable sub-millisecond temporal interpolation during neural network training.

## Prerequisites

* **Operating System:** Ubuntu 22.04 LTS / 24.04 LTS or Raspberry Pi OS (64-bit)
* **ROS2:** Humble Hawksbill or Jazzy Jalisco
* **Dependencies:**
```text
sudo apt update
sudo apt install -y python3-colcon-common-extensions python3-rosdep python3-pip v4l-utils
pip3 install pyserial opencv-python cv-bridge
```

## Cloning & Building Workspace

```bash
# Clone the repository
git clone [https://github.com/huseyinTozluyurt/Autonomous_Robot_Dataset_Collection_with_ROS2.git](https://github.com/huseyinTozluyurt/Autonomous_Robot_Dataset_Collection_with_ROS2.git) ~/deliverybot_ws

# Navigate to workspace
cd ~/deliverybot_ws

# Install ROS 2 dependencies
rosdep update
rosdep install --from-paths src --ignore-src -r -y

# Build the workspace
colcon build

# Source workspace environment
source install/setup.bash
```

### 2. Running Data Collection & Driving | Multi-Terminal Execution Quick Reference
Open separate terminals (or use tmux), source install/setup.bash in each, and run:

```bash
source ~/deliverybot_ws/install/setup.bash
```

#### 1️⃣ Terminal 1 — Guided Motor Driver (Arduino + IMU)
```bash
ros2 run deliverybot_stm32 guided_motor_control_node
```

#### 2️⃣ Terminal 2 — Distance Sensor Array Bridge (STM32)
```bash
ros2 run deliverybot_stm32 serial_bridge_node
```

#### 3️⃣ Terminal 3 — Konftel USB Web Camera Publisher
```bash
ros2 run deliverybot_camera camera_node
```

#### 4️⃣ Terminal 4 — Obstacle Avoidance Safety Filter
```bash
ros2 run deliverybot_safety obstacle_avoidance_node
```

#### 5️⃣ Terminal 5 — Multi-Modal Dataset & Vision Logger
> **Note:** Specify your target recording session name dynamically via ROS 2 CLI parameters:
```bash
ros2 run deliverybot_recording cmd_vel_ml_logger_node --ros-args -p session_name:=Corridor1_ML
```

#### 6️⃣ Terminal 6 — Teleoperation Keyboard Control
```bash
ros2 run deliverybot_manual_control manual_drive_node
```







