"""Robot lifecycle and state management."""

from typing import Dict, Optional
import yaml

from .drivers.base import ArmDriver
from .drivers.baxter_driver import BaxterDriver
from .drivers.mock_driver import MockDriver
from .primitives import BaxterPrimitives
from .safety import SafetyValidator
from .vlm_client import VLMClient
from .grasp_verifier import GraspVerifier


class ArmManager:
    """Manages robot connection, state, and high-level operations.

    Coordinates between driver, primitives, and safety validator.
    """

    def __init__(
        self,
        config_path: str = None,
        enable_grasp_verification: bool = False,
        grasp_verify_retries: int = 2
    ):
        """Initialize arm manager.

        Args:
            config_path: Path to configuration YAML file
            enable_grasp_verification: Enable post-grasp verification (experimental)
            grasp_verify_retries: Maximum retry attempts for failed grasps
        """
        self.config = self._load_config(config_path)

        # Initialize components
        self.driver = self._create_driver()
        self.safety = SafetyValidator(config_path)

        # Initialize VLM client if configured
        self.vlm_client = self._create_vlm_client()

        # Initialize grasp verifier (experimental feature)
        self.grasp_verifier = None
        if enable_grasp_verification:
            if self.vlm_client:
                self.grasp_verifier = GraspVerifier(
                    self.driver,
                    self.vlm_client,
                    enabled=True,
                    max_retries=grasp_verify_retries,
                    debug=True  # Save debug images
                )
                print(f"[ArmManager] Grasp verification enabled (max_retries={grasp_verify_retries})")
            else:
                print("[ArmManager] Warning: Grasp verification requested but VLM not configured")

        self.primitives = BaxterPrimitives(
            self.driver,
            self.safety,
            self.vlm_client,
            grasp_verifier=self.grasp_verifier  # Pass verifier to primitives
        )

        self._connected = False
        self._enabled = False

    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from YAML file."""
        if config_path is None:
            # Default configuration
            return {
                'driver': {'type': 'mock'},
                'robot': {'arms': ['right']},
            }

        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"Warning: Could not load config from {config_path}: {e}")
            return {'driver': {'type': 'mock'}}

    def _create_driver(self) -> ArmDriver:
        """Create appropriate driver based on configuration."""
        driver_type = self.config.get('driver', {}).get('type', 'mock')
        use_depth_camera = self.config.get('driver', {}).get('use_depth_camera', False)

        if driver_type == 'baxter':
            print(f"Creating BaxterDriver (real hardware, depth_camera={use_depth_camera})")
            return BaxterDriver(use_depth_camera=use_depth_camera)
        elif driver_type == 'mock':
            print("Creating MockDriver (simulation)")
            return MockDriver()
        else:
            raise ValueError(f"Unknown driver type: {driver_type}")

    def _create_vlm_client(self) -> Optional[VLMClient]:
        """Create VLM client if configured."""
        vlm_config = self.config.get('vlm', {})

        if not vlm_config.get('enabled', False):
            print("VLM client disabled")
            return None

        provider = vlm_config.get('provider', 'claude')
        api_key = vlm_config.get('api_key')

        print(f"Creating VLM client (provider: {provider})")
        return VLMClient(provider=provider, api_key=api_key)

    def connect(self) -> bool:
        """Connect to robot."""
        if self._connected:
            print("Already connected")
            return True

        success = self.driver.connect()
        if success:
            self._connected = True
            print("Robot connected successfully")
        else:
            print("Failed to connect to robot")

        return success

    def disconnect(self) -> bool:
        """Disconnect from robot."""
        if not self._connected:
            return True

        if self._enabled:
            self.disable()

        success = self.driver.disconnect()
        if success:
            self._connected = False
            print("Robot disconnected")

        return success

    def enable(self) -> bool:
        """Enable robot motors."""
        if not self._connected:
            print("Not connected to robot")
            return False

        if self._enabled:
            print("Robot already enabled")
            return True

        success = self.driver.enable()
        if success:
            self._enabled = True
            print("Robot enabled")
        else:
            print("Failed to enable robot")

        return success

    def disable(self) -> bool:
        """Disable robot motors."""
        if not self._enabled:
            return True

        success = self.driver.disable()
        if success:
            self._enabled = False
            print("Robot disabled")

        return success

    def get_status(self, arm: str = 'right') -> Dict:
        """Get current robot status.

        Args:
            arm: 'left' or 'right'

        Returns:
            Dict containing connection status, joint angles, pose, gripper state
        """
        status = {
            'connected': self._connected,
            'enabled': self._enabled,
            'arm': arm,
            'joint_angles': {},
            'endpoint_pose': [0.0] * 6,
            'gripper_position': 0.0,
            'gripper_force': 0.0,
        }

        if self._connected:
            status['joint_angles'] = self.driver.get_joint_angles(arm)
            status['endpoint_pose'] = self.driver.get_endpoint_pose(arm)
            gripper_pos, gripper_force = self.driver.get_gripper_state(arm)
            status['gripper_position'] = gripper_pos
            status['gripper_force'] = gripper_force

        return status

    def emergency_stop(self) -> bool:
        """Execute emergency stop."""
        print("EMERGENCY STOP TRIGGERED")
        success = self.driver.emergency_stop()
        if success:
            self._enabled = False
        return success
