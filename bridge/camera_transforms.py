"""Camera coordinate transformations using hand-eye calibration data.

This module handles transformations between different coordinate frames:
- Camera frame (D455, head camera, wrist camera)
- Robot base frame
- End-effector frame
"""

import numpy as np
import yaml
from typing import Tuple, Optional, Dict
from scipy.spatial.transform import Rotation


class CameraTransforms:
    """Manages coordinate transformations for all cameras."""

    def __init__(self, calibration_file: Optional[str] = None):
        """Initialize camera transforms.

        Args:
            calibration_file: Path to hand-eye calibration YAML file
        """
        # D455 hand-eye calibration (camera to base)
        self.d455_to_base = None

        if calibration_file:
            self._load_d455_calibration(calibration_file)
        else:
            # Try default location
            default_calib = "/home/cothink/.ros/easy_handeye/baxter_d455_handeye_calibration_eye_on_base.yaml"
            try:
                self._load_d455_calibration(default_calib)
            except Exception as e:
                print(f"Warning: Could not load D455 calibration: {e}")
                print("D455 coordinates will not be transformed to base frame")

        # Head camera transform (fixed, measured manually or from URDF)
        # Head camera is approximately at [0.05, 0, 0.4] relative to base
        # with a downward tilt of about 45 degrees
        self._init_head_camera_transform()

    def _load_d455_calibration(self, filepath: str):
        """Load D455 hand-eye calibration from YAML file.

        Args:
            filepath: Path to calibration YAML file
        """
        try:
            with open(filepath, 'r') as f:
                calib_data = yaml.safe_load(f)

            # Extract transformation
            trans = calib_data['transformation']

            # Translation vector
            translation = np.array([trans['x'], trans['y'], trans['z']])

            # Rotation quaternion (qw, qx, qy, qz)
            quaternion = np.array([trans['qx'], trans['qy'], trans['qz'], trans['qw']])

            # Convert quaternion to rotation matrix
            rotation = Rotation.from_quat(quaternion)
            rotation_matrix = rotation.as_matrix()

            # Build 4x4 transformation matrix
            self.d455_to_base = np.eye(4)
            self.d455_to_base[:3, :3] = rotation_matrix
            self.d455_to_base[:3, 3] = translation

            print(f"[CameraTransforms] Loaded D455 calibration from {filepath}")
            print(f"  Translation: {translation}")
            print(f"  Rotation (euler): {rotation.as_euler('xyz', degrees=True)} deg")

        except Exception as e:
            raise RuntimeError(f"Failed to load D455 calibration: {e}")

    def _init_head_camera_transform(self):
        """Initialize head camera transformation.

        Head camera is fixed on the robot head. The transformation is either:
        1. Measured manually
        2. Extracted from robot URDF
        3. Obtained from TF tree

        For now, we use approximate values based on Baxter's geometry.
        """
        # Approximate head camera position relative to base
        # These values should be refined through measurement or URDF
        translation = np.array([0.05, 0.0, 0.4])  # 5cm forward, 40cm up

        # Head camera points downward at approximately 45 degrees
        # Rotation: pitch down 45 degrees
        rotation = Rotation.from_euler('xyz', [0, -45, 0], degrees=True)
        rotation_matrix = rotation.as_matrix()

        # Build transformation matrix
        self.head_to_base = np.eye(4)
        self.head_to_base[:3, :3] = rotation_matrix
        self.head_to_base[:3, 3] = translation

        print(f"[CameraTransforms] Initialized head camera transform (approximate)")
        print(f"  Translation: {translation}")
        print(f"  Rotation: 45° pitch down")

    def transform_d455_to_base(self, point_camera: np.ndarray) -> Optional[np.ndarray]:
        """Transform point from D455 camera frame to robot base frame.

        Args:
            point_camera: 3D point in camera frame [x, y, z]

        Returns:
            3D point in base frame [x, y, z], or None if calibration not loaded
        """
        if self.d455_to_base is None:
            print("Warning: D455 calibration not loaded, cannot transform")
            return None

        # Convert to homogeneous coordinates
        point_homo = np.append(point_camera, 1.0)

        # Apply transformation
        point_base_homo = self.d455_to_base @ point_homo

        # Convert back to 3D
        return point_base_homo[:3]

    def transform_head_to_base(self, point_camera: np.ndarray) -> np.ndarray:
        """Transform point from head camera frame to robot base frame.

        Args:
            point_camera: 3D point in camera frame [x, y, z]

        Returns:
            3D point in base frame [x, y, z]
        """
        # Convert to homogeneous coordinates
        point_homo = np.append(point_camera, 1.0)

        # Apply transformation
        point_base_homo = self.head_to_base @ point_homo

        # Convert back to 3D
        return point_base_homo[:3]

    def transform_wrist_to_base(
        self,
        point_camera: np.ndarray,
        wrist_pose: np.ndarray
    ) -> np.ndarray:
        """Transform point from wrist camera frame to robot base frame.

        Args:
            point_camera: 3D point in camera frame [x, y, z]
            wrist_pose: Current wrist pose [x, y, z, roll, pitch, yaw]

        Returns:
            3D point in base frame [x, y, z]
        """
        # Build wrist to base transformation from current pose
        translation = wrist_pose[:3]
        rotation = Rotation.from_euler('xyz', wrist_pose[3:6])
        rotation_matrix = rotation.as_matrix()

        wrist_to_base = np.eye(4)
        wrist_to_base[:3, :3] = rotation_matrix
        wrist_to_base[:3, 3] = translation

        # Camera offset from wrist (camera is slightly offset from gripper center)
        # This should be measured or obtained from URDF
        camera_offset = np.array([0.0, 0.0, 0.05])  # 5cm forward from wrist

        # Build camera to wrist transformation
        camera_to_wrist = np.eye(4)
        camera_to_wrist[:3, 3] = camera_offset

        # Combine transformations: camera -> wrist -> base
        camera_to_base = wrist_to_base @ camera_to_wrist

        # Convert to homogeneous coordinates
        point_homo = np.append(point_camera, 1.0)

        # Apply transformation
        point_base_homo = camera_to_base @ point_homo

        # Convert back to 3D
        return point_base_homo[:3]

    def get_d455_transform_matrix(self) -> Optional[np.ndarray]:
        """Get D455 to base transformation matrix.

        Returns:
            4x4 transformation matrix, or None if not loaded
        """
        return self.d455_to_base

    def get_head_transform_matrix(self) -> np.ndarray:
        """Get head camera to base transformation matrix.

        Returns:
            4x4 transformation matrix
        """
        return self.head_to_base

    def is_d455_calibrated(self) -> bool:
        """Check if D455 calibration is loaded.

        Returns:
            True if calibration is loaded
        """
        return self.d455_to_base is not None


# Test code
if __name__ == "__main__":
    print("Testing CameraTransforms...")

    # Initialize transforms
    transforms = CameraTransforms()

    # Test D455 transformation
    if transforms.is_d455_calibrated():
        print("\n[Test] D455 transformation:")
        point_camera = np.array([0.5, 0.0, 0.8])  # 50cm forward, 80cm away
        point_base = transforms.transform_d455_to_base(point_camera)
        print(f"  Camera frame: {point_camera}")
        print(f"  Base frame: {point_base}")
    else:
        print("\n[Test] D455 not calibrated")

    # Test head camera transformation
    print("\n[Test] Head camera transformation:")
    point_camera = np.array([0.0, 0.0, 0.5])  # 50cm in front of camera
    point_base = transforms.transform_head_to_base(point_camera)
    print(f"  Camera frame: {point_camera}")
    print(f"  Base frame: {point_base}")

    # Test wrist camera transformation
    print("\n[Test] Wrist camera transformation:")
    point_camera = np.array([0.0, 0.0, 0.1])  # 10cm in front of camera
    wrist_pose = np.array([0.6, 0.0, 0.2, np.pi, 0.0, 0.0])  # Wrist pointing down
    point_base = transforms.transform_wrist_to_base(point_camera, wrist_pose)
    print(f"  Camera frame: {point_camera}")
    print(f"  Wrist pose: {wrist_pose[:3]}")
    print(f"  Base frame: {point_base}")

    print("\n✓ CameraTransforms test completed")
