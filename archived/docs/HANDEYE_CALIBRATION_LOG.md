# Baxter Hand-Eye Calibration 完整流程记录

## 日期：2026-04-12

## 环境信息
- Baxter 机器人 IP: 011A08P0014.local
- 相机：Intel RealSense D455
- 标定类型：Eye-on-hand (相机安装在机械臂上)
- ArUco Marker ID: 582

## 步骤 1: 设置 Baxter 环境

```bash
cd ~/catkin_ws
source baxter.sh
```

**说明：** 这会设置 ROS_MASTER_URI 指向 Baxter 机器人，确保所有节点在同一个 ROS 网络中。

**执行时间：** 