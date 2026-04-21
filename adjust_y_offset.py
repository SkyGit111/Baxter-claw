#!/usr/bin/env python3
"""
微调Y轴偏移量
"""

import yaml
import sys

def adjust_y_offset(delta_y: float):
    """调整Y轴偏移量

    Args:
        delta_y: Y轴增量（米），正值向右，负值向左
    """

    config_file = "config/position_correction.yaml"

    try:
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)

        current_y = config['d455_position_correction']['offset']['y']
        new_y = current_y + delta_y

        print(f"当前Y轴偏移: {current_y:.4f}m")
        print(f"调整量: {delta_y:+.4f}m")
        print(f"新Y轴偏移: {new_y:.4f}m")

        # 更新配置
        config['d455_position_correction']['offset']['y'] = float(new_y)

        with open(config_file, 'w') as f:
            yaml.dump(config, f, default_flow_style=False)

        print(f"\n✓ 已更新配置文件")
        print(f"\n重新测试以验证效果")

    except Exception as e:
        print(f"错误: {e}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("用法: python adjust_y_offset.py <delta_y>")
        print("示例:")
        print("  python adjust_y_offset.py -0.02   # Y轴向左调整2cm")
        print("  python adjust_y_offset.py +0.03   # Y轴向右调整3cm")
        sys.exit(1)

    try:
        delta_y = float(sys.argv[1])
        adjust_y_offset(delta_y)
    except ValueError:
        print("错误: delta_y必须是数字")
        sys.exit(1)
