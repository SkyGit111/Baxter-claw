# Baxter-Claw 自然语言支持说明

## 当前支持的命令模式

### 1. 抓取物体 (pick_by_name)

**中文模式:**
- "拿一下红色的杯子" → 识别 "红色的杯子"
- "抓住蓝色盒子" → 识别 "蓝色盒子"
- "取那个瓶子" → 识别 "瓶子"
- "夹住白色的盒子" → 识别 "白色的盒子"

**英文模式 (当前限制):**
- "pick cup" → 只识别 "cup" (单词)
- "grab box" → 只识别 "box" (单词)

**问题:** 英文正则 `r'pick.*?(\w+)'` 只能捕获单个单词，无法识别 "red cup" 或 "white box" 这样的短语。

**改进建议:**
```python
# 改进的英文模式
r'pick\s+(?:the\s+)?(.+?)(?:\s+please)?$'
r'grab\s+(?:the\s+)?(.+?)(?:\s+please)?$'
```

### 2. 放置物体 (place)

**中文模式:**
- "放到左边" → 识别方向 "左"
- "放在右边" → 识别方向 "右"
- "放到前面" → 识别方向 "前"

**英文模式:**
- "place" → 无参数，使用默认位置
- "put" → 无参数，使用默认位置

**问题:** 英文模式不支持方向识别。

**改进建议:**
```python
r'place\s+(?:it\s+)?(?:on\s+)?(?:the\s+)?(left|right|front|back|up|down|center)'
r'put\s+(?:it\s+)?(?:on\s+)?(?:the\s+)?(left|right|front|back|up|down|center)'
```

### 3. 夹爪控制 (gripper)

**打开夹爪:**
- "打开夹爪" ✓
- "松开" ✓
- "open gripper" ✓

**关闭夹爪:**
- "关闭夹爪" ✓
- "夹紧" ✓
- "close gripper" ✓

### 4. 场景识别 (describe_scene)

**中文模式:**
- "看看桌上有什么" ✓
- "有什么东西" ✓
- "识别一下" ✓

**英文模式:**
- "describe" ✓
- "what do you see" ✓

### 5. 回原位 (home)

**中文模式:**
- "回到原位" ✓
- "回原点" ✓

**英文模式:**
- "home" ✓
- "reset" ✓

### 6. 查看状态 (status)

**中文模式:**
- "状态" ✓
- "查看状态" ✓

**英文模式:**
- "status" ✓

## 为什么英文支持有限？

当前的正则表达式设计主要针对中文，英文模式存在以下问题：

1. **单词捕获限制**: `\w+` 只匹配单个单词，不能匹配 "red cup" 这样的短语
2. **缺少方向映射**: 英文方向词 (left/right/front/back) 没有映射到坐标
3. **贪婪匹配问题**: 中文用 `[^\s，。]+` 可以匹配多字符，但英文需要不同策略

## 如何改进英文支持

### 方案 1: 改进正则表达式

```python
'pick_by_name': [
    # 中文模式
    r'拿.*?([^\s，。]+)',
    r'抓.*?([^\s，。]+)',
    r'取.*?([^\s，。]+)',
    r'夹.*?([^\s，。]+)',
    # 改进的英文模式
    r'pick\s+(?:up\s+)?(?:the\s+)?(.+?)(?:\s+please)?$',
    r'grab\s+(?:the\s+)?(.+?)(?:\s+please)?$',
    r'get\s+(?:me\s+)?(?:the\s+)?(.+?)(?:\s+please)?$',
],
'place': [
    # 中文模式
    r'放到.*?([左右前后上下中])',
    r'放在.*?([左右前后上下中])',
    # 改进的英文模式
    r'place\s+(?:it\s+)?(?:on\s+)?(?:the\s+)?(left|right|front|back|up|down|center)',
    r'put\s+(?:it\s+)?(?:on\s+)?(?:the\s+)?(left|right|front|back|up|down|center)',
],
```

### 方案 2: 添加英文方向映射

```python
def _direction_to_position(self, direction: str) -> list:
    """Convert direction to approximate position."""
    base = [0.7, 0.0, 0.0]
    
    offsets = {
        # 中文
        '左': [0.0, 0.3, 0.0],
        '右': [0.0, -0.3, 0.0],
        '前': [0.1, 0.0, 0.0],
        '后': [-0.1, 0.0, 0.0],
        '上': [0.0, 0.0, 0.1],
        '下': [0.0, 0.0, -0.1],
        '中': [0.0, 0.0, 0.0],
        # 英文
        'left': [0.0, 0.3, 0.0],
        'right': [0.0, -0.3, 0.0],
        'front': [0.1, 0.0, 0.0],
        'back': [-0.1, 0.0, 0.0],
        'up': [0.0, 0.0, 0.1],
        'down': [0.0, 0.0, -0.1],
        'center': [0.0, 0.0, 0.0],
    }
    
    offset = offsets.get(direction, [0.0, 0.0, 0.0])
    return [base[i] + offset[i] for i in range(3)]
```

## 测试示例

### 当前可用的命令

**中文 (完全支持):**
```
✓ "帮我拿一下红色的杯子"
✓ "抓住细长的白色盒子"
✓ "把它放到左边"
✓ "打开夹爪"
✓ "看看桌上有什么"
✓ "回到原位"
```

**英文 (部分支持):**
```
✓ "pick cup" (单词)
✓ "grab box" (单词)
✗ "pick the red cup" (短语 - 需要改进)
✗ "grab white box" (短语 - 需要改进)
✓ "open gripper"
✓ "describe"
✓ "home"
✗ "place it on the left" (方向 - 需要改进)
```

## 下一步改进建议

1. **立即可做**: 添加改进的英文正则表达式
2. **短期优化**: 添加英文方向词映射
3. **长期扩展**: 使用 NLP 库 (如 spaCy) 进行更智能的意图识别