# Baxter-Claw 真机测试快速参考

## 一键启动

```bash
# 1. 快速启动Bridge Server
./quick_start.sh

# 2. 运行系统测试（在新终端）
python run_system_test.py

# 3. 启动Web界面（在新终端）
python openclaw_plugin/web_interface.py
```

## 测试命令速查

### 环境准备
```bash
# 配置ROS环境
cd ~/catkin_ws && source ./baxter.sh && cd ~/Baxter-claw

# 激活conda环境
conda activate baxter-claw

# 设置API密钥
export QWEN_API_KEY="your-key-here"
```

### 硬件检查
```bash
# 检查Baxter连接
rostopic list | grep /robot/

# 检查深度相机
lsusb | grep 8086:0b5c
rs-enumerate-devices

# 完整硬件检查
./check_baxter.sh
```

### 启动服务
```bash
# 方法1: 快速启动（推荐）
./quick_start.sh

# 方法2: 完整启动脚本
./start_with_baxter.sh

# 方法3: 直接启动
python -m bridge.server
```

### 测试API
```bash
# 健康检查
curl http://localhost:8420/health

# 获取状态
curl http://localhost:8420/status

# 使能机器人
curl -X POST http://localhost:8420/enable

# 打开夹爪
curl -X POST http://localhost:8420/primitives/gripper \
  -H "Content-Type: application/json" \
  -d '{"arm": "right", "command": "open"}'

# 返回Home
curl -X POST http://localhost:8420/primitives/home \
  -H "Content-Type: application/json" \
  -d '{"arm": "right"}'
```

### 运行测试
```bash
# 完整系统测试
python run_system_test.py

# 从指定阶段开始
python run_system_test.py --stage 3

# 跳过硬件检查
python run_system_test.py --skip-hardware

# 不执行实际运动
python run_system_test.py --no-motion

# 单独测试脚本
python test_baxter_connection.py      # ROS连接测试
python test_real_baxter_grasp.py      # 完整抓取测试
python test_dual_arm_plugin.py        # 双臂测试
python test_multiview_vlm.py          # 多视角VLM测试
```

### Web界面
```bash
# 启动Web界面
python openclaw_plugin/web_interface.py

# 访问
# http://localhost:5000
```

## 测试阶段说明

### 阶段0: 环境检查
- ROS环境变量
- Conda环境
- Python依赖
- 配置文件
- API密钥

### 阶段1: 硬件检查
- Baxter连接（ROS话题）
- RealSense D455连接
- 设备枚举

### 阶段2: Bridge Server
- 服务器连接
- 健康检查
- 状态查询

### 阶段3: 基础控制
- 机器人使能
- 夹爪控制
- Home位置

### 阶段4: 视觉系统
- 图像采集
- 场景描述
- 物体定位

### 阶段5: Web界面
- Web服务器
- 摄像头端点
- 聊天接口

## 常见问题排查

### Bridge Server无法启动
```bash
# 检查端口占用
lsof -i :8420

# 检查ROS环境
echo $ROS_MASTER_URI
rostopic list

# 检查Python环境
which python
python --version
conda env list
```

### 机器人无法使能
```bash
# 检查Baxter状态
rostopic echo /robot/state -n 1

# 检查急停按钮
# 确保急停按钮未按下

# 重启Baxter
# 按下Baxter背后的电源按钮
```

### 深度相机无法访问
```bash
# 检查USB连接
lsusb | grep Intel

# 检查权限
sudo chmod 666 /dev/bus/usb/*/*

# 重新插拔USB线

# 测试相机
realsense-viewer
```

### VLM功能不工作
```bash
# 检查API密钥
echo $QWEN_API_KEY

# 测试网络连接
curl https://dashscope.aliyuncs.com

# 检查配置
cat config/baxter.yaml | grep -A 5 vlm
```

## 安全注意事项

### 运动测试前
- [ ] 确保工作空间内无障碍物
- [ ] 确保无人员在机器人运动范围内
- [ ] 急停按钮触手可及
- [ ] 首次测试使用低速度
- [ ] 准备好随时按下急停

### 测试过程中
- [ ] 密切观察机器人运动
- [ ] 发现异常立即按下急停
- [ ] 不要站在机器人运动路径上
- [ ] 保持安全距离（至少1米）

### 紧急情况处理
1. **立即按下急停按钮**
2. 等待机器人完全停止
3. 检查是否有损坏
4. 记录问题现象
5. 分析日志文件

## 测试数据记录

### 测试日志位置
- Bridge Server日志: 终端输出
- 测试报告: `test_report_*.txt`
- 采集图像: `test_*.jpg`
- ROS日志: `~/.ros/log/`

### 性能指标
- 启动时间: Bridge Server启动到ready
- 响应时间: API调用到返回
- 运动时间: 各个primitive执行时间
- 识别准确率: VLM物体识别成功率
- 定位精度: 抓取成功率

## 下一步

测试通过后，可以进行：
1. 调整安全参数（workspace limits）
2. 优化运动速度
3. 校准手眼关系
4. 训练特定场景
5. 开发自定义技能

## 获取帮助

- 查看完整文档: `REAL_ROBOT_TEST_GUIDE.md`
- 查看API文档: http://localhost:8420/docs
- 查看项目README: `README.md`
- 提交Issue: GitHub Issues
