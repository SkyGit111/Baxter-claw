# Baxter-Claw Skills Definition

## Skill 1: pick_object
**Description**: Pick up an object by name using vision

**When to use**:
- User asks to pick, grab, grasp, or take an object
- Examples: "抓住蓝色小方块", "拿起红色杯子", "grab the yellow cube"

**Parameters**:
- `object_name` (string, required): Name of the object to pick
- `arm` (string, optional): Which arm to use ("left", "right", or "auto")

**Execution**:
1. Call `pick_by_name(object_name, arm)`
2. If successful, skill is DONE

**Success condition**: Object is grasped and lifted

---

## Skill 2: place_object_direction
**Description**: Place the held object in a direction (left, right, front, back, center)

**When to use**:
- User asks to place object with direction only
- Examples: "放到左边", "put it on the right", "放到前面"

**Parameters**:
- `direction` (string, required): Direction to place ("left", "right", "front", "back", "center")
- `arm` (string, optional): Which arm is holding the object ("left", "right", or "auto")

**Execution**:
1. Call `place(direction, arm)`
2. If successful, skill is DONE

**Success condition**: Object is released and arm retracted

---

## Skill 3: place_object_relative
**Description**: Place the held object relative to another object

**When to use**:
- User asks to place object relative to a target object
- Examples: "放到黄色方块上", "把它放到红色杯子旁边", "place it on top of the box"

**Parameters**:
- `target_object_name` (string, required): Name of the reference object
- `relative_position` (string, required): Where to place relative to target
  - "on_top": On top of the target object
  - "next_to": Next to the target object (15cm to the side)
  - "behind": Behind the target object (15cm back)
  - "in_front": In front of the target object (15cm forward)
- `arm` (string, optional): Which arm is holding the object ("left", "right", or "auto")

**Execution**:
1. Call `place_by_name(target_object_name, relative_position, arm)`
2. If successful, skill is DONE

**Success condition**: Object is released at correct position and arm retracted

---

## Skill 4: pick_and_place_direction
**Description**: Pick an object and place it in a direction (combined skill)

**When to use**:
- User asks to move an object to a direction
- Examples: "把蓝色方块放到左边", "move the red cup to the right"

**Parameters**:
- `object_name` (string, required): Name of the object to pick
- `direction` (string, required): Direction to place
- `arm` (string, optional): Which arm to use ("auto" recommended)

**Execution**:
1. Call `pick_by_name(object_name, arm)`
2. If pick fails, skill FAILS
3. Call `place(direction, arm)` (use same arm that picked)
4. If successful, skill is DONE

**Success condition**: Object is picked and placed at target direction

---

## Skill 5: pick_and_place_relative
**Description**: Pick an object and place it relative to another object (combined skill)

**When to use**:
- User asks to move an object relative to another object
- Examples: "把蓝色方块放到黄色方块上", "place the red cup next to the white box"

**Parameters**:
- `source_object_name` (string, required): Name of the object to pick
- `target_object_name` (string, required): Name of the reference object
- `relative_position` (string, required): Where to place ("on_top", "next_to", "behind", "in_front")
- `arm` (string, optional): Which arm to use ("auto" recommended)

**Execution**:
1. Call `pick_by_name(source_object_name, arm)`
2. If pick fails, skill FAILS
3. Call `place_by_name(target_object_name, relative_position, arm)` (use same arm)
4. If successful, skill is DONE

**Success condition**: Source object is picked and placed relative to target object

---

## Skill 6: locate_object
**Description**: Find the 3D coordinates of an object using vision

**When to use**:
- User asks to locate, find, or identify object position
- Examples: "识别魔方的坐标", "where is the red cup", "find the yellow block"

**Parameters**:
- `object_name` (string, required): Name of the object to locate

**Execution**:
1. Call `locate_object(object_name)`
2. Return position to user
3. Skill is DONE

**Success condition**: Object position is found and returned

---

## Skill 7: describe_scene
**Description**: Describe what objects are visible in the scene

**When to use**:
- User asks what's on the table or in view
- Examples: "看看桌上有什么", "what do you see", "describe the scene"

**Parameters**: None

**Execution**:
1. Call `describe_scene()`
2. Return description to user
3. Skill is DONE

**Success condition**: Scene description is returned

---

## Skill 8: go_home
**Description**: Move arm(s) to home position

**When to use**:
- User asks to reset, go home, or return to initial position
- Examples: "回到原位", "reset arms", "go home"

**Parameters**:
- `arm` (string, optional): Which arm ("left", "right", or "both")

**Execution**:
1. Call `home(arm)`
2. Skill is DONE

**Success condition**: Arm(s) moved to home position

---

## Skill 9: open_gripper
**Description**: Open gripper to release object

**When to use**:
- User asks to open gripper or release object
- Examples: "打开夹爪", "open gripper", "release"

**Parameters**:
- `arm` (string, required): Which arm ("left" or "right")

**Execution**:
1. Call `gripper_open(arm)`
2. Skill is DONE

**Success condition**: Gripper is opened

---

## Skill 10: close_gripper
**Description**: Close gripper

**When to use**:
- User asks to close gripper
- Examples: "关闭夹爪", "close gripper"

**Parameters**:
- `arm` (string, required): Which arm ("left" or "right")

**Execution**:
1. Call `gripper_close(arm)`
2. Skill is DONE

**Success condition**: Gripper is closed

---

## Skill 11: parallel_pick_and_place
**Description**: Execute two pick-and-place tasks simultaneously with both arms

**When to use**:
- User asks to do two tasks at the same time with both arms
- User explicitly mentions "同时", "simultaneously", "at the same time", "并行"
- Examples: 
  - "用右手抓取蓝色小方块放到红色方块上，同时用左手抓取黄色方块放到魔方上"
  - "simultaneously pick blue cube with right arm and yellow cube with left arm"

**Parameters**:
- `left_task` (object, required): Task for left arm
  - `source_object` (string): Object to pick with left arm
  - `target_object` (string): Where to place (object name)
  - `relative_position` (string): "on_top", "next_to", "behind", "in_front"
- `right_task` (object, required): Task for right arm
  - `source_object` (string): Object to pick with right arm
  - `target_object` (string): Where to place (object name)
  - `relative_position` (string): "on_top", "next_to", "behind", "in_front"

**Execution**:
1. Start left arm task in parallel: pick left_task.source_object → place relative to left_task.target_object
2. Start right arm task in parallel: pick right_task.source_object → place relative to right_task.target_object
3. Wait for both tasks to complete
4. If both successful, skill is DONE
5. If either fails, skill FAILS with details

**Success condition**: Both arms complete their pick-and-place tasks successfully

**Example**:
```json
{
  "skill": "parallel_pick_and_place",
  "left_task": {
    "source_object": "黄色小方块",
    "target_object": "魔方",
    "relative_position": "on_top"
  },
  "right_task": {
    "source_object": "蓝色小方块",
    "target_object": "红色小方块",
    "relative_position": "on_top"
  }
}
```

---

## Skill 12: sequential_relay_pick_place
**Description**: Sequential relay: left arm picks object from left side and places at center, then right arm picks from center and places at right side

**When to use**:
- User asks to move an object from left to right using both arms
- User mentions relay, handover, or sequential transfer from left to right
- Object is on the left side and needs to be moved to the right side
- Examples:
  - "把蓝色小方块从左边移到右边"
  - "用左右臂接力把物体从左侧传到右侧"
  - "relay the blue cube from left to right"
  - "transfer the object from left side to right side using both arms"

**Parameters**:
- `object_name` (string, required): Name of the object to relay (e.g., "蓝色小方块", "blue cube")
- `final_target_name` (string, optional): Reference object for final placement (if None, uses offset)
- `final_relative_position` (string, optional): Where to place relative to final target ("next_to", "on_top", "behind", "in_front"), default: "next_to"
- `relay_offset_y` (float, optional): Y offset for relay position, default: 0.0 (center)
- `final_offset_x` (float, optional): X offset for final position from relay, default: 0.20 (20cm to the right)

**Execution**:
1. Left arm picks object from left side
2. Left arm places object at center (Y=0, relay position)
3. Left arm returns to home position
4. Right arm picks object from center
5. Right arm places object at right side (final position)
6. Right arm returns to home position

**Success condition**: Object successfully relayed from left side to right side via center handover

**Example**:
```json
{
  "skill": "sequential_relay_pick_place",
  "object_name": "蓝色小方块",
  "final_offset_x": 0.25
}
```

**Important Notes**:
- Left arm picks from wherever the object is located (typically left side)
- Relay position is at center (Y=0) with same X and Z as pick position
- Final position is offset from relay position (default 20cm to the right)
- If `final_target_name` is provided, places relative to that target instead of using offset
- Both arms return to home after their respective tasks

---

## Skill 13: sequential_handover
**Description**: Left arm picks object A and places it at center, then right arm picks object A and places it on object B (sequential dual-arm handover)

**When to use**:
- User asks for a handover or relay task between arms with a specific target object
- User mentions "依次", "先...再...", "传递", "接力", "sequentially", "then"
- Examples:
  - "先用左手抓取蓝色小方块放到中间，再用右手抓取它放到红色小方块上"
  - "left arm picks blue cube to center, then right arm picks it and places on red cube"

**Parameters**:
- `object_a` (string, required): Object to be picked by left arm first (e.g., "蓝色小方块")
- `object_b` (string, required): Final target object for placement (e.g., "红色小方块")
- `relative_position` (string, optional): Where to place on object B ("on_top", "next_to", "behind", "in_front"), default: "on_top"

**Execution**:
1. Left arm picks object_a
2. Left arm places object_a at center position (Y=0)
3. Left arm returns to home position
4. Right arm picks object_a from center
5. Right arm places object_a relative to object_b
6. If all steps successful, skill is DONE

**Success condition**: Object A successfully transferred from left side to object B via center handover

**Example**:
```json
{
  "skill": "sequential_handover",
  "object_a": "蓝色小方块",
  "object_b": "红色小方块",
  "relative_position": "on_top"
}
```

---

## Skill 14: bimanual_hold_and_rotate
**Description**: Hold one ruler segment fixed with one arm while rotating an adjacent segment around their shared hinge joint with the other arm

**When to use**:
- User asks to hold/fix one segment and rotate/turn another segment
- User mentions rotating around a joint/hinge
- User specifies rotation angle (30°, 60°, 90°) and direction (clockwise/counterclockwise)
- Examples:
  - "用左手固定蓝色尺段，用右手把黄色尺段顺时针旋转90度"
  - "固定蓝色部分，把黄色部分逆时针旋转60度"
  - "hold blue segment with left arm, rotate yellow segment 90 degrees clockwise with right arm"

**Parameters**:
- `fixed_arm` (string, optional): Arm to hold fixed segment ("left" or "right"), default: "left"
- `moving_arm` (string, optional): Arm to rotate moving segment ("left" or "right"), default: "right"
- `fixed_segment_color` (string, required): Color of segment to hold fixed (e.g., "blue", "yellow", "green")
- `moving_segment_color` (string, required): Color of segment to rotate (e.g., "blue", "yellow", "green")
- `angle_degrees` (number, required): Rotation angle in degrees (e.g., 30, 60, 90)
- `direction` (string, required): Rotation direction ("clockwise" or "counterclockwise")
- `segment_length` (number, optional): Length of each segment in meters, default: 0.15

**Execution**:
1. Locate all points using VLM before any motion:
   - Fixed segment grasp point
   - Moving segment grasp point
   - Fixed segment midpoint
   - Moving segment midpoint
   - Hinge joint between the two specified segments
2. Compute hinge center from geometry and VLM observation
3. Plan circular arc trajectory for rotation
4. Validate all waypoints are safe and reachable
5. Fixed arm grasps and holds fixed segment
6. Moving arm grasps moving segment
7. Moving arm follows arc trajectory to rotate segment
8. Release both arms

**Success condition**: Moving segment successfully rotated by specified angle around hinge

**Example**:
```json
{
  "skill": "bimanual_hold_and_rotate",
  "fixed_arm": "left",
  "moving_arm": "right",
  "fixed_segment_color": "blue",
  "moving_segment_color": "yellow",
  "angle_degrees": 90,
  "direction": "clockwise",
  "segment_length": 0.15
}
```

**Important Notes**:
- The two segments must be adjacent (share a hinge joint)
- For 3-segment rulers with 2 joints, specify which two adjacent segments to use via their colors
- System will locate the hinge between the specified colored segments
- Rotation happens in XY plane (table surface)
- All localization happens before robot motion begins

---

## Skill 15: bimanual_shape_ruler
**Description**: Adjust articulated ruler configuration from S-shape to L-shape using bimanual push mode

**When to use**:
- User asks to adjust ruler shape or configuration
- User mentions changing from S-shape to L-shape
- User asks to straighten or adjust the articulated ruler
- Examples:
  - "把尺子从S型调整成L型"
  - "调整尺子构型"
  - "adjust ruler to L-shape"
  - "straighten the ruler segments"

**Parameters**:
- `fixed_arm` (string, optional): Arm to hold fixed segment ("left" or "right"), default: "left"
- `moving_arm` (string, optional): Arm to push moving segment ("left" or "right"), default: "right"
- `target_shape` (string, optional): Target shape configuration ("L"), default: "L"
- `l_shape_blue_turn_direction` (string, optional): Blue segment turn direction ("clockwise" or "counterclockwise"), default: "clockwise"
- `config_path` (string, optional): Path to ruler task configuration, default: "config/ruler_task.yaml"
- `dry_run` (boolean, optional): If true, only compute plan without executing, default: false

**Execution**:
1. Load configuration from ruler_task.yaml
2. Locate all points using VLM (red grasp, green joint, orange joint, blue push)
3. Convert to motion coordinates (fixed Z = -0.16m)
4. Calculate L-shape target configuration using two-link kinematics
5. Plan waypoints using angle interpolation with joint limit validation
6. Validate all poses (safety + IK)
7. Fixed arm grasps and holds red segment
8. Moving arm pushes (NOT grasps) blue segment along waypoints
9. Release both arms

**Success condition**: Ruler successfully adjusted to L-shape configuration

**Example**:
```json
{
  "skill": "bimanual_shape_ruler",
  "fixed_arm": "left",
  "moving_arm": "right",
  "target_shape": "L",
  "l_shape_blue_turn_direction": "clockwise",
  "dry_run": false
}
```

**Important Notes**:
- **Push mode**: Moving arm does NOT close gripper, only pushes
- Fixed motion Z coordinate (-0.16m) for all movements
- Two-link angle interpolation (not simple circular arc)
- Physical joint angle limits are validated
- All localization happens before robot motion
- Configuration file defines segment colors and joint positions
- Green joint (red-yellow) is approximately fixed when red segment is held
- Orange joint (yellow-blue) moves during adjustment

---

## Skill 16: flatten_articulated_ruler
**Description**: Flatten an S-shaped articulated ruler by pulling both endpoints apart with dual-arm coordination

**When to use**:
- User asks to flatten, straighten, or pull apart the ruler
- User mentions pulling the ruler straight
- User asks to unfold or extend the ruler
- Examples:
  - "把尺子拉直"
  - "将折叠的尺子向两边拉开"
  - "flatten the ruler"
  - "pull the ruler straight"
  - "straighten the folded ruler"

**Parameters**:
- `config_path` (string, optional): Path to flatten ruler task configuration, default: "config/flatten_ruler_task.yaml"
- `dry_run` (boolean, optional): If true, only compute plan without executing, default: false

**Execution**:
1. Load configuration from flatten_ruler_task.yaml
2. Locate red endpoint (purple tape) and blue endpoint (green tape) using VLM
3. Calculate initial and final positions with pulling distance
4. Generate synchronized trajectories with position and orientation interpolation
5. Validate all poses (workspace + IK)
6. Both arms grasp their respective endpoints
7. Execute synchronized pulling motion with yaw interpolation
8. Release both endpoints

**Success condition**: Ruler successfully flattened with both endpoints pulled apart

**Example**:
```json
{
  "skill": "flatten_articulated_ruler",
  "dry_run": false
}
```

**Important Notes**:
- **Dual-arm grasp mode**: Both arms close grippers to hold endpoints
- **Synchronized motion**: Left and right arms move together
- **Orientation interpolation**: Yaw rotates to follow pulling direction
- Fixed Z coordinate for all movements (table surface)
- Pull distance, speed, and waypoint count are configurable
- All localization happens before robot motion
- Gripper orientation remains vertical (downward) throughout
- Only locates 2 points (red and blue endpoints), no joint localization needed

---

## Notes for LLM

### Parameter Extraction Rules

1. **object_name / source_object_name**: Extract the object the user wants to manipulate
   - "抓住蓝色小方块" → object_name = "蓝色小方块"
   - "grab the red cup" → object_name = "red cup"

2. **target_object_name**: Extract the reference object for placement
   - "放到黄色方块上" → target_object_name = "黄色方块"
   - "place it next to the white box" → target_object_name = "white box"

3. **relative_position**: Map user's spatial description
   - "上面", "上", "on top", "on" → "on_top"
   - "旁边", "next to", "beside" → "next_to"
   - "后面", "behind" → "behind"
   - "前面", "in front", "front" → "in_front"

4. **direction**: Map user's direction
   - "左边", "左", "left" → "left"
   - "右边", "右", "right" → "right"
   - "前面", "前", "front" → "front"
   - "后面", "后", "back" → "back"
   - "中间", "center" → "center"

5. **arm**: Default to "auto" unless user specifies
   - "用左手", "left arm" → "left"
   - "用右手", "right arm" → "right"
   - Otherwise → "auto"

### Skill Selection Rules

1. **Single action tasks**: Use simple skills (pick_object, place_object_*)
   - "抓住蓝色小方块" → pick_object
   - "放到左边" → place_object_direction

2. **Combined tasks**: Use combined skills (pick_and_place_*)
   - "把蓝色方块放到左边" → pick_and_place_direction
   - "把蓝色方块放到黄色方块上" → pick_and_place_relative

3. **Query tasks**: Use query skills (locate_object, describe_scene)
   - "魔方在哪里" → locate_object
   - "看看桌上有什么" → describe_scene

### CRITICAL: Parameter Accuracy

- **ALWAYS extract BOTH object names** for pick_and_place_relative
- **NEVER confuse source and target objects**
- Example: "把蓝色方块放到黄色方块上"
  - source_object_name = "蓝色方块" (the one to pick)
  - target_object_name = "黄色方块" (the reference for placement)
