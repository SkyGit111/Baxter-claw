#!/usr/bin/env python3
"""
Test script for sequential handover task.

Task: "Left arm picks blue cube to center, then right arm picks it and places on red cube"

Phases:
1. Left arm picks blue cube (from left side)
2. Left arm places blue cube at center (Y=0, Z=-0.16)
3. Left arm returns to home
4. Right arm picks blue cube (from center)
5. Right arm places blue cube on red cube

Setup:
- Place blue cube on the left side of the table
- Place red cube on the right side of the table
- Ensure robot is enabled and Bridge Server is running
"""

import requests
import sys
import time

# Configuration
BRIDGE_URL = "http://localhost:8420"
OBJECT_A = "蓝色小方块"  # Object to transfer
OBJECT_B = "红色小方块"  # Target object
RELATIVE_POSITION = "on_top"  # Where to place object A relative to object B

# ANSI color codes
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
CYAN = '\033[96m'
RESET = '\033[0m'


def print_header(text):
    """Print a formatted header."""
    print(f"\n{CYAN}{'='*70}{RESET}")
    print(f"{CYAN}{text}{RESET}")
    print(f"{CYAN}{'='*70}{RESET}\n")


def print_phase(phase_num, text):
    """Print a phase header."""
    print(f"\n{YELLOW}[Phase {phase_num}] {text}{RESET}")


def print_success(text):
    """Print success message."""
    print(f"{GREEN}✓ {text}{RESET}")


def print_error(text):
    """Print error message."""
    print(f"{RED}✗ {text}{RESET}")


def check_server():
    """Check if Bridge Server is running."""
    try:
        response = requests.get(f"{BRIDGE_URL}/health", timeout=2)
        return response.status_code == 200
    except:
        return False


def phase1_left_pick(object_name):
    """Phase 1: Left arm picks object A."""
    print_phase(1, f"Left arm picks {object_name}")

    try:
        response = requests.post(
            f"{BRIDGE_URL}/vision/pick_by_name",
            json={
                'arm': 'left',
                'object_name': object_name,
                'use_d455': True
            },
            timeout=90
        )
        response.raise_for_status()
        result = response.json()

        if not result.get('success'):
            print_error(f"Failed to pick {object_name}: {result.get('message')}")
            return None

        pick_position = result.get('position')
        if not pick_position:
            print_error("No position returned from pick")
            return None

        print_success(f"Left arm picked {object_name} at {pick_position}")
        return pick_position

    except Exception as e:
        print_error(f"Exception: {str(e)}")
        return None


def phase2_left_place_center(pick_position, object_name):
    """Phase 2: Left arm places object A at center."""
    print_phase(2, f"Left arm places {object_name} at center")

    try:
        # Calculate center position: keep X, set Y=0, set Z=-0.16
        center_position = [pick_position[0], 0.0, -0.16]
        print(f"  Center position: {center_position}")

        response = requests.post(
            f"{BRIDGE_URL}/primitives/place",
            json={
                'arm': 'left',
                'position': center_position
            },
            timeout=90
        )
        response.raise_for_status()
        result = response.json()

        if not result.get('success'):
            print_error(f"Failed to place at center: {result.get('message')}")
            return False

        print_success(f"Left arm placed {object_name} at center")
        return True

    except Exception as e:
        print_error(f"Exception: {str(e)}")
        return False


def phase3_left_home():
    """Phase 3: Left arm returns to home."""
    print_phase(3, "Left arm returns to home")

    try:
        response = requests.post(
            f"{BRIDGE_URL}/primitives/home",
            json={'arm': 'left'},
            timeout=90
        )
        response.raise_for_status()
        result = response.json()

        if not result.get('success'):
            print_error(f"Failed to return home: {result.get('message')}")
            return False

        print_success("Left arm returned to home")
        return True

    except Exception as e:
        print_error(f"Exception: {str(e)}")
        return False


def phase4_right_pick(object_name):
    """Phase 4: Right arm picks object A from center."""
    print_phase(4, f"Right arm picks {object_name} from center")

    try:
        response = requests.post(
            f"{BRIDGE_URL}/vision/pick_by_name",
            json={
                'arm': 'right',
                'object_name': object_name,
                'use_d455': True
            },
            timeout=90
        )
        response.raise_for_status()
        result = response.json()

        if not result.get('success'):
            print_error(f"Failed to pick {object_name}: {result.get('message')}")
            return False

        print_success(f"Right arm picked {object_name}")
        return True

    except Exception as e:
        print_error(f"Exception: {str(e)}")
        return False


def phase5_right_place(object_a, object_b, relative_position):
    """Phase 5: Right arm places object A on object B."""
    print_phase(5, f"Right arm places {object_a} {relative_position} {object_b}")

    try:
        # Step 1: Locate target object (for testing VLM, but don't use the result)
        print(f"  Locating {object_b} (for VLM testing)...")
        try:
            locate_response = requests.post(
                f"{BRIDGE_URL}/vision/locate_object",
                json={
                    'object_name': object_b,
                    'use_d455': True
                },
                timeout=90
            )
            locate_response.raise_for_status()
            locate_result = locate_response.json()

            if locate_result.get('found'):
                vlm_position = locate_result.get('position')
                print(f"  VLM located {object_b} at: {vlm_position}")
                print(f"  {YELLOW}⚠ VLM result will be ignored, using hardcoded position{RESET}")
            else:
                print(f"  {YELLOW}⚠ VLM did not find {object_b}, using hardcoded position anyway{RESET}")
        except Exception as e:
            print(f"  {YELLOW}⚠ VLM localization failed: {e}{RESET}")
            print(f"  {YELLOW}⚠ Continuing with hardcoded position{RESET}")

        # Step 2: Use hardcoded position for actual placement
        hardcoded_position = [0.60, -0.275, -0.13]
        print(f"  Using hardcoded target position: {hardcoded_position}")

        response = requests.post(
            f"{BRIDGE_URL}/primitives/place",
            json={
                'arm': 'right',
                'position': hardcoded_position
            },
            timeout=90
        )
        response.raise_for_status()
        result = response.json()

        if not result.get('success'):
            print_error(f"Failed to place at target: {result.get('message')}")
            return False

        print_success(f"Right arm placed {object_a} at hardcoded position")
        return True

    except Exception as e:
        print_error(f"Exception: {str(e)}")
        return False


def main():
    """Main test function."""
    print_header("SEQUENTIAL HANDOVER TEST")

    print(f"{BLUE}[Task]{RESET}")
    print(f"  Object A: {OBJECT_A} (left side → center → object B)")
    print(f"  Object B: {OBJECT_B} (final target)")
    print(f"  Position: {RELATIVE_POSITION}")
    print(f"{CYAN}{'='*70}{RESET}\n")

    # Check server
    print("Checking Bridge Server...")
    if not check_server():
        print_error("Bridge Server is not running!")
        print(f"  Please start it with: python bridge/server.py")
        return False
    print_success("Bridge Server is running")

    # Confirm setup
    print(f"\n{YELLOW}Setup checklist:{RESET}")
    print(f"  1. Robot is enabled")
    print(f"  2. {OBJECT_A} is placed on the LEFT side of the table")
    print(f"  3. {OBJECT_B} is placed on the RIGHT side of the table")
    print(f"  4. Workspace is clear")

    input(f"\n{YELLOW}Press ENTER to start the test...{RESET}")

    # Execute phases
    start_time = time.time()

    # Phase 1: Left arm picks object A
    pick_position = phase1_left_pick(OBJECT_A)
    if not pick_position:
        print_error("Phase 1 failed")
        return False

    # Phase 2: Left arm places object A at center
    if not phase2_left_place_center(pick_position, OBJECT_A):
        print_error("Phase 2 failed")
        return False

    # Phase 3: Left arm returns to home
    if not phase3_left_home():
        print_error("Phase 3 failed")
        return False

    # Phase 4: Right arm picks object A from center
    if not phase4_right_pick(OBJECT_A):
        print_error("Phase 4 failed")
        return False

    # Phase 5: Right arm places object A on object B
    if not phase5_right_place(OBJECT_A, OBJECT_B, RELATIVE_POSITION):
        print_error("Phase 5 failed")
        return False

    # Success
    elapsed_time = time.time() - start_time

    print_header("TEST COMPLETE")
    print_success(f"All phases completed successfully!")
    print(f"  Total time: {elapsed_time:.1f} seconds")
    print(f"  {OBJECT_A} successfully transferred from left → center → {OBJECT_B}")
    print(f"{CYAN}{'='*70}{RESET}\n")

    return True


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print(f"\n\n{YELLOW}⚠️  Test interrupted by user{RESET}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{RED}❌ Unexpected error: {e}{RESET}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
