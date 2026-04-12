#!/usr/bin/env python
"""启动 Baxter-Claw Bridge Server

使用前请确保：
1. 已运行 cd ~/catkin_ws && ./baxter.sh
2. 已激活 conda activate baxter-claw
3. 在项目根目录运行此脚本
"""

import sys
import os

# Add ROS paths
_ros_paths = ['/opt/ros/noetic/lib/python3/dist-packages', '/usr/lib/python3/dist-packages']
for path in _ros_paths:
    if path not in sys.path:
        sys.path.append(path)

# Check if in correct directory
if not os.path.exists('bridge/server.py'):
    print("✗ 错误: 请在 Baxter-claw 项目根目录运行此脚本")
    sys.exit(1)

print("="*60)
print("Baxter-Claw Bridge Server")
print("="*60)
print()

# Import and run server
from bridge.server import main

if __name__ == "__main__":
    main()