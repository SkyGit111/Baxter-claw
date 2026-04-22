#!/usr/bin/env python
"""直接测试夹爪控制"""

import sys
_ros_paths = ['/opt/ros/noetic/lib/python3/dist-packages', '/usr/lib/python3/dist-packages']
for path in _ros_paths:
    if path not in sys.path:
        sys.path.append(path)

from bridge.drivers.baxter_driver import BaxterDriver
import time

print("初始化驱动...")
driver = BaxterDriver(use_depth_camera=False)

print("连接机器人...")
if not driver.connect():
    print("连接失败")
    sys.exit(1)

print("使能机器人...")
if not driver.enable():
    print("使能失败")
    sys.exit(1)

print("\n获取初始夹爪状态...")
pos, force = driver.get_gripper_state('right')
print(f"位置: {pos}, 力: {force}")

print("\n校准夹爪...")
result = driver.gripper_command('right', 'calibrate')
print(f"校准结果: {result}")
time.sleep(3)

print("\n打开夹爪...")
result = driver.gripper_command('right', 'open')
print(f"打开结果: {result}")
time.sleep(3)

pos, force = driver.get_gripper_state('right')
print(f"打开后 - 位置: {pos}, 力: {force}")

print("\n关闭夹爪...")
result = driver.gripper_command('right', 'close')
print(f"关闭结果: {result}")
time.sleep(3)

pos, force = driver.get_gripper_state('right')
print(f"关闭后 - 位置: {pos}, 力: {force}")

print("\n测试完成")
