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
from .collision_detector import CollisionDetector


class ArmManager:
    """Manages robot connection, state, and high-level operations.

    Coordinates between driver, primitives, and safety validator.
    """

    def __init__(
        self,
        config_path: str = None,
        enable_grasp_verification: bool = None,
        grasp_verify_retries: int = None
    ):
        """Initialize arm manager.

        Args:
            config_path: Path to configuration YAML file
            enable_grasp_verification: Enable post-grasp verification (experimental)
                                      If None, reads from config file
            grasp_verify_retries: Maximum retry attempts for failed grasps
                                 If None, reads from config file
        """
        self.config = self._load_config(config_path)

        # Initialize components
        self.driver = self._create_driver()
        self.safety = SafetyValidator(config_path)

        # Initialize VLM client if configured
        self.vlm_client = self._create_vlm_client()

        # Initialize grasp verifier (experimental feature)
        self.grasp_verifier = self._create_grasp_verifier(
            enable_grasp_verification,
            grasp_verify_retries
        )

        # Initialize collision detector (experimental feature)
        self.collision_detector = self._create_collision_detector()

        self.primitives = BaxterPrimitives(
            self.driver,
            self.safety,
            self.vlm_client,
            grasp_verifier=self.grasp_verifier,  # Pass verifier to primitives
            collision_detector=self.collision_detector  # Pass collision detector to primitives
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
        ik_solver_type = self.config.get('driver', {}).get('ik_solver', 'enhanced')

        if driver_type == 'baxter':
            print(f"Creating BaxterDriver (real hardware, depth_camera={use_depth_camera}, ik_solver={ik_solver_type})")
            return BaxterDriver(use_depth_camera=use_depth_camera, ik_solver_type=ik_solver_type)
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

    def _create_grasp_verifier(
        self,
        enable_override: Optional[bool],
        retries_override: Optional[int]
    ) -> Optional[GraspVerifier]:
        """Create grasp verifier based on configuration.

        Args:
            enable_override: Override config file setting (from command line)
            retries_override: Override config file setting (from command line)

        Returns:
            GraspVerifier instance if enabled, None otherwise
        """
        # Support both top-level and nested config structure for backward compatibility
        grasp_config = self.config.get('experimental', {}).get('grasp_verification', {})
        if not grasp_config:
            grasp_config = self.config.get('grasp_verification', {})

        # Command line arguments override config file
        enabled = enable_override if enable_override is not None else grasp_config.get('enabled', False)
        max_retries = retries_override if retries_override is not None else grasp_config.get('max_retries', 2)
        debug = grasp_config.get('debug', True)

        if not enabled:
            print("[ArmManager] Grasp verification disabled")
            return None

        if not self.vlm_client:
            print("[ArmManager] Warning: Grasp verification requested but VLM not configured")
            return None

        print(f"[ArmManager] Grasp verification enabled (max_retries={max_retries})")
        return GraspVerifier(
            self.driver,
            self.vlm_client,
            enabled=True,
            max_retries=max_retries,
            debug=debug
        )

    def _create_collision_detector(self) -> CollisionDetector:
        """Create collision detector based on configuration."""
        # Support both top-level and nested config structure for backward compatibility
        collision_config = self.config.get('experimental', {}).get('collision_detection', {})
        if not collision_config:
            collision_config = self.config.get('collision_detection', {})

        enabled = collision_config.get('enabled', False)
        position_threshold = collision_config.get('position_threshold', 0.005)
        stagnation_duration = collision_config.get('stagnation_duration', 2.0)
        sample_interval = collision_config.get('sample_interval', 0.2)
        min_samples = collision_config.get('min_samples', 3)
        debug = collision_config.get('debug', False)

        return CollisionDetector(
            enabled=enabled,
            position_threshold=position_threshold,
            stagnation_duration=stagnation_duration,
            sample_interval=sample_interval,
            min_samples=min_samples,
            debug=debug
        )

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
