现在需要基于新的真实任务道具修改上一版 bimanual hold-and-rotate skill。

真实道具结构已经改变并固定如下：

红色尺段 -- 绿色旋转关节 -- 黄色尺段 -- 橙色旋转关节 -- 蓝色尺段

当前任务不再要求机器人抓黄色尺段，也不再要求蓝色尺段绕某个固定旋转关节做简单圆弧运动。新的任务是：

- 左臂抓住红色尺段并保持不动；
- 右臂抓住蓝色尺段；
- 右臂移动蓝色抓取点，带动黄色尺段和蓝色尺段发生平面构型变化；
- 初始构型为 S 型；
- 目标构型为 L 型；
- 整个过程只执行一次连续构型调整动作，中途不能回 home，不能重新拍照定位，不能释放后再抓。

请不要继续使用“通过两个尺段中点和尺段长度反推旋转关节”的旧逻辑。这个逻辑在真实道具上不可靠。现在绿色关节和橙色关节都已经贴上彩色胶带，因此旋转关节坐标应当像抓取点一样，直接通过 VLM + D455 定位。

请新增或重构为新的 skill，建议命名为：

bimanual_shape_ruler

或者：

bimanual_ruler_shape_adjustment

不要把它继续实现成普通 pick/place，也不要实现成单关节 hold-and-rotate。

====================
一、配置文件要求
====================

请新增配置文件或配置项，例如 config/ruler_task.yaml，用于描述当前道具颜色和任务角色。默认配置为：

articulated_ruler:
  segments:
    fixed:
      name: red_segment
      color: red
      grasp_prompt: "红色尺段远离绿色关节一端的抓取块中心"

    middle:
      name: yellow_segment
      color: yellow
      midpoint_prompt: "黄色尺段的几何中点"

    moving:
      name: blue_segment
      color: blue
      grasp_prompt: "蓝色尺段远离橙色关节一端的抓取块中心"

  joints:
    fixed_joint:
      name: green_joint
      color: green
      prompt: "红色尺段和黄色尺段之间的绿色旋转关节中心"

    moving_joint:
      name: orange_joint
      color: orange
      prompt: "黄色尺段和蓝色尺段之间的橙色旋转关节中心"

  default_task:
    fixed_arm: left
    moving_arm: right
    fixed_segment: red_segment
    moving_segment: blue_segment
    target_shape: L
    l_shape_blue_turn_direction: clockwise
    waypoint_count: 10
    speed: 0.10

颜色、段名、关节名和 prompt 都必须可以通过配置文件修改，不要硬编码。

====================
二、VLM 直接定位要求
====================

动作开始前必须一次性完成全部定位。需要定位：

R = red_grasp_position
  即红色尺段抓取点

B = blue_grasp_position
  即蓝色尺段抓取点

G = green_joint_position
  即红色尺段和黄色尺段之间的绿色旋转关节中心

O = orange_joint_position
  即黄色尺段和蓝色尺段之间的橙色旋转关节中心

请复用现有 VLM + D455 定位能力。如果现有 locate_object 只能定位物体中心，请封装 locate_named_point(description)，使其能够根据配置文件中的 prompt 定位指定点。

后续计算和执行阶段只能使用本次预定位结果，不允许中途重新拍照定位。

====================
三、几何模型改变
====================

旧模型：
- 蓝色抓取点绕某个固定关节做圆弧。

新模型：
- 左臂固定红色尺段，因此绿色关节 G 可以近似视为固定锚点；
- 黄色尺段连接 G 和 O；
- 蓝色尺段连接 O 和 B；
- 右臂控制 B 点移动；
- O 点随黄色尺段和蓝色尺段被动运动；
- 这是一个 G-O-B 的平面二连杆链条构型调整问题。

请不要把 B 点轨迹规划成绕 O 点的固定圆弧，因为 O 点在任务过程中不是固定点。

====================
四、L 型目标构型计算
====================

已知当前定位点：

R = 红色抓取点
G = 绿色关节
O = 橙色关节
B = 蓝色抓取点

全部计算只使用 XY 平面，Z 坐标保持不变。

首先计算当前实际等效长度：

L1 = distance_xy(G, O)
L2 = distance_xy(O, B)

不要强行使用理论尺长 0.15 来计算目标位置，因为真实抓取点和关节位置可能存在偏差。0.15 只作为 sanity check 或配置参考。

定义红色尺段方向：

u_red = normalize_xy(G - R)

默认 L 型目标定义为：

- 黄色尺段方向与红色尺段方向共线，作为红色尺段的延长线；
- 蓝色尺段方向与黄色尺段方向垂直；
- 垂直方向由配置项 l_shape_blue_turn_direction 决定，clockwise 或 counterclockwise。

因此：

u_yellow_target = u_red

if l_shape_blue_turn_direction == "clockwise":
    u_blue_target = rotate90_clockwise(u_yellow_target)
else:
    u_blue_target = rotate90_counterclockwise(u_yellow_target)

O_target = G + L1 * u_yellow_target
B_target = O_target + L2 * u_blue_target

最终右臂需要移动到 B_target。

请返回并记录：
- R
- G
- O
- B
- L1
- L2
- u_red
- O_target
- B_target
- target_shape

====================
五、路径规划要求
====================

不要使用单圆弧路径。请用二连杆角度插值生成蓝色抓取点 B 的 waypoint。

当前角度：

theta1_current = atan2(O_y - G_y, O_x - G_x)
theta2_current = atan2(B_y - O_y, B_x - O_x)

目标角度：

theta1_target = atan2(u_yellow_target_y, u_yellow_target_x)
theta2_target = atan2(u_blue_target_y, u_blue_target_x)

对 theta1 和 theta2 同时做角度插值，生成 N 个 waypoint。N 从配置读取，默认 10。

对于第 k 个插值：

theta1_k = interpolate_angle(theta1_current, theta1_target, ratio_k)
theta2_k = interpolate_angle(theta2_current, theta2_target, ratio_k)

O_k = G + L1 * [cos(theta1_k), sin(theta1_k)]
B_k = O_k + L2 * [cos(theta2_k), sin(theta2_k)]

右臂只需要依次移动到 B_k。O_k 是用于计算路径的虚拟随动关节点，不需要机器人直接控制。

所有 B_k 的 z 坐标保持为 B 的当前 z，或者使用配置中的 constant_z。

每个 waypoint 执行前都要进行：
- workspace safety check；
- IK reachability check；
- 如果不可达，dry_run 或执行前应直接返回失败，说明 failed_waypoint_index。

====================
六、执行流程
====================

新增高级 primitive，例如：

async def bimanual_shape_ruler(...)

执行流程为：

1. 读取 ruler_task 配置；
2. 定位 R、G、O、B；
3. 计算当前构型；
4. 根据 L 型目标定义计算 O_target 和 B_target；
5. 生成 B 点 waypoints；
6. 对所有 waypoints 做 safety 和 IK 检查；
7. 如果 dry_run=True，只返回完整 plan，不执行机器人；
8. 左臂移动到 R 上方；
9. 左臂下降到 R；
10. 左臂闭合夹爪，固定红色尺段；
11. 左臂保持当前位置，不回 home，不释放；
12. 右臂移动到 B 上方；
13. 右臂下降到 B；
14. 右臂闭合夹爪，抓住蓝色尺段；
15. 右臂按 B waypoints 连续移动，带动尺子从 S 型接近 L 型；
16. 右臂释放；
17. 左臂释放；
18. 返回执行结果。

中途禁止：
- 回 home；
- 重新拍照；
- 重新定位；
- 调用旧的完整 pick/place；
- 把蓝色段当作绕固定橙色关节转动。

====================
七、返回结果
====================

返回 JSON 至少包含：

success
message
fixed_arm
moving_arm
target_shape
red_grasp_position
blue_grasp_position
green_joint_position
orange_joint_position
L1
L2
O_target
B_target
waypoints
failed_stage
failed_waypoint_index
warnings

====================
八、测试要求
====================

必须支持 dry_run=True。

请增加几何测试：

1. 给定 R、G、O、B，能计算 L1、L2；
2. 能根据 L 型定义计算 O_target、B_target；
3. waypoint 数量正确；
4. 第一个 waypoint 接近当前 B；
5. 最后一个 waypoint 接近 B_target；
6. 所有 waypoint 的 z 坐标不变；
7. 所有 waypoint 对应的 G-O_k 长度等于 L1；
8. 所有 waypoint 对应的 O_k-B_k 长度等于 L2。

最后输出修改文件列表、运行方式、dry_run 示例和实机调用示例。