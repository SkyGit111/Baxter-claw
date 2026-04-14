# Baxter Hand-Eye Calibration 完整操作流程

## 日期：2026-04-12

## 环境信息
- **Baxter 机器人 IP**: 011A08P0014.local
- **相机**: Intel RealSense D455
- **标定类型**: Eye-on-hand (相机安装在右臂末端)
- **ArUco Marker ID**: 582
- **Marker 尺寸**: 0.1 米

---

## 前置条件

1. Baxter 机器人已开机并连接到网络
2. RealSense D455 相机已连接到工作站
3. ArUco marker (ID 582) 已打印并固定在工作区域
4. 工作站已安装：
   - ROS Noetic
   - easy_handeye
   - aruco_ros
   - realsense-ros

---

## 完整操作流程

### 步骤 1: 打开终端并设置 Baxter 环境

**重要**: 不要激活 conda 环境，使用系统 Python 和 ROS。

```bash
cd ~/catkin_ws
./baxter.sh
```

**验证环境设置**:
```bash
echo $ROS_MASTER_URI
# 应该输出: http://011A08P0014.local:11311

echo $ROS_IP
# 应该输出你的工作站 IP
```

---

### 步骤 2: 验证 Baxter 连接

```bash
# 检查 Baxter topics
rostopic list | grep robot

# 应该看到:
# /robot/state
# /robot/joint_states
# /robot/limb/right/...
# 等等

# 检查 TF
rosrun tf tf_echo base right_gripper

# 应该看到 base 到 right_gripper 的变换
```

---

### 步骤 3: 启动完整的标定系统

在**同一个终端**中运行：

```bash
roslaunch easy_handeye baxter_calibrate.launch
```

这个 launch 文件会启动：
1. RealSense 相机节点
2. ArUco marker 检测节点
3. easy_handeye 标定服务器
4. RViz 可视化
5. rqt_easy_handeye GUI

**等待所有节点启动** (大约 10-15 秒)

---

### 步骤 4: 验证系统状态

在**另一个终端**中（也要先 source baxter.sh）：

```bash
cd ~/catkin_ws
./baxter.sh

# 检查所有节点是否运行
rosnode list

# 应该看到:
# /camera/realsense2_camera
# /aruco_single
# /baxter_d455_handeye_calibration_eye_on_hand/easy_handeye_calibration_server
# /rviz_xxx
# 等等

# 检查 ArUco marker 是否被检测到
rostopic echo /aruco_single/result -n 1

# 如果看到输出，说明 marker 被检测到了

# 检查完整的 TF 树
rosrun tf view_frames
# 会生成 frames.pdf，查看 TF 树结构
```

---

### 步骤 5: 使用 RViz 和 GUI 进行标定

此时应该有三个窗口打开：

#### 窗口 1: RViz
- 左侧面板：显示 TF 树和坐标系
- 中间：3D 可视化
  - 应该看到 Baxter 机器人模型
  - 相机坐标系 (camera_optical_frame)
  - ArUco marker 坐标系 (aruco_marker_frame)
- 底部：相机图像（带 marker 检测框）

**RViz 配置检查**:
- Fixed Frame: 设置为 `base` 或 `torso`
- 添加 TF display
- 添加 RobotModel display
- 添加 Image display (topic: /camera/color/image_raw)

#### 窗口 2: rqt_easy_handeye
标定控制面板，包含：
- 顶部：标定配置信息
- 中间：样本列表（初始为空）
- 底部：四个按钮
  - **Take sample**: 采集当前姿态
  - **Remove sample**: 删除选中的样本
  - **Compute**: 计算标定结果
  - **Save**: 保存标定结果

#### 窗口 3: rqt_image_view (可选)
显示相机图像和 ArUco marker 检测结果

---

### 步骤 6: 采集标定样本

**目标**: 采集 10-15 个不同姿态的样本

**采集原则**:
1. **确保 marker 始终在相机视野内**
2. **覆盖不同的距离**: 近距离 (30cm) 到远距离 (80cm)
3. **覆盖不同的角度**: 正面、侧面、倾斜
4. **覆盖工作空间的不同位置**: 左、右、前、后、上、下

**操作步骤**:

1. **移动 Baxter 右臂到第一个位置**
   - 可以手动移动（按住 cuff 按钮）
   - 或使用 Baxter 的 joint position 控制

2. **在 RViz 中验证**:
   - 确认能看到绿色的 ArUco marker 检测框
   - 确认 marker 在图像中心附近（不要太靠边缘）

3. **在 rqt_easy_handeye 中点击 "Take sample"**
   - 样本列表中会出现新的条目
   - 显示样本编号和时间戳

4. **移动到下一个位置，重复步骤 1-3**

**推荐的采集顺序**:

```
样本 1-3:   正面，不同距离 (近、中、远)
样本 4-6:   左侧，不同距离
样本 7-9:   右侧，不同距离
样本 10-12: 倾斜角度 (向左倾、向右倾、向前倾)
样本 13-15: 极限位置 (工作空间边界)
```

**注意事项**:
- 每次采集前等待 1-2 秒，确保机器人静止
- 如果某个样本质量不好（marker 检测不稳定），可以删除重新采集
- 样本越多越好，但质量比数量更重要

---

### 步骤 7: 计算标定结果

采集完所有样本后：

1. **点击 "Compute" 按钮**
   - 系统会计算相机到机械臂末端的变换
   - 计算时间约 1-5 秒

2. **查看标定结果**
   - 终端会输出标定矩阵
   - GUI 会显示标定误差（reprojection error）

3. **评估标定质量**:
   ```
   优秀: reprojection error < 2 像素
   良好: reprojection error < 5 像素
   可接受: reprojection error < 10 像素
   需重新标定: reprojection error > 10 像素
   ```

4. **如果误差太大**:
   - 删除误差最大的几个样本
   - 重新点击 "Compute"
   - 或者重新采集更多高质量样本

---

### 步骤 8: 保存标定结果

标定结果满意后：

1. **点击 "Save" 按钮**
   - 标定结果会保存到 ROS 参数服务器
   - 同时保存到配置文件

2. **验证保存成功**:
   ```bash
   # 查看保存的参数
   rosparam get /baxter_d455_handeye_calibration_eye_on_hand
   
   # 应该看到标定矩阵
   ```

3. **标定文件位置**:
   ```
   ~/.ros/easy_handeye/baxter_d455_handeye_calibration_eye_on_hand.yaml
   ```

---

### 步骤 9: 应用标定结果

标定完成后，在使用相机时需要发布标定的变换：

```bash
# 启动标定结果发布节点
roslaunch easy_handeye publish.launch eye_on_hand:=true \
  namespace_prefix:=baxter_d455_handeye_calibration
```

这会在 TF 树中发布 `right_gripper` → `camera_optical_frame` 的变换。

---

## 常见问题排查

### 问题 1: RViz 中看不到 Baxter 的坐标系

**原因**: RViz 没有连接到 Baxter 的 ROS master

**解决**:
```bash
# 确认环境变量
echo $ROS_MASTER_URI
# 必须是: http://011A08P0014.local:11311

# 如果不对，重新 source
cd ~/catkin_ws
./baxter.sh
```

### 问题 2: RViz 中看不到 ArUco marker

**原因**: 相机或 aruco_ros 节点没有连接到 Baxter 的 ROS master

**解决**: 确保在启动 roslaunch 前已经 source baxter.sh

### 问题 3: ArUco marker 检测不稳定

**可能原因**:
- 光照不足或过强
- Marker 打印质量差
- Marker 尺寸配置错误
- 相机距离太远或太近

**解决**:
- 改善光照条件
- 重新打印高质量 marker
- 检查 launch 文件中的 marker 尺寸参数
- 调整相机距离 (推荐 30-80cm)

### 问题 4: 标定误差很大

**可能原因**:
- 样本质量差
- 样本分布不均匀
- 相机内参不准确

**解决**:
- 删除误差大的样本
- 重新采集，覆盖更多角度和位置
- 先进行相机内参标定

### 问题 5: RViz 不断自动重启

**原因**: launch 文件中 RViz 的 respawn 参数设置为 true

**解决**: 已修复 - 将 `calibrate.launch` 中的 `respawn="true"` 改为 `respawn="false"`

**位置**: `/home/cothink/catkin_ws/src/easy_handeye/easy_handeye/launch/calibrate.launch` 第 90 行

### 问题 6: 多个 RViz 窗口自动打开

**原因**: roslaunch 会自动启动 RViz，如果手动再启动会有多个

**解决**: 只使用 roslaunch 启动，不要手动启动 RViz

---

## 标定后的使用

标定完成后，在 Baxter-Claw 系统中使用：

1. **更新 config/baxter.yaml**:
   ```yaml
   depth_camera_transform:
     translation: [x, y, z]  # 从标定结果复制
     rotation: [qx, qy, qz, qw]  # 从标定结果复制
   ```

2. **启动 Bridge Server 时会自动加载标定结果**

3. **验证标定效果**:
   - 使用 pick_by_name 抓取物体
   - 检查定位精度
   - 如果精度不够，重新标定

---

## 完整命令总结

```bash
# 终端 1: 启动标定系统
cd ~/catkin_ws
./baxter.sh
roslaunch easy_handeye baxter_calibrate.launch

# 终端 2: 验证和调试（可选）
cd ~/catkin_ws
./baxter.sh
rostopic list
rosnode list
rosrun tf view_frames
```

---

## 注意事项

1. **不要激活 conda 环境** - 使用系统 ROS
2. **所有终端都要 source baxter.sh** - 确保连接到同一个 ROS master
3. **标定前确认 Baxter 已使能** - 否则无法移动机械臂
4. **采集样本时保持机器人静止** - 避免运动模糊
5. **定期保存标定结果** - 避免意外丢失
6. **记录标定日期和条件** - 便于追溯和重现

---

## 参考资料

- easy_handeye 文档: https://github.com/IFL-CAMP/easy_handeye
- aruco_ros 文档: https://github.com/pal-robotics/aruco_ros
- Baxter SDK 文档: http://sdk.rethinkrobotics.com/

---

**文档版本**: 1.0  
**最后更新**: 2026-04-12  
**作者**: Baxter-Claw Team