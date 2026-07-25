# 🤖 Indoor Autonomous Delivery Robot (ROS 2 Workspace)

[![ROS 2](https://img.shields.io/badge/ROS2-Humble%20%7C%20Jazzy-blue?logo=ros&logoColor=white)](https://docs.ros.org/)
[![Python](https://img.shields.io/badge/Python-3.10%2B-green?logo=python&logoColor=white)](https://www.python.org/)
[![C++ / Embedded](https://img.shields.io/badge/Microcontrollers-Arduino%20%2F%20STM32-orange?logo=arduino&logoColor=white)](https://www.arduino.cc/)
[![License](https://img.shields.io/badge/License-MIT-brightgreen.svg)](LICENSE)

An industrial, event-driven **ROS 2 modular architecture** designed for indoor autonomous navigation, sensor fusion, real-time safety filtering, and synchronized multi-modal data collection for **Machine Learning (Behavioral Cloning & Imitation Learning)**.

The system runs on a **Raspberry Pi 4** central compute node, communicating asynchronously with an **Arduino Uno** (differential motor driver & MPU6050 IMU telemetry), an **STM32F103** microcontroller (4-channel HC-SR04 ultrasonic array), and a **Konftel Cam10 USB camera** streaming via V4L2.

---

## 📸 System Overview & Hardware Architecture

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


📁 Repository & Package Structure
The repository is structured as a standard colcon workspace (deliverybot_ws/src):


deliverybot_ws/
└── src/
    ├── deliverybot_bringup/         # System launch files and parameter YAML configs
    ├── deliverybot_camera/          # V4L2 USB camera stream publisher
    ├── deliverybot_description/     # Robot URDF / 3D spatial models
    ├── deliverybot_interfaces/      # Custom msg / srv interface definitions
    ├── deliverybot_manual_control/  # Non-blocking terminal teleop keyboard driver
    ├── deliverybot_navigation/     # Autonomous trajectory & path planning
    ├── deliverybot_perception/     # Computer vision & segmentation algorithms
    ├── deliverybot_recording/      # Multi-modal machine learning dataset recorder
    ├── deliverybot_safety/         # Dynamic ultrasonic obstacle avoidance layer
    └── deliverybot_stm32/          # Serial bridges for Arduino & STM32 hardware
