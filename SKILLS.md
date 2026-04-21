# Baxter-Claw Skills Definition

## Skill Architecture

Skills are atomic operations that can be composed into workflows. Each skill has:
- **Input parameters**: What data it needs
- **Output data**: What data it produces
- **Success criteria**: How to know if it succeeded
- **Next skill suggestions**: What skills typically follow

## Query Skills (Information Gathering)

### locate_object
**Purpose**: Find the 3D position of a named object using vision

**Input**:
```json
{
  "object_name": "string (e.g., 'red cup', '魔方')"
}
```

**Output**:
```json
{
  "success": true,
  "position": [x, y, z],
  "confidence": 85,
  "object_name": "red cup"
}
```

**Next Skills**:
- If success → `pick` (use position from output)
- If failed → `describe_scene` (to understand why)

**Usage Example**:
```
User: "识别魔方的坐标"
→ locate_object(object_name="魔方")
→ Returns: position=[0.6, 0.15, 0.1]
→ Done (query task, return result to user)
```

---

### describe_scene
**Purpose**: Get a natural language description of what the robot sees

**Input**:
```json
{
  "camera": "right_hand" (optional, default: "right_hand")
}
```

**Output**:
```json
{
  "success": true,
  "description": "I see a red cup on the left, a blue box in the center..."
}
```

**Next Skills**:
- This is typically a terminal skill (returns info to user)

---

### identify_objects
**Purpose**: List all objects detected in the scene

**Input**: None

**Output**:
```json
{
  "success": true,
  "objects": [
    {"name": "red cup", "confidence": 90},
    {"name": "blue box", "confidence": 85}
  ]
}
```

**Next Skills**:
- If user wants to pick one → `locate_object` or `pick_by_name`

---

## Manipulation Skills (Robot Actions)

### pick
**Purpose**: Pick up an object at a known 3D position

**Input**:
```json
{
  "arm": "left" | "right" | "auto",
  "position": [x, y, z],
  "approach_height": 0.1 (optional)
}
```

**Output**:
```json
{
  "success": true,
  "arm_used": "right",
  "final_position": [x, y, z+0.1]
}
```

**State Change**:
- `robot_state[arm_used].holding_object = true`

**Next Skills**:
- `place` (to put object down)
- `handover` (to transfer to other arm)

**Usage Example**:
```
Step 1: locate_object(object_name="魔方")
  → Returns: position=[0.6, 0.15, 0.1]
Step 2: pick(arm="auto", position=[0.6, 0.15, 0.1])
  → System chooses arm based on position
  → Executes pick sequence
```

---

### pick_by_name
**Purpose**: Pick up an object by name (combines locate + pick)

**Input**:
```json
{
  "object_name": "string",
  "arm": "left" | "right" | "auto"
}
```

**Output**:
```json
{
  "success": true,
  "arm_used": "right",
  "position": [x, y, z],
  "vlm_response": {...}
}
```

**State Change**:
- `robot_state[arm_used].holding_object = true`
- `robot_state[arm_used].object_name = object_name`

**Next Skills**:
- `place` (to put object down)

**Internal Flow**:
1. Locate object using VLM
2. Choose arm based on position (if auto)
3. Execute pick at located position

**Usage Example**:
```
User: "拿红色杯子"
→ pick_by_name(object_name="红色杯子", arm="auto")
→ Internally: locate → choose arm → pick
→ Done
```

---

### place
**Purpose**: Place held object at a target location

**Input**:
```json
{
  "arm": "left" | "right" | "auto",
  "position": [x, y, z] | null,
  "direction": "left" | "right" | "front" | "back" | "center" (if position is null)
}
```

**Output**:
```json
{
  "success": true,
  "arm_used": "right",
  "final_position": [x, y, z]
}
```

**State Change**:
- `robot_state[arm_used].holding_object = false`
- `robot_state[arm_used].object_name = null`

**Next Skills**:
- `home` (return to home position)
- `pick_by_name` (pick another object)

---

### move_to
**Purpose**: Move arm to a specific position without grasping

**Input**:
```json
{
  "arm": "left" | "right",
  "position": [x, y, z],
  "orientation": [roll, pitch, yaw] (optional)
}
```

**Output**:
```json
{
  "success": true,
  "arm_used": "right",
  "final_position": [x, y, z]
}
```

**Next Skills**:
- `gripper_open` / `gripper_close`
- `home`

---

### gripper_open / gripper_close
**Purpose**: Control gripper state

**Input**:
```json
{
  "arm": "left" | "right" | "both"
}
```

**Output**:
```json
{
  "success": true,
  "message": "左臂夹爪已打开"
}
```

**Next Skills**:
- After open → `pick` or `move_to`
- After close → `place` or `move_to`

---

### home
**Purpose**: Return arm(s) to safe home position

**Input**:
```json
{
  "arm": "left" | "right" | "both"
}
```

**Output**:
```json
{
  "success": true,
  "message": "右臂已回到原位"
}
```

**Next Skills**:
- Typically terminal (task complete)

---

## Dual-Arm Skills

### bimanual_pick
**Purpose**: Pick large object with both arms simultaneously

**Input**:
```json
{
  "object_name": "string",
  "left_offset": [-0.05, 0, 0] (optional),
  "right_offset": [0.05, 0, 0] (optional)
}
```

**Output**:
```json
{
  "success": true,
  "left_position": [x1, y1, z1],
  "right_position": [x2, y2, z2]
}
```

**State Change**:
- Both arms marked as holding object

**Next Skills**:
- Coordinated placement (not yet implemented)

---

### handover
**Purpose**: Transfer object from one arm to another

**Input**:
```json
{
  "from_arm": "left" | "right",
  "to_arm": "left" | "right",
  "handover_position": [x, y, z] (optional)
}
```

**Output**:
```json
{
  "success": true,
  "handover_position": [x, y, z]
}
```

**State Change**:
- `from_arm`: holding_object = false
- `to_arm`: holding_object = true

**Next Skills**:
- `place` with to_arm

---

## Skill Composition Patterns

### Pattern 1: Locate and Pick
```
User: "识别魔方的坐标并抓取"

Workflow:
1. locate_object(object_name="魔方")
   → Output: position=[0.6, 0.15, 0.1]
2. pick(arm="auto", position=[0.6, 0.15, 0.1])
   → System chooses arm based on y-coordinate
   → Output: success=true, arm_used="left"
3. Done
```

### Pattern 2: Pick and Place
```
User: "拿红杯子放到左边"

Workflow:
1. pick_by_name(object_name="红杯子", arm="auto")
   → Output: success=true, arm_used="right"
2. place(arm="right", direction="左")
   → Output: success=true
3. Done
```

### Pattern 3: Query Only
```
User: "识别魔方的坐标"

Workflow:
1. locate_object(object_name="魔方")
   → Output: position=[0.6, 0.15, 0.1], confidence=85
2. Return result to user immediately (no further actions)
```

---

## Skill Selection Rules for LLM

### For Query Tasks:
1. Execute the query skill once
2. Return result immediately to user
3. Do NOT enter workflow loop

### For Manipulation Tasks:
1. Start with initial skill from intent
2. After each skill execution, check:
   - Did it succeed?
   - Is the user's goal complete?
   - What data is available for next skill?
3. Use output data from previous skill as input to next skill
4. Set action="done" when goal is achieved

### Data Flow Between Skills:
```python
# Example: locate → pick
step1_result = locate_object(object_name="魔方")
if step1_result['success']:
    position = step1_result['position']  # Extract position
    step2_result = pick(arm="auto", position=position)  # Use in next skill
```

### Completion Criteria:
- **Query tasks**: After first skill returns result
- **Pick task**: After object is grasped and lifted
- **Place task**: After object is released and arm retracted
- **Home task**: After arm reaches home position
- **Handover task**: After object transferred successfully

---

## Error Handling

### If skill fails:
1. Check failure count for this skill
2. If failed < 2 times: Retry with adjusted parameters
3. If failed >= 2 times: Try alternative approach or report error

### Alternative Approaches:
- `pick_by_name` fails → Try `locate_object` + `pick` separately
- `locate_object` fails → Try `describe_scene` to understand why
- Arm collision detected → Use other arm

---

## Implementation Notes

### Current Implementation:
- Skills are implemented as actions in `execute_action()`
- Each skill calls Bridge Server API
- Results include success flag and output data

### Needed Improvements:
1. ✅ Add `locate_object` skill
2. ✅ Add `identify_objects` skill
3. ✅ Distinguish query vs manipulation tasks
4. ⚠️ Improve data passing between skills in workflow
5. ⚠️ Add explicit skill composition logic
6. ⚠️ Better completion detection

### Data Passing Issue:
**Problem**: LLM doesn't see detailed output from previous skill

**Current**: 
```python
history_text = "1. locate_object: ✓ 成功\n   信息: 找到魔方..."
```

**Needed**:
```python
history_text = "1. locate_object: ✓ 成功\n   输出数据: position=[0.6, 0.15, 0.1]\n   可用于下一步: pick(position=...)"
```

**Solution**: Include structured output data in workflow prompt
