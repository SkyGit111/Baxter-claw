"""RealSense D455 depth camera driver."""

import numpy as np
import pyrealsense2 as rs
from typing import Tuple, Optional, Dict
import cv2


class RealSenseDriver:
    """Driver for Intel RealSense D455 depth camera.

    Provides RGB-D image capture and 3D coordinate conversion.
    """

    def __init__(self, width: int = 640, height: int = 480, fps: int = 30):
        """Initialize RealSense D455.

        Args:
            width: Image width in pixels
            height: Image height in pixels
            fps: Frames per second
        """
        self.width = width
        self.height = height
        self.fps = fps

        # Initialize pipeline
        self.pipeline = rs.pipeline()
        self.config = rs.config()

        # Configure streams
        self.config.enable_stream(rs.stream.depth, width, height, rs.format.z16, fps)
        self.config.enable_stream(rs.stream.color, width, height, rs.format.bgr8, fps)

        # Start pipeline
        print(f"[RealSense] Starting D455 ({width}x{height} @ {fps}fps)...")
        self.profile = self.pipeline.start(self.config)

        # Get camera intrinsics
        self.depth_intrinsics = self.profile.get_stream(rs.stream.depth).as_video_stream_profile().get_intrinsics()
        self.color_intrinsics = self.profile.get_stream(rs.stream.color).as_video_stream_profile().get_intrinsics()

        # Align depth to color
        self.align = rs.align(rs.stream.color)

        print(f"[RealSense] D455 initialized successfully")
        print(f"  Depth intrinsics: fx={self.depth_intrinsics.fx:.1f}, fy={self.depth_intrinsics.fy:.1f}")
        print(f"  Color intrinsics: fx={self.color_intrinsics.fx:.1f}, fy={self.color_intrinsics.fy:.1f}")

    def capture_rgbd(self) -> Tuple[np.ndarray, np.ndarray]:
        """Capture aligned RGB and depth images.

        Returns:
            Tuple of (rgb_image, depth_image)
            - rgb_image: numpy array (H, W, 3) uint8
            - depth_image: numpy array (H, W) uint16, values in millimeters
        """
        # Wait for frames
        frames = self.pipeline.wait_for_frames()

        # Align depth to color
        aligned_frames = self.align.process(frames)

        # Get aligned frames
        depth_frame = aligned_frames.get_depth_frame()
        color_frame = aligned_frames.get_color_frame()

        if not depth_frame or not color_frame:
            raise RuntimeError("Failed to capture frames")

        # Convert to numpy arrays
        depth_image = np.asanyarray(depth_frame.get_data())
        color_image = np.asanyarray(color_frame.get_data())

        return color_image, depth_image

    def deproject_pixel_to_point(self, x: int, y: int, depth: float) -> Tuple[float, float, float]:
        """Convert 2D pixel + depth to 3D point in camera coordinates.

        Args:
            x: Pixel x coordinate
            y: Pixel y coordinate
            depth: Depth value in meters

        Returns:
            Tuple of (x, y, z) in meters in camera coordinate frame
        """
        # Use color intrinsics (since depth is aligned to color)
        point = rs.rs2_deproject_pixel_to_point(
            self.color_intrinsics,
            [x, y],
            depth
        )
        return tuple(point)

    def get_depth_at_pixel(self, depth_image: np.ndarray, x: int, y: int, window_size: int = 5) -> Optional[float]:
        """Get depth value at pixel with median filtering.

        Args:
            depth_image: Depth image array
            x: Pixel x coordinate
            y: Pixel y coordinate
            window_size: Window size for median filter (reduces noise)

        Returns:
            Depth in meters, or None if invalid
        """
        h, w = depth_image.shape

        # Ensure pixel is within bounds
        if x < 0 or x >= w or y < 0 or y >= h:
            return None

        # Extract window around pixel
        half_window = window_size // 2
        y_min = max(0, y - half_window)
        y_max = min(h, y + half_window + 1)
        x_min = max(0, x - half_window)
        x_max = min(w, x + half_window + 1)

        window = depth_image[y_min:y_max, x_min:x_max]

        # Filter out zero values (invalid depth)
        valid_depths = window[window > 0]

        if len(valid_depths) == 0:
            return None

        # Return median depth in meters
        median_depth_mm = np.median(valid_depths)
        return median_depth_mm / 1000.0  # Convert mm to meters

    def get_3d_point_from_pixel(
        self,
        depth_image: np.ndarray,
        x: int,
        y: int,
        window_size: int = 5
    ) -> Optional[Tuple[float, float, float]]:
        """Get 3D point from pixel coordinates.

        Args:
            depth_image: Depth image array
            x: Pixel x coordinate
            y: Pixel y coordinate
            window_size: Window size for median filter

        Returns:
            Tuple of (x, y, z) in meters, or None if invalid
        """
        depth = self.get_depth_at_pixel(depth_image, x, y, window_size)

        if depth is None or depth <= 0:
            return None

        return self.deproject_pixel_to_point(x, y, depth)

    def capture_and_save_debug(self, filename_prefix: str = "debug"):
        """Capture and save RGB and depth images for debugging.

        Args:
            filename_prefix: Prefix for saved files
        """
        rgb, depth = self.capture_rgbd()

        # Save RGB
        cv2.imwrite(f"{filename_prefix}_rgb.jpg", rgb)

        # Save depth as colormap for visualization
        depth_colormap = cv2.applyColorMap(
            cv2.convertScaleAbs(depth, alpha=0.03),
            cv2.COLORMAP_JET
        )
        cv2.imwrite(f"{filename_prefix}_depth.jpg", depth_colormap)

        print(f"[RealSense] Saved debug images: {filename_prefix}_*.jpg")

    def stop(self):
        """Stop the pipeline and release resources."""
        self.pipeline.stop()
        print("[RealSense] Pipeline stopped")

    def __del__(self):
        """Cleanup on deletion."""
        try:
            self.pipeline.stop()
        except:
            pass


# Test code
if __name__ == "__main__":
    print("Testing RealSense D455...")

    # Initialize driver
    driver = RealSenseDriver()

    # Capture a frame
    print("\nCapturing frame...")
    rgb, depth = driver.capture_rgbd()
    print(f"  RGB shape: {rgb.shape}")
    print(f"  Depth shape: {depth.shape}")
    print(f"  Depth range: {depth.min()} - {depth.max()} mm")

    # Test 3D point conversion
    print("\nTesting 3D point conversion at image center...")
    center_x = rgb.shape[1] // 2
    center_y = rgb.shape[0] // 2
    point_3d = driver.get_3d_point_from_pixel(depth, center_x, center_y)

    if point_3d:
        print(f"  Pixel ({center_x}, {center_y}) -> 3D point: ({point_3d[0]:.3f}, {point_3d[1]:.3f}, {point_3d[2]:.3f}) m")
    else:
        print(f"  No valid depth at center pixel")

    # Save debug images
    print("\nSaving debug images...")
    driver.capture_and_save_debug("realsense_test")

    # Cleanup
    driver.stop()
    print("\n✓ RealSense test completed successfully")