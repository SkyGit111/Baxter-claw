"""Image processing utilities for camera images.

Handles preprocessing of images from different cameras:
- Head camera: cropping, perspective correction
- Wrist camera: enhancement, noise reduction
- D455: depth filtering, colorization
"""

import cv2
import numpy as np
from typing import Tuple, Optional, Dict


class ImageProcessor:
    """Processes images from different cameras for VLM analysis."""

    def __init__(self):
        """Initialize image processor."""
        # Head camera parameters (measured from actual images)
        # Based on actual Baxter head camera view: table is at bottom, background at top
        self.head_camera_config = {
            'crop_top': 0.45,     # Crop top 45% (ceiling, lights, shelves)
            'crop_bottom': 0.0,   # Don't crop bottom (table workspace)
            'crop_left': 0.1,     # Crop left 10% (minimal side cropping)
            'crop_right': 0.1,    # Crop right 10% (minimal side cropping)
            'enhance_contrast': True,
            'perspective_correction': True,
        }

        # Wrist camera parameters
        self.wrist_camera_config = {
            'enhance_sharpness': True,
            'denoise': True,
            'auto_white_balance': True,
        }

        # D455 depth parameters
        self.depth_config = {
            'min_depth_mm': 300,    # 30cm minimum
            'max_depth_mm': 2000,   # 2m maximum
            'median_filter_size': 5,
        }

    def process_head_camera_image(self, image: np.ndarray) -> Tuple[np.ndarray, Dict]:
        """Process head camera image for VLM analysis.

        Steps:
        1. Crop to focus on workspace (remove sky, robot body, etc.)
        2. Enhance contrast
        3. Optional: perspective correction to top-down view

        Args:
            image: Raw BGR image from head camera

        Returns:
            Tuple of (processed_image, metadata)
        """
        if image is None or image.size == 0:
            return None, {}

        original_shape = image.shape
        processed = image.copy()

        # Step 1: Crop to workspace region
        h, w = processed.shape[:2]
        crop_top = int(h * self.head_camera_config['crop_top'])
        crop_bottom = int(h * (1 - self.head_camera_config['crop_bottom']))
        crop_left = int(w * self.head_camera_config['crop_left'])
        crop_right = int(w * (1 - self.head_camera_config['crop_right']))

        processed = processed[crop_top:crop_bottom, crop_left:crop_right]
        print(f"[ImageProcessor] Head camera cropped: {original_shape[:2]} -> {processed.shape[:2]}")

        # Step 2: Enhance contrast (CLAHE - Contrast Limited Adaptive Histogram Equalization)
        if self.head_camera_config['enhance_contrast']:
            lab = cv2.cvtColor(processed, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)

            # Apply CLAHE to L channel
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            l = clahe.apply(l)

            # Merge back
            lab = cv2.merge([l, a, b])
            processed = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
            print(f"[ImageProcessor] Contrast enhanced")

        # Step 3: Perspective correction (optional, experimental)
        if self.head_camera_config['perspective_correction']:
            processed = self._apply_perspective_correction(processed)

        # Metadata
        metadata = {
            'original_shape': original_shape,
            'processed_shape': processed.shape,
            'crop_region': (crop_top, crop_bottom, crop_left, crop_right),
            'enhanced': True,
        }

        return processed, metadata

    def _apply_perspective_correction(self, image: np.ndarray) -> np.ndarray:
        """Apply perspective correction to head camera image.

        Attempts to correct the tilted view to a more top-down perspective.
        This is experimental and may need tuning.

        Args:
            image: Cropped head camera image

        Returns:
            Perspective-corrected image
        """
        h, w = image.shape[:2]

        # Define source points (trapezoid due to perspective)
        # After cropping top 45%, the table trapezoid occupies most of the image
        # Top edge (far end of table): narrower, near top of cropped image
        # Bottom edge (near end of table): wider, at bottom of cropped image
        src_points = np.float32([
            [w * 0.25, h * 0.05],  # Top-left (far end, narrower)
            [w * 0.75, h * 0.05],  # Top-right (far end, narrower)
            [w * 0.0, h * 0.95],   # Bottom-left (near end, wider)
            [w * 1.0, h * 0.95],   # Bottom-right (near end, wider)
        ])

        # Define destination points (rectangle for top-down view)
        dst_points = np.float32([
            [0, 0],
            [w, 0],
            [0, h],
            [w, h],
        ])

        # Calculate perspective transformation matrix
        matrix = cv2.getPerspectiveTransform(src_points, dst_points)

        # Apply transformation
        corrected = cv2.warpPerspective(image, matrix, (w, h))

        print(f"[ImageProcessor] Perspective correction applied")
        return corrected

    def process_wrist_camera_image(self, image: np.ndarray) -> Tuple[np.ndarray, Dict]:
        """Process wrist camera image for VLM analysis.

        Steps:
        1. Denoise (wrist camera may have motion blur)
        2. Enhance sharpness
        3. Auto white balance

        Args:
            image: Raw BGR image from wrist camera

        Returns:
            Tuple of (processed_image, metadata)
        """
        if image is None or image.size == 0:
            return None, {}

        processed = image.copy()

        # Step 1: Denoise
        if self.wrist_camera_config['denoise']:
            processed = cv2.fastNlMeansDenoisingColored(
                processed,
                None,
                h=10,
                hColor=10,
                templateWindowSize=7,
                searchWindowSize=21
            )
            print(f"[ImageProcessor] Wrist image denoised")

        # Step 2: Enhance sharpness
        if self.wrist_camera_config['enhance_sharpness']:
            kernel = np.array([[-1, -1, -1],
                             [-1,  9, -1],
                             [-1, -1, -1]])
            processed = cv2.filter2D(processed, -1, kernel)
            print(f"[ImageProcessor] Sharpness enhanced")

        # Step 3: Auto white balance
        if self.wrist_camera_config['auto_white_balance']:
            processed = self._auto_white_balance(processed)

        metadata = {
            'original_shape': image.shape,
            'processed_shape': processed.shape,
            'denoised': True,
            'sharpened': True,
            'white_balanced': True,
        }

        return processed, metadata

    def _auto_white_balance(self, image: np.ndarray) -> np.ndarray:
        """Apply automatic white balance.

        Args:
            image: BGR image

        Returns:
            White-balanced image
        """
        result = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        avg_a = np.average(result[:, :, 1])
        avg_b = np.average(result[:, :, 2])
        result[:, :, 1] = result[:, :, 1] - ((avg_a - 128) * (result[:, :, 0] / 255.0) * 1.1)
        result[:, :, 2] = result[:, :, 2] - ((avg_b - 128) * (result[:, :, 0] / 255.0) * 1.1)
        result = cv2.cvtColor(result, cv2.COLOR_LAB2BGR)
        print(f"[ImageProcessor] White balance applied")
        return result

    def process_d455_image(
        self,
        rgb_image: np.ndarray,
        depth_image: Optional[np.ndarray] = None
    ) -> Tuple[np.ndarray, Optional[np.ndarray], Dict]:
        """Process D455 RGB-D image.

        Steps:
        1. Filter depth image (remove noise, outliers)
        2. Enhance RGB image
        3. Create depth visualization

        Args:
            rgb_image: RGB image from D455
            depth_image: Depth image from D455 (optional)

        Returns:
            Tuple of (processed_rgb, processed_depth, metadata)
        """
        if rgb_image is None or rgb_image.size == 0:
            return None, None, {}

        processed_rgb = rgb_image.copy()
        processed_depth = None

        # Process depth if available
        if depth_image is not None:
            processed_depth = self._filter_depth_image(depth_image)

        # Enhance RGB
        processed_rgb = self._enhance_rgb(processed_rgb)

        metadata = {
            'original_shape': rgb_image.shape,
            'has_depth': depth_image is not None,
            'depth_filtered': processed_depth is not None,
        }

        return processed_rgb, processed_depth, metadata

    def _filter_depth_image(self, depth_image: np.ndarray) -> np.ndarray:
        """Filter depth image to remove noise and outliers.

        Args:
            depth_image: Raw depth image (uint16, millimeters)

        Returns:
            Filtered depth image
        """
        filtered = depth_image.copy()

        # Step 1: Remove values outside valid range
        min_depth = self.depth_config['min_depth_mm']
        max_depth = self.depth_config['max_depth_mm']
        filtered[filtered < min_depth] = 0
        filtered[filtered > max_depth] = 0

        # Step 2: Median filter to remove noise
        kernel_size = self.depth_config['median_filter_size']
        filtered = cv2.medianBlur(filtered, kernel_size)

        # Step 3: Fill small holes (optional)
        # This helps with objects that have reflective surfaces
        mask = (filtered == 0).astype(np.uint8)
        kernel = np.ones((3, 3), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        filtered[mask == 1] = 0

        print(f"[ImageProcessor] Depth image filtered (range: {min_depth}-{max_depth}mm)")
        return filtered

    def _enhance_rgb(self, image: np.ndarray) -> np.ndarray:
        """Enhance RGB image from D455.

        Args:
            image: RGB image

        Returns:
            Enhanced image
        """
        # Convert to LAB color space
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)

        # Apply CLAHE to L channel
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        l = clahe.apply(l)

        # Merge back
        lab = cv2.merge([l, a, b])
        enhanced = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

        return enhanced

    def create_depth_visualization(self, depth_image: np.ndarray) -> np.ndarray:
        """Create colorized visualization of depth image.

        Args:
            depth_image: Depth image (uint16, millimeters)

        Returns:
            Colorized depth image (BGR)
        """
        # Normalize to 0-255
        depth_normalized = cv2.normalize(
            depth_image,
            None,
            0,
            255,
            cv2.NORM_MINMAX,
            dtype=cv2.CV_8U
        )

        # Apply colormap
        depth_colormap = cv2.applyColorMap(depth_normalized, cv2.COLORMAP_JET)

        # Mask out invalid depths (show as black)
        mask = depth_image == 0
        depth_colormap[mask] = [0, 0, 0]

        return depth_colormap

    def encode_image_to_jpeg(
        self,
        image: np.ndarray,
        quality: int = 90
    ) -> bytes:
        """Encode image to JPEG bytes.

        Args:
            image: BGR image
            quality: JPEG quality (0-100)

        Returns:
            JPEG bytes
        """
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
        success, jpeg_buffer = cv2.imencode('.jpg', image, encode_param)

        if not success:
            raise RuntimeError("Failed to encode image as JPEG")

        return jpeg_buffer.tobytes()

    def save_debug_images(
        self,
        prefix: str,
        raw_image: Optional[np.ndarray] = None,
        processed_image: Optional[np.ndarray] = None,
        depth_image: Optional[np.ndarray] = None
    ):
        """Save debug images for inspection.

        Args:
            prefix: Filename prefix
            raw_image: Raw image
            processed_image: Processed image
            depth_image: Depth image
        """
        if raw_image is not None:
            cv2.imwrite(f"{prefix}_raw.jpg", raw_image)
            print(f"[ImageProcessor] Saved {prefix}_raw.jpg")

        if processed_image is not None:
            cv2.imwrite(f"{prefix}_processed.jpg", processed_image)
            print(f"[ImageProcessor] Saved {prefix}_processed.jpg")

        if depth_image is not None:
            depth_viz = self.create_depth_visualization(depth_image)
            cv2.imwrite(f"{prefix}_depth.jpg", depth_viz)
            print(f"[ImageProcessor] Saved {prefix}_depth.jpg")


# Test code
if __name__ == "__main__":
    print("Testing ImageProcessor...")

    processor = ImageProcessor()

    # Create test images
    print("\n[Test] Creating test images...")
    test_image = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
    test_depth = np.random.randint(500, 1500, (480, 640), dtype=np.uint16)

    # Test head camera processing
    print("\n[Test] Processing head camera image...")
    processed_head, metadata = processor.process_head_camera_image(test_image)
    print(f"  Result shape: {processed_head.shape}")
    print(f"  Metadata: {metadata}")

    # Test wrist camera processing
    print("\n[Test] Processing wrist camera image...")
    processed_wrist, metadata = processor.process_wrist_camera_image(test_image)
    print(f"  Result shape: {processed_wrist.shape}")
    print(f"  Metadata: {metadata}")

    # Test D455 processing
    print("\n[Test] Processing D455 image...")
    processed_rgb, processed_depth, metadata = processor.process_d455_image(
        test_image, test_depth
    )
    print(f"  RGB shape: {processed_rgb.shape}")
    print(f"  Depth shape: {processed_depth.shape if processed_depth is not None else None}")
    print(f"  Metadata: {metadata}")

    # Test JPEG encoding
    print("\n[Test] Encoding to JPEG...")
    jpeg_bytes = processor.encode_image_to_jpeg(processed_rgb)
    print(f"  JPEG size: {len(jpeg_bytes)} bytes")

    print("\n✓ ImageProcessor test completed")
