"""Abstract base class for robot arm drivers."""

from abc import ABC, abstractmethod
from typing import Dict, List, Tuple


class ArmDriver(ABC):
    """Abstract interface for robot arm control.

    This interface allows swapping between real hardware (BaxterDriver)
    and mock implementations (MockDriver) for testing.
    """

    @abstractmethod
    def connect(self) -> bool:
        """Connect to the robot.

        Returns:
            True if connection successful, False otherwise.
        """
        pass

    @abstractmethod
    def disconnect(self) -> bool:
        """Disconnect from the robot.

        Returns:
            True if disconnection successful, False otherwise.
        """
        pass

    @abstractmethod
    def enable(self) -> bool:
        """Enable the robot motors.

        Returns:
            True if enable successful, False otherwise.
        """
        pass

    @abstractmethod
    def disable(self) -> bool:
        """Disable the robot motors.

        Returns:
            True if disable successful, False otherwise.
        """
        pass

    @abstractmethod
    def is_enabled(self) -> bool:
        """Check if robot is enabled.

        Returns:
            True if robot is enabled, False otherwise.
        """
        pass

    @abstractmethod
    def move_to_joint_positions(
        self, arm: str, positions: Dict[str, float], speed: float = 0.3, timeout: float = 15.0
    ) -> bool:
        """Move arm to specified joint positions.

        Args:
            arm: 'left' or 'right'
            positions: Dict mapping joint names to angles in radians
            speed: Motion speed ratio (0-1)
            timeout: Maximum time to wait for motion completion

        Returns:
            True if motion completed successfully, False otherwise.
        """
        pass

    @abstractmethod
    def move_to_pose(
        self, arm: str, pose: List[float], speed: float = 0.3, timeout: float = 15.0
    ) -> bool:
        """Move arm end-effector to specified Cartesian pose.

        Args:
            arm: 'left' or 'right'
            pose: [x, y, z, roll, pitch, yaw] in meters and radians
            speed: Motion speed ratio (0-1)
            timeout: Maximum time to wait for motion completion

        Returns:
            True if motion completed successfully, False otherwise.
        """
        pass

    @abstractmethod
    def get_joint_angles(self, arm: str) -> Dict[str, float]:
        """Get current joint angles.

        Args:
            arm: 'left' or 'right'

        Returns:
            Dict mapping joint names to current angles in radians.
        """
        pass

    @abstractmethod
    def get_endpoint_pose(self, arm: str) -> List[float]:
        """Get current end-effector pose.

        Args:
            arm: 'left' or 'right'

        Returns:
            [x, y, z, roll, pitch, yaw] in meters and radians.
        """
        pass

    @abstractmethod
    def gripper_command(self, arm: str, action: str, force: float = 30.0) -> bool:
        """Control gripper.

        Args:
            arm: 'left' or 'right'
            action: 'open', 'close', or 'calibrate'
            force: Grip force (0-100)

        Returns:
            True if command successful, False otherwise.
        """
        pass

    @abstractmethod
    def get_gripper_state(self, arm: str) -> Tuple[float, float]:
        """Get gripper state.

        Args:
            arm: 'left' or 'right'

        Returns:
            Tuple of (position, force) where position is 0-100 (0=closed, 100=open)
            and force is current grip force.
        """
        pass

    @abstractmethod
    def capture_image(self, camera: str) -> bytes:
        """Capture image from specified camera.

        Args:
            camera: Camera identifier (e.g., 'left_hand', 'right_hand', 'head')

        Returns:
            JPEG image data as bytes.
        """
        pass

    @abstractmethod
    def emergency_stop(self) -> bool:
        """Execute emergency stop.

        Returns:
            True if stop successful, False otherwise.
        """
        pass
