"""Safety validation for robot motions."""

from typing import List, Dict, Tuple
import yaml
from pathlib import Path


class SafetyValidator:
    """Validates robot motions against safety constraints.

    Checks workspace limits, joint limits, and speed constraints
    to prevent dangerous motions.
    """

    def __init__(self, config_path: str = None):
        """Initialize safety validator.

        Args:
            config_path: Path to safety configuration YAML file.
                        If None, uses default safe values.
        """
        self.config = self._load_config(config_path)

        # Baxter joint limits (radians)
        # Source: Baxter SDK documentation
        self.joint_limits = {
            'right': {
                'right_s0': (-1.70167993878, 1.70167993878),
                'right_s1': (-2.147, 1.047),
                'right_e0': (-3.05417993878, 3.05417993878),
                'right_e1': (-0.05, 2.618),
                'right_w0': (-3.059, 3.059),
                'right_w1': (-1.57079632679, 2.094),
                'right_w2': (-3.059, 3.059),
            },
            'left': {
                'left_s0': (-1.70167993878, 1.70167993878),
                'left_s1': (-2.147, 1.047),
                'left_e0': (-3.05417993878, 3.05417993878),
                'left_e1': (-0.05, 2.618),
                'left_w0': (-3.059, 3.059),
                'left_w1': (-1.57079632679, 2.094),
                'left_w2': (-3.059, 3.059),
            }
        }

        # Workspace limits (meters) - conservative safe zone
        self.workspace_limits = self.config.get('workspace', {
            'x': (0.3, 0.9),    # Forward reach
            'y': (-0.7, 0.7),   # Lateral reach
            'z': (-0.2, 0.5),   # Height above table
        })

        # Speed limits
        self.max_speed = self.config.get('max_speed', 0.5)

    def _load_config(self, config_path: str) -> Dict:
        """Load safety configuration from YAML file."""
        if config_path is None:
            return {}

        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
                return config.get('safety', {})
        except Exception as e:
            print(f"Warning: Could not load safety config: {e}")
            return {}

    def check_joint_limits(self, arm: str, positions: Dict[str, float]) -> Tuple[bool, str]:
        """Check if joint positions are within safe limits.

        Args:
            arm: 'left' or 'right'
            positions: Dict of joint names to angles (radians)

        Returns:
            Tuple of (is_safe, error_message)
        """
        if arm not in self.joint_limits:
            return False, f"Unknown arm: {arm}"

        limits = self.joint_limits[arm]

        for joint_name, angle in positions.items():
            if joint_name not in limits:
                return False, f"Unknown joint: {joint_name}"

            min_angle, max_angle = limits[joint_name]
            if angle < min_angle or angle > max_angle:
                return False, (
                    f"Joint {joint_name} angle {angle:.3f} outside limits "
                    f"[{min_angle:.3f}, {max_angle:.3f}]"
                )

        return True, ""

    def check_workspace(self, arm: str, pose: List[float]) -> Tuple[bool, str]:
        """Check if Cartesian pose is within safe workspace.

        Args:
            arm: 'left' or 'right'
            pose: [x, y, z, roll, pitch, yaw]

        Returns:
            Tuple of (is_safe, error_message)
        """
        x, y, z = pose[0], pose[1], pose[2]

        x_min, x_max = self.workspace_limits['x']
        y_min, y_max = self.workspace_limits['y']
        z_min, z_max = self.workspace_limits['z']

        if not (x_min <= x <= x_max):
            return False, f"X position {x:.3f} outside limits [{x_min}, {x_max}]"

        if not (y_min <= y <= y_max):
            return False, f"Y position {y:.3f} outside limits [{y_min}, {y_max}]"

        if not (z_min <= z <= z_max):
            return False, f"Z position {z:.3f} outside limits [{z_min}, {z_max}]"

        return True, ""

    def check_speed(self, speed: float) -> Tuple[bool, str]:
        """Check if speed is within safe limits.

        Args:
            speed: Speed ratio (0-1)

        Returns:
            Tuple of (is_safe, error_message)
        """
        if speed < 0 or speed > self.max_speed:
            return False, f"Speed {speed} outside limits [0, {self.max_speed}]"

        return True, ""

    def validate_motion(
        self,
        arm: str,
        target_type: str,
        target: any,
        speed: float = 0.3
    ) -> Tuple[bool, str]:
        """Comprehensive motion validation.

        Args:
            arm: 'left' or 'right'
            target_type: 'joint' or 'pose'
            target: Joint positions dict or pose list
            speed: Motion speed

        Returns:
            Tuple of (is_safe, error_message)
        """
        # Check speed
        is_safe, msg = self.check_speed(speed)
        if not is_safe:
            return False, msg

        # Check target
        if target_type == 'joint':
            return self.check_joint_limits(arm, target)
        elif target_type == 'pose':
            return self.check_workspace(arm, target)
        else:
            return False, f"Unknown target type: {target_type}"
