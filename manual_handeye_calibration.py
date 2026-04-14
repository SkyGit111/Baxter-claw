#!/usr/bin/env python
"""
手动 Hand-Eye 标定脚本
不依赖 rqt GUI，直接使用 ROS 服务
"""

import rospy
from easy_handeye.handeye_client import HandeyeClient

def manual_calibration():
    rospy.init_node('manual_handeye_calibration')

    # 连接到标定服务
    namespace = 'baxter_d455_handeye_calibration_eye_on_hand'
    client = HandeyeClient()
    client.init_from_namespace(namespace)

    print("="*60)
    print("手动 Hand-Eye 标定")
    print("="*60)
    print()
    print("命令:")
    print("  s - 采集当前样本")
    print("  l - 列出所有样本")
    print("  d <n> - 删除样本 n")
    print("  c - 计算标定结果")
    print("  v - 保存标定结果")
    print("  q - 退出")
    print()
    print("请移动机器人到不同位置，确保 marker 在相机视野内")
    print("每个位置输入 's' 采集样本")
    print()

    sample_count = 0

    while not rospy.is_shutdown():
        try:
            cmd = input(f"[{sample_count} 个样本] 命令: ").strip().lower()

            if cmd == 's':
                # 采集样本
                print("正在采集样本...")
                client.take_sample()
                sample_count += 1
                print(f"✓ 样本 {sample_count} 已采集")

            elif cmd == 'l':
                # 列出样本
                samples = client.get_sample_list()
                print(f"\n已采集 {len(samples.hand_world_samples.transforms)} 个样本")
                for i in range(len(samples.hand_world_samples.transforms)):
                    print(f"  样本 {i+1}")
                print()

            elif cmd.startswith('d '):
                # 删除样本
                try:
                    idx = int(cmd.split()[1]) - 1
                    client.remove_sample(idx)
                    sample_count -= 1
                    print(f"✓ 样本 {idx+1} 已删除")
                except:
                    print("✗ 无效的样本编号")

            elif cmd == 'c':
                # 计算标定
                if sample_count < 5:
                    print(f"✗ 样本不足，至少需要 5 个样本（当前 {sample_count} 个）")
                    continue

                print("\n正在计算标定结果...")
                print("可用算法:")
                algorithms = client.list_algorithms()
                for i, alg in enumerate(algorithms.algorithms):
                    print(f"  {i+1}. {alg}")

                # 使用默认算法
                result = client.compute_calibration()

                if result.valid:
                    print("\n✓ 标定成功!")
                    print(f"平移 (x, y, z): {result.calibration.transform.translation.x:.4f}, "
                          f"{result.calibration.transform.translation.y:.4f}, "
                          f"{result.calibration.transform.translation.z:.4f}")
                    print(f"旋转 (x, y, z, w): {result.calibration.transform.rotation.x:.4f}, "
                          f"{result.calibration.transform.rotation.y:.4f}, "
                          f"{result.calibration.transform.rotation.z:.4f}, "
                          f"{result.calibration.transform.rotation.w:.4f}")
                else:
                    print("✗ 标定失败")
                print()

            elif cmd == 'v':
                # 保存标定
                print("正在保存标定结果...")
                client.save()
                print("✓ 标定结果已保存")
                print()

            elif cmd == 'q':
                print("退出标定")
                break

            else:
                print("未知命令")

        except KeyboardInterrupt:
            print("\n退出标定")
            break
        except Exception as e:
            print(f"错误: {e}")

if __name__ == '__main__':
    try:
        manual_calibration()
    except rospy.ROSInterruptException:
        pass