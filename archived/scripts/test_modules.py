#!/usr/bin/env python3
"""Quick test for individual modules of the multi-view VLM system."""

import sys
import numpy as np


def test_camera_transforms():
    """Test camera coordinate transformations."""
    print("\n" + "="*60)
    print("Testing Camera Transforms")
    print("="*60)

    try:
        from bridge.camera_transforms import CameraTransforms

        transforms = CameraTransforms()

        # Test D455 transformation
        if transforms.is_d455_calibrated():
            print("✓ D455 calibration loaded")

            # Test point transformation
            point_camera = np.array([0.5, 0.0, 0.8])
            point_base = transforms.transform_d455_to_base(point_camera)

            if point_base is not None:
                print(f"✓ D455 transformation works")
                print(f"  Camera: {point_camera}")
                print(f"  Base: {point_base}")
            else:
                print("✗ D455 transformation failed")
                return False
        else:
            print("⚠ D455 calibration not loaded")

        # Test head camera transformation
        point_camera = np.array([0.0, 0.0, 0.5])
        point_base = transforms.transform_head_to_base(point_camera)
        print(f"✓ Head camera transformation works")
        print(f"  Camera: {point_camera}")
        print(f"  Base: {point_base}")

        return True

    except Exception as e:
        print(f"✗ Camera transforms test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_image_processor():
    """Test image processing."""
    print("\n" + "="*60)
    print("Testing Image Processor")
    print("="*60)

    try:
        from bridge.image_processor import ImageProcessor
        import cv2

        processor = ImageProcessor()

        # Create test images
        test_rgb = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        test_depth = np.random.randint(500, 1500, (480, 640), dtype=np.uint16)

        # Test head camera processing
        processed_head, metadata = processor.process_head_camera_image(test_rgb)
        if processed_head is not None:
            print(f"✓ Head camera processing works")
            print(f"  Input: {test_rgb.shape}")
            print(f"  Output: {processed_head.shape}")
        else:
            print("✗ Head camera processing failed")
            return False

        # Test wrist camera processing
        processed_wrist, metadata = processor.process_wrist_camera_image(test_rgb)
        if processed_wrist is not None:
            print(f"✓ Wrist camera processing works")
            print(f"  Input: {test_rgb.shape}")
            print(f"  Output: {processed_wrist.shape}")
        else:
            print("✗ Wrist camera processing failed")
            return False

        # Test D455 processing
        processed_rgb, processed_depth, metadata = processor.process_d455_image(
            test_rgb, test_depth
        )
        if processed_rgb is not None and processed_depth is not None:
            print(f"✓ D455 processing works")
            print(f"  RGB: {processed_rgb.shape}")
            print(f"  Depth: {processed_depth.shape}")
        else:
            print("✗ D455 processing failed")
            return False

        # Test JPEG encoding
        jpeg_bytes = processor.encode_image_to_jpeg(processed_rgb)
        print(f"✓ JPEG encoding works ({len(jpeg_bytes)} bytes)")

        return True

    except Exception as e:
        print(f"✗ Image processor test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_vlm_prompts():
    """Test VLM prompt generation."""
    print("\n" + "="*60)
    print("Testing VLM Prompts")
    print("="*60)

    try:
        from bridge.vlm_prompts import VLMPrompts

        prompts = VLMPrompts()

        # Test Phase 1 D455 prompt
        prompt = prompts.get_phase1_d455_prompt("red cup")
        if len(prompt) > 100:
            print(f"✓ Phase 1 D455 prompt generated ({len(prompt)} chars)")
        else:
            print("✗ Phase 1 D455 prompt too short")
            return False

        # Test Phase 1 head camera prompt
        prompt = prompts.get_phase1_head_camera_prompt("red cup")
        if len(prompt) > 100:
            print(f"✓ Phase 1 head camera prompt generated ({len(prompt)} chars)")
        else:
            print("✗ Phase 1 head camera prompt too short")
            return False

        # Test Phase 2 wrist prompt
        prompt = prompts.get_phase2_wrist_camera_prompt("red cup", [0.6, 0.0, 0.05])
        if len(prompt) > 100:
            print(f"✓ Phase 2 wrist prompt generated ({len(prompt)} chars)")
        else:
            print("✗ Phase 2 wrist prompt too short")
            return False

        # Test fusion prompt
        d455_result = {
            'position': [0.6, 0.0, 0.05],
            'confidence': 85,
            'description': 'Red cup in center'
        }
        prompt = prompts.get_multi_view_fusion_prompt("red cup", d455_result, None, None)
        if len(prompt) > 100:
            print(f"✓ Fusion prompt generated ({len(prompt)} chars)")
        else:
            print("✗ Fusion prompt too short")
            return False

        return True

    except Exception as e:
        print(f"✗ VLM prompts test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_integration():
    """Test that all modules can be imported together."""
    print("\n" + "="*60)
    print("Testing Module Integration")
    print("="*60)

    try:
        from bridge.camera_transforms import CameraTransforms
        from bridge.image_processor import ImageProcessor
        from bridge.vlm_prompts import VLMPrompts
        from bridge.multi_view_vlm import MultiViewVLMCoordinator

        print("✓ All modules can be imported")
        print("✓ No import conflicts detected")

        return True

    except Exception as e:
        print(f"✗ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("="*60)
    print("Multi-View VLM Module Tests")
    print("="*60)

    results = []

    # Run tests
    results.append(("Camera Transforms", test_camera_transforms()))
    results.append(("Image Processor", test_image_processor()))
    results.append(("VLM Prompts", test_vlm_prompts()))
    results.append(("Integration", test_integration()))

    # Summary
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)

    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {name}")

    all_passed = all(result[1] for result in results)

    print("\n" + "="*60)
    if all_passed:
        print("✓ All tests passed!")
        print("="*60)
        return 0
    else:
        print("✗ Some tests failed")
        print("="*60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
