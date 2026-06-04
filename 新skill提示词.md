你现在需要在现有 Baxter-Claw 项目中开发一个新的上层 skill，用于完成“一只机械臂固定折叠尺的一段，另一只机械臂带动另一段绕旋转关节做平面旋转”的双臂协同任务。

请先完整阅读当前项目代码结构，不要凭空假设函数名。重点检查：
- openclaw_plugin/skills.md
- openclaw_plugin/baxter_claw_plugin.py
- bridge/server.py
- bridge/models.py
- bridge/primitives.py
- bridge/multi_view_vlm.py
- bridge/vlm_client.py
- bridge/drivers/baxter_driver.py
- bridge/safety.py
- bridge/ik_solver.py

以及当前已有的 pick/place、parallel_pick_and_place、locate_object 等实现方式。

本次开发目标不是简单的 pick/place 组合，而是新增一个真正的“双臂协同固定-旋转”技能。请严格按照现有项目架构扩展，不要破坏已有 skill 和 API。

====================
一、任务背景
====================

实验对象是一个由折叠尺、纸板和彩色胶带制作的铰接物体：

- 可以是 2 段硬质尺段 + 1 个旋转关节；
- 也可以是 3 段硬质尺段 + 2 个旋转关节；
- 每段尺子的长度已知为 15 cm，即机器人坐标系中长度为 0.15 m；
- 每段尺子的中点到相邻关节的距离为 7.5 cm，即 0.075 m；
- 每段尺子通过不同颜色胶带进行区分，例如蓝色尺段、黄色尺段、绿色尺段；
- 具体要固定哪一段、旋转哪一段、使用哪个连接关节，应根据用户自然语言中的颜色描述来确定；
- 整个任务发生在桌面平面上，可以视为 XY 平面运动；
- Z 坐标在抓取和旋转过程中保持不变，不需要做三维旋转规划。

自然语言示例：

- “用左手固定蓝色尺段，用右手把黄色尺段顺时针旋转90度。”
- “固定蓝色部分，把黄色部分逆时针旋转60度。”
- “用左手固定绿色尺段，用右手把黄色尺段顺时针旋转30度。”
- “固定蓝色尺段，把与它相连的黄色尺段旋转到红色目标线附近。”

这里的关键是：
- skill 中实际参与任务的是两个相邻尺段；
- 这两个尺段之间的连接点就是本次旋转的关节；
- 对于 3 段 2 关节物体，必须通过颜色确定具体操作哪两个相邻尺段和它们之间的那个关节；
- 不要默认一定使用中间段或第三段进行几何消歧。

====================
二、新 skill 的总体行为
====================

请新增一个上层 skill，建议命名为：

bimanual_hold_and_rotate

也可以根据现有命名风格命名为：

hold_and_rotate_ruler
bimanual_rotate_articulated_object

但命名要保持清晰，并在 skills.md、插件层、Bridge Server 和 primitives 中一致。

该 skill 的行为应为：

1. 在机器人执行动作之前，先完成所有视觉定位。
2. 根据用户指令解析出：
   - fixed_arm：负责固定的手臂；
   - moving_arm：负责带动旋转的手臂；
   - fixed_segment_color：被固定尺段的颜色；
   - moving_segment_color：被旋转尺段的颜色；
   - direction：clockwise 或 counterclockwise；
   - angle_degrees：旋转角度，例如 30、60、90。
3. 使用 VLM + D455 预先定位以下点：
   - fixed_grasp_position：固定臂抓取点；
   - moving_grasp_position：旋转臂抓取点；
   - fixed_segment_midpoint：固定尺段中点；
   - moving_segment_midpoint：旋转尺段中点；
   - hinge_observed_position：这两个指定颜色尺段之间连接点/旋转关节的视觉定位坐标。
4. 根据两个尺段中点和已知尺段长度 0.15 m，计算两个可能的旋转关节候选点。
5. 使用 VLM 直接定位得到的 hinge_observed_position，在两个候选点中选择距离更近的一个，作为最终 hinge_position。
6. 根据 hinge_position、moving_grasp_position 和用户指令中的旋转角度，计算 moving_grasp_position 的目标位置 target_position。
7. 在 XY 平面上规划 moving_grasp_position 从当前位置到目标位置的圆弧路径。
8. 路径规划完成后，再开始机器人动作执行。
9. 执行过程中禁止出现类似“pick 完成后回 home、重新拍照、再 place”的旧流程。
10. 执行过程必须连贯：
    - 固定臂抓取并保持不动；
    - 旋转臂抓取另一段；
    - 旋转臂沿规划圆弧路径移动，带动尺子绕 hinge_position 旋转；
    - 最后释放旋转臂，再释放固定臂。
11. 任务执行完成后返回执行结果、计算出的旋转中心、VLM 观测关节点、目标点、waypoints、实际执行状态等信息。

====================
三、重要限制：不能复用旧 pick/place 的整体流程
====================

已有 pick/place 逻辑通常是：

- 定位一个物体；
- pick；
- 回 home 或移动到安全位姿；
- 重新拍照；
- 定位 place 位置；
- place。

这个新任务不能这样做。

原因是：旋转任务需要在抓住尺子后保持连续的物理约束。如果固定臂或旋转臂中途 home、重新拍照、重新规划，就会破坏任务。

因此：

- 可以复用底层 move_to_pose、gripper_command、IK、安全检查、VLM 定位等函数；
- 不能直接调用会包含 home、重新定位、重新拍照、释放物体等副作用的完整 pick_and_place 逻辑；
- 如果现有 pick() 内部会执行不适合本任务的动作，请新写适合该任务的子原语，例如 grasp_at_position_without_retreat 或 controlled_grasp；
- 旋转动作必须新增低层动作原语，例如 follow_arc_trajectory 或 rotate_held_object_along_arc；
- 所有定位、旋转中心计算、目标点计算和路径规划必须在机器人开始动作之前完成。

====================
四、建议新增 API 与数据模型
====================

请在 bridge/models.py 中新增请求模型，例如：

BimanualHoldAndRotateRequest:
- fixed_arm: str = "left"
- moving_arm: str = "right"
- fixed_segment_color: str
- moving_segment_color: str
- fixed_grasp_name: Optional[str]
- moving_grasp_name: Optional[str]
- angle_degrees: float
- direction: str  # "clockwise" or "counterclockwise"
- segment_length: float = 0.15
- use_d455: bool = True
- approach_height: float = 0.10
- speed: float = 0.10
- waypoint_angle_step_degrees: float = 10.0
- keep_z_constant: bool = True
- dry_run: bool = False

字段说明：

1. fixed_segment_color
   表示要固定的尺段颜色，例如 "blue"。

2. moving_segment_color
   表示要旋转的尺段颜色，例如 "yellow"。

3. fixed_grasp_name 和 moving_grasp_name
   如果用户或上层插件提供了更具体的抓取点描述，则使用这些描述；
   如果没有提供，则自动生成描述，例如：
   - “蓝色尺段远离黄色尺段关节的一端的抓取块中心”
   - “黄色尺段远离蓝色尺段关节的一端的抓取块中心”

4. angle_degrees 和 direction
   从用户自然语言解析得到。

5. segment_length
   默认 0.15 m。

在 bridge/server.py 中新增接口，例如：

POST /dualarm/hold_and_rotate

接口应调用 primitives 中新增的高级方法，例如：

async def bimanual_hold_and_rotate(...)

====================
五、OpenClaw 插件层参数解析
====================

在 openclaw_plugin/skills.md 中新增该 skill 的说明。

技能触发条件：

当用户要求：
- 一只手固定某个尺段/物体；
- 另一只手旋转、转动、拨动、调整另一段；
- 指令中出现“顺时针”“逆时针”“旋转30度/60度/90度”等；
- 或者出现“固定蓝色部分，把黄色部分转到某个角度/目标线”；

应选择 bimanual_hold_and_rotate。

参数提取要求：

- fixed_arm：默认 left；
- moving_arm：默认 right；
- fixed_segment_color：从用户描述中提取，例如 blue、yellow、green；
- moving_segment_color：从用户描述中提取；
- angle_degrees：从 30/60/90 等角度中提取；
- direction：clockwise 或 counterclockwise；
- 如果用户没有说明角度，默认使用 90 度，但要在返回 message 中说明使用了默认值；
- segment_length 默认 0.15。

例如：

用户输入：
“用左手固定蓝色尺段，用右手把黄色尺段顺时针旋转90度。”

应解析为：

{
  "fixed_arm": "left",
  "moving_arm": "right",
  "fixed_segment_color": "blue",
  "moving_segment_color": "yellow",
  "direction": "clockwise",
  "angle_degrees": 90,
  "segment_length": 0.15
}

在 baxter_claw_plugin.py 中新增对应的 _execute_xxx 方法，将参数通过 HTTP POST 发送到 /dualarm/hold_and_rotate。

不要影响已有 pick_object、place_object、parallel_pick_and_place 等技能。

====================
六、VLM 定位要求
====================

该任务必须在动作开始前完成所有视觉定位。

需要定位的点包括：

1. fixed_grasp_position
   例如：
   “蓝色尺段远离黄色尺段连接关节的一端的抓取块中心”
   或：
   “蓝色固定抓取块的中心点”

2. moving_grasp_position
   例如：
   “黄色尺段远离蓝色尺段连接关节的一端的抓取块中心”
   或：
   “黄色旋转抓取块的中心点”

3. fixed_segment_midpoint
   例如：
   “蓝色尺段的几何中点”

4. moving_segment_midpoint
   例如：
   “黄色尺段的几何中点”

5. hinge_observed_position
   例如：
   “蓝色尺段和黄色尺段之间的连接点”
   “蓝色尺段与黄色尺段相连的旋转关节中心”
   “蓝色和黄色两段尺子的交接点”

注意：
- 对于 3 段尺子、2 个关节的情况，VLM 必须根据 fixed_segment_color 和 moving_segment_color 来定位这两个指定颜色尺段之间的连接点；
- 不要定位错误的另一个关节；
- 不要默认使用中间段或第三段；
- 如果指定的两个颜色尺段在图像中看起来并不相邻，应返回清晰错误，提示这两个尺段之间没有可用于旋转的连接关节；
- 如果 VLM 对 hinge_observed_position 的定位置信度低，应返回 warning，并在日志中记录。

如果现有 locate_object 只能定位物体中心，请封装一个 helper，例如：

async def locate_named_point(description: str, use_d455: bool = True) -> Dict

它可以复用现有 VLM + D455 的定位流程，但 prompt 要明确要求 VLM 返回指定“点”的位置，例如：
- 某段尺子的中点；
- 某个彩色抓取块中心；
- 两个指定颜色尺段之间的连接点。

所有定位结果应保存到一个 plan_data 或 rotation_plan 对象中。后续执行阶段只使用这个对象，不再重新拍照定位。

====================
七、旋转中心计算逻辑
====================

已知：
- 每段尺子长度 L = 0.15 m；
- 每段尺子中点到关节的距离 r = L / 2 = 0.075 m；
- 两个相邻尺段的中点分别为 A 和 B；
- 旋转关节 H 应满足：
  distance(H, A) = r
  distance(H, B) = r；
- VLM 额外提供了两个指定颜色尺段之间连接点的粗定位：
  H_vlm = hinge_observed_position。

请实现一个几何 helper，例如：

def estimate_hinge_center_from_two_midpoints_and_observed_joint(
    midpoint_a: List[float],
    midpoint_b: List[float],
    observed_hinge: List[float],
    segment_length: float,
    tolerance: float = 0.02
) -> Dict

要求：

1. 只在 XY 平面计算，忽略 Z；
2. 以 midpoint_a 和 midpoint_b 为圆心，r = segment_length / 2 为半径，求两个圆交点；
3. 这两个圆交点就是几何上可能的两个旋转关节候选点；
4. 比较两个候选点到 observed_hinge 的 XY 距离；
5. 选择距离 observed_hinge 更近的候选点作为最终 hinge_position；
6. Z 坐标可以取 observed_hinge[2]，也可以取两个中点或 moving_grasp_position 的平均 z，但后续路径规划中 Z 保持不变；
7. 返回结构中应包含：
   - selected_hinge；
   - candidate_hinges；
   - observed_hinge；
   - distance_to_observed；
   - selection_reason；
   - warnings。

请注意：
- 不要再使用 third_segment_midpoint 或中间段几何约束消歧；
- 本 skill 必须能够支持 2 段尺子 + 1 个关节的物体；
- 对于 3 段尺子 + 2 个关节的物体，也只根据 fixed_segment_color 与 moving_segment_color 确定当前要使用的那个连接关节。

视觉噪声处理要求：

如果两个圆没有严格交点，可能是因为 VLM 中点定位存在误差。此时不要直接崩溃，请实现合理 fallback。

推荐处理方式：

1. 计算两个中点距离 d = distance(A, B)；
2. 理论上两个相邻 15 cm 尺段的中点到共同关节均为 0.075 m，因此 d 应满足 d <= 2r；
3. 若 d 略大于 2r，但超出不多，例如 d <= 2r + tolerance：
   - 将其视为视觉噪声；
   - 可在两圆交点公式中进行 clamp；
   - 或者选择在线段 AB 垂直平分线上、且最接近 observed_hinge 的近似点；
4. 若 d 明显大于 2r + tolerance：
   - 返回失败，说明两个中点距离与已知尺段长度不一致，可能是 VLM 定位错误或两个颜色尺段并不相邻；
5. 若 d 非常小：
   - 返回失败，说明两个尺段中点定位异常；
6. 对最终 hinge_position 做一致性检查：
   - distance(hinge, midpoint_a) 应接近 0.075；
   - distance(hinge, midpoint_b) 应接近 0.075；
   - hinge 到 observed_hinge 的距离不应过大；
   - 如果误差较大，返回 warning 或失败，具体阈值可设置为 0.02 到 0.03 m。

请在代码中添加清晰注释，说明：
- midpoint-to-hinge 距离为 0.075 m；
- 两圆交点求解方式；
- 为什么需要 VLM 额外定位连接点；
- 如何通过 observed_hinge 在两个候选点中消歧；
- 如何处理视觉误差。

====================
八、目标点计算逻辑
====================

已知：
- 旋转中心 H = [hx, hy, hz]
- 旋转臂当前抓取点 P0 = [px, py, pz]
- 用户指令解析出的旋转角度 angle_degrees
- 旋转方向 direction

请实现 helper：

def rotate_point_around_center_xy(
    point: List[float],
    center: List[float],
    angle_degrees: float,
    direction: str
) -> List[float]

约定：
- 从桌面上方沿 +Z 或机器人上方向下看，逆时针为正角度；
- counterclockwise = +angle；
- clockwise = -angle；
- 只旋转 XY；
- Z 保持 point[2] 不变。

公式：

dx = px - hx
dy = py - hy

theta = radians(signed_angle)

target_x = hx + cos(theta) * dx - sin(theta) * dy
target_y = hy + sin(theta) * dx + cos(theta) * dy
target_z = pz

返回 target_position。

====================
九、圆弧路径规划逻辑
====================

请新增 helper：

def plan_arc_waypoints_xy(
    start_point: List[float],
    center: List[float],
    angle_degrees: float,
    direction: str,
    waypoint_angle_step_degrees: float = 10.0
) -> List[List[float]]

要求：

1. 根据旋转角度生成多个中间 waypoint；
2. 每个 waypoint 都位于以 hinge_position 为圆心，以 start_point 到 hinge_position 的 XY 距离为半径的圆弧上；
3. Z 坐标保持 start_point[2] 不变；
4. waypoint 数量不能太少：
   - 至少 5 个；
   - 推荐每 10 度一个点；
   - 例如 90 度旋转至少生成 9 到 10 个点；
5. 最后一个 waypoint 必须是 target_position；
6. 每个 waypoint 在执行前都要经过 workspace safety check 和 IK reachability check；
7. 如果某个 waypoint 不可达，应返回失败并说明是哪个 waypoint 不可达，而不是直接执行一半。

这里的“路径规划”先实现几何圆弧 waypoint 规划即可，不要引入复杂的 MoveIt/RRT，除非项目里已经有成熟接口可直接复用。当前目标是让实机实验稳定跑通。

====================
十、执行流程
====================

新增 primitives 中的高级方法，例如：

async def bimanual_hold_and_rotate(...):
    # 1. parse and validate color-based task parameters
    # 2. pre-localization
    # 3. compute hinge
    # 4. compute target
    # 5. plan arc
    # 6. safety and IK validation
    # 7. execute fixed grasp
    # 8. execute moving grasp
    # 9. follow arc
    # 10. release

具体流程：

阶段 1：参数确认
- 根据用户指令确定 fixed_segment_color；
- 根据用户指令确定 moving_segment_color；
- 确认两个颜色尺段应当相邻；
- 确认使用的是这两个颜色尺段之间的连接关节。

阶段 2：预定位
- 定位 fixed_grasp_position；
- 定位 moving_grasp_position；
- 定位 fixed_segment_midpoint；
- 定位 moving_segment_midpoint；
- 定位 hinge_observed_position，即两个指定颜色尺段之间的连接点；
- 保存全部定位结果。

阶段 3：几何计算
- 根据两个尺段中点和尺长计算两个候选 hinge；
- 根据 hinge_observed_position 选择正确的 hinge_position；
- 根据 moving_grasp_position、hinge_position、angle、direction 计算 target_position；
- 根据圆弧生成 waypoints；
- 输出完整 rotation_plan。

阶段 4：预检查
- 检查 fixed_grasp_position 是否在 fixed_arm 工作空间内；
- 检查 moving_grasp_position 是否在 moving_arm 工作空间内；
- 检查每个 waypoint 是否在 moving_arm 工作空间内；
- 检查 IK 是否可解；
- 如果 dry_run=True，则只返回 rotation_plan，不执行机器人动作。

阶段 5：机器人执行
推荐先保守顺序执行，不要一开始就双臂并行：

1. fixed_arm 移动到 fixed_grasp_position 上方 approach_height；
2. fixed_arm 下降到 fixed_grasp_position；
3. fixed_arm 夹爪闭合，抓住固定段；
4. fixed_arm 保持当前位置，不回 home，不释放；
5. moving_arm 移动到 moving_grasp_position 上方 approach_height；
6. moving_arm 下降到 moving_grasp_position；
7. moving_arm 夹爪闭合，抓住旋转段；
8. moving_arm 按 waypoints 顺序逐点移动，带动尺子绕 hinge_position 旋转；
9. moving_arm 打开夹爪释放；
10. fixed_arm 打开夹爪释放；
11. 根据现有系统习惯，可选择是否撤回到一个很小的安全高度，但不能在旋转过程中 home。

阶段 6：返回结果
返回 JSON 中至少包含：
- success
- message
- fixed_arm
- moving_arm
- fixed_segment_color
- moving_segment_color
- fixed_grasp_position
- moving_grasp_position
- fixed_segment_midpoint
- moving_segment_midpoint
- hinge_observed_position
- candidate_hinges
- hinge_position
- hinge_selection_reason
- target_position
- waypoints
- angle_degrees
- direction
- failed_stage，如果失败
- failed_waypoint_index，如果路径中某个点不可达
- warnings

====================
十一、下层动作原语要求
====================

请新增一个负责“沿圆弧逐点移动”的下层原语，例如：

def follow_arc_waypoints(
    arm: str,
    waypoints: List[List[float]],
    orientation: Optional[List[float]] = None,
    speed: float = 0.10
) -> Dict

要求：
- 逐个 waypoint 调用 driver.move_to_pose；
- 默认末端姿态保持向下，例如沿用项目中 pick/place 的默认 orientation；
- 每个 waypoint 执行失败时立即停止，并返回失败；
- 每一步输出日志；
- 速度默认低一些，例如 0.10 到 0.15，避免真实尺子被拉偏；
- 不要自动打开夹爪；
- 不要自动 home；
- 不要重新拍照定位。

也可以新增：

def controlled_grasp_at_position(...)
def hold_position(...)

但要尽量复用现有底层 driver 方法，避免重复代码。

====================
十二、日志与调试要求
====================

请添加详细日志，方便实机调试：

- 解析出的 fixed_segment_color 和 moving_segment_color；
- 每个 VLM 定位点的名称、坐标、confidence；
- fixed_segment_midpoint；
- moving_segment_midpoint；
- hinge_observed_position；
- 两个候选 hinge 的坐标；
- 每个候选 hinge 到 observed_hinge 的距离；
- 最终选择哪个 hinge，以及选择原因；
- angle 和 direction；
- target_position；
- waypoints 列表；
- 每个 waypoint 的 safety check 和 IK check 结果；
- 执行到第几个 waypoint；
- 失败阶段和错误原因。

必须支持 dry_run=True，用于只计算和打印 rotation_plan，不控制机器人移动。

====================
十三、测试要求
====================

请至少新增或修改测试/示例脚本，例如：

examples/hold_and_rotate_demo.py
tests/test_hold_and_rotate_geometry.py

几何单元测试至少覆盖：

1. rotate_point_around_center_xy：
   - center=[0,0,0]
   - point=[1,0,0]
   - counterclockwise 90° => approximately [0,1,0]
   - clockwise 90° => approximately [0,-1,0]

2. plan_arc_waypoints_xy：
   - 90° 旋转生成多个点；
   - 所有点到 center 的半径基本一致；
   - 最后一个点等于目标点；
   - Z 坐标不变。

3. estimate_hinge_center_from_two_midpoints_and_observed_joint：
   - 给定两个尺段中点和 observed_hinge，能从两个候选圆交点中选出距离 observed_hinge 更近的那个；
   - 对少量 VLM 噪声有容忍；
   - 支持 2 段尺子 1 个关节的情况；
   - 不依赖 third_segment_midpoint；
   - 如果两个中点距离与 segment_length 明显不一致，返回清晰错误，而不是静默生成错误结果。

如果项目当前没有 pytest 框架，也请至少提供一个可运行的 Python demo，以 dry_run 模式打印完整 plan。

====================
十四、工程约束
====================

1. 不要大规模重构现有系统。
2. 不要破坏已有 API。
3. 不要删除已有功能。
4. 不要把这个任务写成普通 pick/place 任务。
5. 不要在旋转执行过程中重新拍照、重新定位或回 home。
6. 所有动作开始前必须完成定位和路径规划。
7. 路径规划先用 XY 平面圆弧 waypoint 实现，保持 Z 不变。
8. 不要使用第三段尺段或中间段几何约束来消除关节二义性。
9. 关节二义性必须通过 VLM 额外定位两个指定颜色尺段之间的连接点来解决。
10. 对于 3 段尺子、2 个关节的物体，必须根据 fixed_segment_color 和 moving_segment_color 定位它们之间的那个关节，不能定位另一个关节。
11. 如果代码中发现已有函数会产生不适合本任务的副作用，请不要直接调用它，而是调用更底层的 driver/primitives 方法或新增专用函数。
12. 如果真实代码结构与以上文件名或函数名有差异，请以实际代码为准，但功能目标不能改变。
13. 最后请给出修改文件列表、核心实现说明、运行方式和测试方式。

====================
十五、最终交付
====================

完成后请输出：

1. 修改了哪些文件；
2. 新增了哪些 API；
3. 新增了哪些 skill；
4. 新增了哪些 primitives/helper；
5. VLM 定位逻辑说明；
6. 颜色如何决定参与任务的两个尺段和关节；
7. 旋转中心几何计算逻辑说明；
8. 如何通过 hinge_observed_position 消除两个圆交点的二义性；
9. 如何 dry_run 测试；
10. 如何实机调用；
11. 有哪些安全注意事项；
12. 当前实现的已知限制。

请开始实现。