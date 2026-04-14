#!/usr/bin/env python
"""
修复版 rqt_easy_handeye 启动脚本
"""

import sys
import rospy
from qt_gui.main import Main

def main():
    # 初始化 ROS 节点
    rospy.init_node('rqt_easy_handeye_fixed', anonymous=True)

    # 设置 namespace
    namespace = 'baxter_d455_handeye_calibration_eye_on_hand'
    rospy.set_param('/rqt_easy_handeye/namespace', namespace)

    # 启动 rqt 并加载 easy_handeye 插件
    plugin = 'rqt_easy_handeye'
    main = Main(filename=plugin)

    # 传递 namespace 参数
    sys.argv.extend(['--force-discover'])

    sys.exit(main.main(standalone=plugin, plugin_argument_provider=None))

if __name__ == '__main__':
    main()