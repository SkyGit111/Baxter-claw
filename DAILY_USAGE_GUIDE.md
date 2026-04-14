# Baxter-Claw 日常使用指南

## 快速启动（日常使用）

### 方式1: 命令行启动（最简单）

```bash
# 1. 确保环境已配置（只需一次）
source ~/catkin_ws/baxter.sh
conda activate baxter-claw

# 2. 启动Bridge Server
cd ~/Baxter-claw
./start_bridge.sh

# 3. 使用API或Web界面控制机器人
```

### 方式2: Web界面启动（推荐）

```bash
# 终端1: 启动Bridge Server
./start_bridge.sh

# 终端2: 启动Web界面
python openclaw_plugin/web_interface.py

# 浏览器访问: http://localhost:5000
# 直接语音或文字输入指令
```

### 方式3: OpenClaw插件启动

```bash
# 1. 启动Bridge Server
./start_bridge.sh

# 2. 启动OpenClaw（如果已安装插件）
openclaw

# 3. 使用自然语言控制
```

---

## 日常使用场景

### 场景1: 简单抓取任务

**Web界面方式**:
1. 打开浏览器 http://localhost:5000
2. 输入或语音: "帮我拿一下红色的杯子"
3. 等待机器人完成
4. 输入: "放到左边"

**API方式**:
```bash
# 抓取
curl -X POST http://localhost:8420/primitives/pick_by_name \
  -H "Content-Type: application/json" \
  -d '{"object_name": "红色杯子", "arm": "right"}'

# 放置
curl -X POST http://localhost:8420/primitives/place \
  -H "Content-Type: application/json" \
  -d '{"arm": "right", "position": [0.5, 0.3, 0.0]}'
```

### 场景2: 物体识别

**Web界面**:
1. 点击"刷新图像"查看当前场景
2. 输入: "看看桌上有什么"
3. 查看识别结果

**API方式**:
```bash
curl -X POST http://localhost:8420/vision/describe_scene
```

### 场景3: 双臂协作

**Web界面**:
```
"用两只手拿起这个大盒子"
```

**API方式**:
```bash
curl -X POST http://localhost:8420/primitives/bimanual_pick \
  -H "Content-Type: application/json" \
  -d '{"object_name": "大盒子"}'
```

---

## 日常维护

### 每日启动检查清单

```bash
# 1. 检查Baxter状态
rostopic echo /robot/state -n 1

# 2. 检查深度相机
rs-enumerate-devices

# 3. 启动服务
./start_bridge.sh

# 4. 快速健康检查
curl http://localhost:8420/health
```

### 常见操作

#### 使能/禁用机器人
```bash
# 使能
curl -X POST http://localhost:8420/enable

# 禁用
curl -X POST http://localhost:8420/disable
```

#### 返回Home位置
```bash
# 单臂
curl -X POST http://localhost:8420/primitives/home \
  -H "Content-Type: application/json" \
  -d '{"arm": "right"}'

# 双臂
curl -X POST http://localhost:8420/primitives/home \
  -H "Content-Type: application/json" \
  -d '{"arm": "both"}'
```

#### 急停恢复
```bash
# 1. 按下急停后，先解除急停按钮
# 2. 重新使能
curl -X POST http://localhost:8420/enable

# 3. 返回Home
curl -X POST http://localhost:8420/primitives/home \
  -H "Content-Type: application/json" \
  -d '{"arm": "both"}'
```

---

## 性能优化建议

### 1. 启动优化

**创建启动别名**:
```bash
# 添加到 ~/.bashrc
alias baxter-start='cd ~/Baxter-claw && ./start_bridge.sh'
alias baxter-web='cd ~/Baxter-claw && python openclaw_plugin/web_interface.py'

# 使用
baxter-start
baxter-web
```

**后台运行**:
```bash
# Bridge Server后台运行
nohup ./start_bridge.sh > bridge.log 2>&1 &

# Web界面后台运行
nohup python openclaw_plugin/web_interface.py > web.log 2>&1 &

# 查看日志
tail -f bridge.log
tail -f web.log
```

### 2. 使用systemd服务（可选）

创建系统服务，开机自启：

```bash
# /etc/systemd/system/baxter-bridge.service
[Unit]
Description=Baxter-Claw Bridge Server
After=network.target

[Service]
Type=simple
User=cothink
WorkingDirectory=/home/cothink/Baxter-claw
Environment="ROS_MASTER_URI=http://011A08P0014.local:11311"
Environment="ROS_IP=YOUR_IP"
ExecStart=/home/cothink/miniconda3/envs/baxter-claw/bin/python -m bridge.server
Restart=on-failure

[Install]
WantedBy=multi-user.target

# 启用服务
sudo systemctl enable baxter-bridge
sudo systemctl start baxter-bridge
```

---

## 监控和日志

### 实时监控

**方法1: 查看Bridge Server日志**
```bash
# 如果前台运行，直接查看终端输出
# 如果后台运行
tail -f bridge.log
```

**方法2: 监控API状态**
```bash
# 持续监控健康状态
watch -n 5 'curl -s http://localhost:8420/health | jq'
```

**方法3: ROS话题监控**
```bash
# 监控机器人状态
rostopic echo /robot/state

# 监控关节状态
rostopic echo /robot/limb/right/endpoint_state
```

### 日志管理

**日志位置**:
- Bridge Server: 终端输出或 `bridge.log`
- ROS日志: `~/.ros/log/`
- Web界面: 终端输出或 `web.log`

**日志清理**:
```bash
# 清理ROS日志（保留最近7天）
rosclean purge -y

# 清理自定义日志
rm -f bridge.log web.log
```

---

## 故障排查（快速版）

### 问题1: Bridge Server无法启动
```bash
# 检查端口
lsof -i :8420

# 检查ROS
rostopic list | grep /robot/

# 重启
pkill -f "bridge.server"
./start_bridge.sh
```

### 问题2: 机器人不响应
```bash
# 检查使能状态
curl http://localhost:8420/status

# 重新使能
curl -X POST http://localhost:8420/enable
```

### 问题3: 视觉功能异常
```bash
# 检查相机
rs-enumerate-devices

# 重启相机
# 拔掉USB，等待5秒，重新插入

# 测试图像采集
curl -X POST http://localhost:8420/camera/capture
```

### 问题4: Web界面无法访问
```bash
# 检查Web服务
lsof -i :5000

# 重启Web界面
pkill -f "web_interface"
python openclaw_plugin/web_interface.py
```

---

## 最佳实践

### 1. 每日工作流程

```bash
# 早上启动
cd ~/Baxter-claw
source ~/catkin_ws/baxter.sh
conda activate baxter-claw
./start_bridge.sh

# 工作中
# 使用Web界面或API执行任务

# 晚上关闭
# Ctrl+C 停止Bridge Server
# 禁用机器人（可选）
curl -X POST http://localhost:8420/disable
```

### 2. 安全习惯

- ✅ 每次启动后先测试Home位置
- ✅ 执行新任务前先低速测试
- ✅ 保持急停按钮触手可及
- ✅ 定期检查工作空间
- ✅ 异常情况立即急停

### 3. 性能优化

- 🚀 使用Web界面的语音输入提高效率
- 🚀 常用任务创建快捷命令
- 🚀 批量任务使用API脚本
- 🚀 定期清理日志文件

---

## 与测试流程的对比

| 方面 | 测试流程 | 日常使用 |
|------|---------|---------|
| **启动时间** | 5-10分钟（完整检查） | 30秒（直接启动） |
| **检查项目** | 所有组件逐一验证 | 快速健康检查 |
| **使用方式** | 运行测试脚本 | Web界面/API |
| **关注点** | 发现问题 | 完成任务 |
| **日志** | 详细测试报告 | 关键错误 |
| **适用场景** | 首次部署、更新后 | 日常操作 |

---

## 何时使用测试流程

只在以下情况使用完整测试流程：

1. **首次部署** - 验证所有组件
2. **系统更新** - 确保兼容性
3. **故障排查** - 定位问题
4. **性能评估** - 生成报告
5. **定期检查** - 每周/每月一次

日常使用时，直接启动即可！

---

## 快速参考

```bash
# 启动
./start_bridge.sh

# 健康检查
curl http://localhost:8420/health

# 使能
curl -X POST http://localhost:8420/enable

# Home
curl -X POST http://localhost:8420/primitives/home \
  -d '{"arm":"right"}' -H "Content-Type: application/json"

# Web界面
python openclaw_plugin/web_interface.py
# 访问 http://localhost:5000

# 停止
Ctrl+C
```
