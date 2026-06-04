#!/usr/bin/env python
"""Test script for sequential handover skill."""

import httpx

def test_sequential_handover():
    """Test the new sequential handover skill."""
    
    client = httpx.Client(timeout=300.0)
    bridge_url = "http://localhost:8420"
    
    print("=" * 70)
    print("Testing Sequential Handover Skill")
    print("=" * 70)
    print("\nScenario:")
    print("  1. 蓝色小方块 on left side")
    print("  2. 红色小方块 on right side")
    print("  3. Left arm picks 蓝色小方块 → places at center (Y=0)")
    print("  4. Left arm returns home")
    print("  5. Right arm picks 蓝色小方块 from center → places on 红色小方块")
    print("=" * 70)
    
    input("\nPress Enter to start test...")
    
    # This would be called by OpenClaw plugin
    # For direct testing, we can call the bridge endpoints manually
    
    print("\n[Manual Test Steps]")
    print("1. Place 蓝色小方块 on the left side of the table")
    print("2. Place 红色小方块 on the right side of the table")
    print("3. In OpenClaw, say:")
    print('   "先用左手抓取蓝色小方块放到中间，再用右手抓取它放到红色小方块上"')
    print("\nThe LLM should recognize this as 'sequential_handover' skill")
    print("with parameters:")
    print("  object_a: 蓝色小方块")
    print("  object_b: 红色小方块")
    print("  relative_position: on_top")

if __name__ == '__main__':
    test_sequential_handover()
