# API调用修复说明

## 问题总结

### 1. 夹爪控制 ✅ 工作正常
- 直接测试证明夹爪能动
- Bridge Server的API也能工作
- 问题：测试逻辑不合理（夹爪已经打开时再打开会失败）

### 2. VLM API参数错误 ❌ 需要修复
- 错误：`{"detail":[{"type":"missing","loc":["body"],"msg":"Field required"}]}`
- 原因：`describe_scene` 需要请求体，但测试脚本没有发送

---

## 正确的API调用方式

### 夹爪控制 ✅
```bash
# 校准夹爪（首次使用必须）
curl -X POST http://localhost:8420/gripper \
  -H "Content-Type: application/json" \
  -d '{"arm": "right", "action": "calibrate"}'

# 打开夹爪
curl -X POST http://localhost:8420/gripper \
  -H "Content-Type: application/json" \
  -d '{"arm": "right", "action": "open"}'

# 关闭夹爪
curl -X POST http://localhost:8420/gripper \
  -H "Content-Type: application/json" \
  -d '{"arm": "right", "action": "close"}'
```

### VLM场景描述 ✅ 修复
```bash
# ❌ 错误（缺少请求体）
curl -X POST http://localhost:8420/vision/describe_scene

# ✅ 正确（包含camera参数）
curl -X POST http://localhost:8420/vision/describe_scene \
  -H "Content-Type: application/json" \
  -d '{"camera": "right_hand"}'
```

### 物体定位 ✅
```bash
curl -X POST http://localhost:8420/vision/locate_object \
  -H "Content-Type: application/json" \
  -d '{"object_name": "红色杯子", "camera": "right_hand"}'
```

### 基于名称抓取 ✅
```bash
curl -X POST http://localhost:8420/vision/pick_by_name \
  -H "Content-Type: application/json" \
  -d '{"object_name": "红色杯子", "arm": "right", "camera": "right_hand"}'
```

---

## 测试脚本的问题

### 问题1: 夹爪测试逻辑不合理
```python
# 当前逻辑：
# 1. 获取初始位置
# 2. 发送打开命令
# 3. 检查位置是否变化

# 问题：如果夹爪已经打开，位置不会变化
```

**解决方案**：
1. 先校准夹爪
2. 先关闭，再打开（确保有变化）
3. 或者接受"已经在目标状态"的情况

### 问题2: VLM API调用缺少请求体
```python
# ❌ 错误
response = await client.post("/vision/describe_scene")

# ✅ 正确
response = await client.post("/vision/describe_scene", json={
    "camera": "right_hand"
})
```

---

## 立即测试

### 测试1: 夹爪控制（手动序列）
```bash
# 1. 校准
curl -X POST http://localhost:8420/gripper \
  -H "Content-Type: application/json" \
  -d '{"arm": "right", "action": "calibrate"}'

# 等待3秒

# 2. 关闭
curl -X POST http://localhost:8420/gripper \
  -H "Content-Type: application/json" \
  -d '{"arm": "right", "action": "close"}'

# 等待2秒，观察夹爪是否关闭

# 3. 打开
curl -X POST http://localhost:8420/gripper \
  -H "Content-Type: application/json" \
  -d '{"arm": "right", "action": "open"}'

# 观察夹爪是否打开
```

### 测试2: VLM场景描述
```bash
# 确保QWEN_API_KEY已设置
export QWEN_API_KEY="sk-bd990626c84a4142b9581f13c5317522"

# 重启Bridge Server（如果刚设置API密钥）
# pkill -f bridge.server
# ./start_bridge.sh

# 测试场景描述
curl -X POST http://localhost:8420/vision/describe_scene \
  -H "Content-Type: application/json" \
  -d '{"camera": "right_hand"}'
```

---

## 下一步

1. **夹爪控制已经工作** ✅
   - 直接测试证明能动
   - API调用也能工作
   - 只是测试脚本逻辑需要改进

2. **VLM API需要正确的请求体** ✅
   - 已提供正确的调用方式
   - 需要确保API密钥已设置

3. **建议使用 test_real_baxter_grasp.py** ✅
   - 这个脚本直接使用Driver，更可靠
   - 已经过验证能真正控制机器人

---

## 总结

**好消息**：
- ✅ 机器人连接正常
- ✅ 夹爪控制工作
- ✅ Bridge Server正确使用Baxter Driver

**需要注意**：
- API调用需要正确的请求体格式
- 测试逻辑需要考虑当前状态
- VLM功能需要API密钥

系统已经基本可用！建议使用 `test_real_baxter_grasp.py` 进行完整测试。
