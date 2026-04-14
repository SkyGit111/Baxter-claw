# Home位姿更新说明

## 已完成的更改

### 1. 更新了Home位姿定义 ✅

**文件**: `bridge/primitives.py`

**旧的Home位姿**（默认值）:
```python
'right': {
    'right_s0': 0.0,
    'right_s1': -0.55,
    'right_e0': 0.0,
    'right_e1': 0.75,
    'right_w0': 0.0,
    'right_w1': 1.26,
    'right_w2': 0.0,
}
```

**新的Home位姿**（当前舒适位置）:
```python
'right': {
    'right_s0': 0.076316,
    'right_s1': -0.981748,
    'right_e0': 1.140515,
    'right_e1': 1.890631,
    'right_w0': -0.641204,
    'right_w1': 1.038888,
    'right_w2': 0.479752,
},
'left': {
    'left_s0': -0.079384,
    'left_s1': -0.998621,
    'left_e0': -1.188068,
    'left_e1': 1.937801,
    'left_w0': 0.671884,
    'left_w1': 1.028918,
    'left_w2': -0.501612,
}
```

### 2. 升级Home方法支持双臂 ✅

**文件**: `bridge/primitives.py`

**新功能**:
- 支持 `arm='left'` - 左臂回Home
- 支持 `arm='right'` - 右臂回Home
- 支持 `arm='both'` - 双臂同时回Home ⭐ 新增

**实现**:
```python
def home(self, arm: str, speed: float = 0.3) -> Dict:
    """Return arm(s) to predefined home position.
    
    Args:
        arm: 'left', 'right', or 'both'
        speed: Motion speed ratio (0-1)
    """
    if arm == 'both':
        # 依次移动左右臂
        results = []
        for single_arm in ['left', 'right']:
            result = self.home(single_arm, speed)
            results.append(result)
        # 检查是否都成功
        ...
```

### 3. 更新API模型 ✅

**文件**: `bridge/models.py`

```python
class HomeRequest(BaseModel):
    """Request to return arm to home position."""
    arm: Literal["left", "right", "both"] = Field(default="right", ...)
    #                              ^^^^^ 新增
```

---

## 使用方法

### API调用

#### 单臂回Home
```bash
# 右臂
curl -X POST http://localhost:8420/primitives/home \
  -H "Content-Type: application/json" \
  -d '{"arm": "right"}'

# 左臂
curl -X POST http://localhost:8420/primitives/home \
  -H "Content-Type: application/json" \
  -d '{"arm": "left"}'
```

#### 双臂回Home ⭐ 新功能
```bash
curl -X POST http://localhost:8420/primitives/home \
  -H "Content-Type: application/json" \
  -d '{"arm": "both"}'
```

### Python调用

```python
import httpx

client = httpx.Client(base_url="http://localhost:8420")

# 单臂
response = client.post("/primitives/home", json={"arm": "right"})

# 双臂
response = client.post("/primitives/home", json={"arm": "both"})
```

### Web界面

```
输入: "回到Home位置"
或: "双臂回Home"
```

---

## 重启Bridge Server

**重要**: 修改后需要重启Bridge Server才能生效！

```bash
# 停止当前服务
pkill -f bridge.server

# 重新启动
./start_bridge.sh
```

---

## 测试新的Home位姿

### 测试1: 单臂Home
```bash
# 右臂
curl -X POST http://localhost:8420/primitives/home \
  -H "Content-Type: application/json" \
  -d '{"arm": "right"}'

# 观察机器人是否移动到新的Home位置
```

### 测试2: 双臂Home
```bash
curl -X POST http://localhost:8420/primitives/home \
  -H "Content-Type: application/json" \
  -d '{"arm": "both"}'

# 观察双臂是否都移动到Home位置
```

### 测试3: 验证位姿
```bash
# 移动到Home后，检查关节角度
curl http://localhost:8420/status?arm=right | python -m json.tool

# 关节角度应该与home_positions中定义的值一致
```

---

## 未来更新Home位姿

如果需要再次更新Home位姿，使用提供的脚本：

```bash
# 1. 手动移动机器人到理想位置

# 2. 运行脚本保存当前位姿
python save_current_as_home.py

# 3. 脚本会生成 new_home_positions.txt

# 4. 手动编辑 bridge/primitives.py，替换 home_positions

# 5. 重启Bridge Server
pkill -f bridge.server && ./start_bridge.sh
```

---

## 其他需要双臂支持的动作

以下动作也应该支持'both'选项（待实现）:

### 夹爪控制
```python
# 当前: 只支持单臂
gripper(arm='right', action='open')

# 建议: 支持双臂
gripper(arm='both', action='open')  # 同时打开双臂夹爪
```

### 使能/禁用
```python
# 当前: 全局使能
enable()  # 使能整个机器人

# 可能不需要单独的arm参数
```

---

## 总结

✅ **已完成**:
1. 更新Home位姿为当前舒适位置
2. Home方法支持'both'双臂
3. API模型支持'both'选项
4. 创建保存脚本方便未来更新

⚠️ **需要重启**:
- 修改后必须重启Bridge Server

🔧 **建议扩展**:
- 夹爪控制支持'both'
- 其他动作原语的双臂支持

---

现在系统已经完全支持双臂Home功能！
