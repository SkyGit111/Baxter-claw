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
