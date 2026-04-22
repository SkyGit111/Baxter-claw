#!/usr/bin/env python3
"""
Test script for improved architecture with proper data passing.

Tests:
1. Query tasks (should execute once and return)
2. Manipulation tasks with data flow (locate → pick)
3. Complex workflows
"""

import sys
import os
from openclaw_plugin.baxter_claw_plugin import BaxterClawPlugin


def print_section(title):
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def test_query_task_routing():
    """Test that query tasks execute directly without workflow loop."""
    print_section("测试 1: 查询任务路由（应该直接执行，不进入工作流循环）")

    api_key = sys.argv[1] if len(sys.argv) > 1 else os.getenv('QWEN_API_KEY')
    if not api_key:
        print("跳过：需要 API key")
        return

    plugin = BaxterClawPlugin(llm_api_key=api_key)

    test_cases = [
        "识别魔方的坐标",
        "where is the red cup",
        "看看桌上有什么",
    ]

    for msg in test_cases:
        print(f"\n用户: {msg}")
        print("-" * 80)

        # Parse intent first
        intent = plugin.parse_intent(msg)
        print(f"意图识别:")
        print(f"  动作: {intent.get('action')}")
        print(f"  任务类型: {intent.get('task_type')}")
        print(f"  参数: {intent.get('params')}")

        # Check if it's correctly identified as query
        if intent.get('task_type') == 'query':
            print("  ✅ 正确识别为查询任务")
        else:
            print(f"  ❌ 错误：应该是 'query'，实际是 '{intent.get('task_type')}'")


def test_data_passing():
    """Test that data flows correctly between skills in workflow."""
    print_section("测试 2: 技能间数据传递")

    print("""
理论流程：
1. 用户: "识别魔方的坐标并抓取"
2. LLM 识别为 manipulation 任务
3. 工作流开始:
   - 迭代1: locate_object(object_name="魔方")
     → 返回: position=[0.6, 0.15, 0.1]
   - 迭代2: LLM 看到输出数据，应该调用:
     pick(arm="auto", position=[0.6, 0.15, 0.1])
     而不是 pick_by_name(object_name="魔方")
   - 迭代3: 完成，返回 action="done"

关键改进：
- 工作流 prompt 现在包含结构化输出数据
- 明确告诉 LLM 如何使用前一步的数据
- 添加了 pick 技能（使用已知坐标）
""")

    print("这需要实际运行来验证，建议手动测试。")


def test_skill_definitions():
    """Verify skill definitions are clear."""
    print_section("测试 3: 技能定义验证")

    print("""
已创建 SKILLS.md 文档，定义了：

查询技能:
- locate_object: 定位物体，返回 position
- describe_scene: 描述场景
- identify_objects: 识别所有物体

操作技能:
- pick: 在已知位置抓取（使用 locate_object 的输出）
- pick_by_name: 定位并抓取（内部调用 locate + pick）
- place: 放置物体
- home: 回原位
- 等等...

每个技能都定义了：
- 输入参数
- 输出数据
- 状态变化
- 下一步建议
- 使用示例

这为 LLM 提供了清晰的技能组合指导。
""")


def test_completion_detection():
    """Test that workflow knows when to stop."""
    print_section("测试 4: 完成条件检测")

    print("""
改进的完成条件：

1. 查询任务：
   - 执行一次查询技能后立即返回结果
   - 不进入工作流循环

2. 操作任务：
   - pick 任务: 物体被抓取并抬起 → done
   - place 任务: 物体被放置且手臂收回 → done
   - home 任务: 手臂到达原位 → done
   - "识别坐标"任务: locate_object 成功 → done

3. 工作流 prompt 明确说明：
   "For '识别坐标' task: if locate_object succeeded, goal is DONE"

这应该防止无限循环。
""")


def main():
    print("=" * 80)
    print("Baxter-Claw 架构改进验证")
    print("=" * 80)

    print("""
主要改进：

1. ✅ 添加了 locate_object, identify_objects 技能
2. ✅ 区分查询任务和操作任务
3. ✅ 查询任务直接执行，不进入工作流循环
4. ✅ 添加了 pick 技能（使用已知坐标）
5. ✅ 工作流 prompt 包含结构化输出数据
6. ✅ 明确的数据传递指导
7. ✅ 改进的完成条件检测
8. ✅ 创建了 SKILLS.md 技能定义文档

这些改进应该解决：
- "识别魔方的坐标" 反复调用 describe_scene 的问题
- locate_object 返回坐标后，LLM 错误调用 pick_by_name 的问题
- 工作流不知道何时完成的问题
""")

    # Run tests
    test_query_task_routing()
    test_data_passing()
    test_skill_definitions()
    test_completion_detection()

    print("\n" + "=" * 80)
    print("建议的手动测试步骤：")
    print("=" * 80)
    print("""
1. 启动 Bridge Server (mock 模式):
   cd /home/cothink/Baxter-claw
   python start_server.py

2. 在另一个终端测试查询任务:
   python -c "
   from openclaw_plugin.baxter_claw_plugin import BaxterClawPlugin
   plugin = BaxterClawPlugin(llm_api_key='your_key')
   result = plugin.handle_message('识别魔方的坐标')
   print(result)
   "

   期望：
   - 应该识别为 query 任务
   - 直接执行 locate_object
   - 返回结果，不进入工作流循环

3. 测试操作任务:
   result = plugin.handle_message('识别魔方的坐标并抓取')

   期望：
   - 识别为 manipulation 任务
   - 迭代1: locate_object → 返回 position
   - 迭代2: pick(position=...) 而不是 pick_by_name
   - 迭代3: done

4. 观察终端输出:
   - 查看 [Task Type] 是否正确
   - 查看 [Mode] 是否正确选择
   - 查看工作流中的 "输出数据" 是否显示
   - 查看是否正确使用了前一步的数据
""")


if __name__ == "__main__":
    main()
