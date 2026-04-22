#!/usr/bin/env python
"""Test grasp verification feature.

This script tests the grasp verification module in isolation.
"""

import asyncio
import sys
import os

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bridge.grasp_verifier import GraspVerifier
from bridge.drivers.mock_driver import MockDriver
from bridge.vlm_client import VLMClient


async def test_verification():
    """Test grasp verification with mock components."""

    print("="*60)
    print("Grasp Verification Test")
    print("="*60)
    print()

    # Create mock driver
    driver = MockDriver()
    driver.connect()

    # Create VLM client (requires API key)
    vlm_api_key = os.getenv('QWEN_API_KEY')
    if not vlm_api_key:
        print("✗ Error: QWEN_API_KEY not set")
        print("  Set it with: export QWEN_API_KEY=your_key")
        return

    vlm_client = VLMClient(
        provider='qwen',
        api_key=vlm_api_key
    )

    # Test 1: Verifier initialization
    print("Test 1: Initialize verifier (enabled)")
    verifier = GraspVerifier(
        driver=driver,
        vlm_client=vlm_client,
        enabled=True,
        max_retries=2,
        debug=True
    )
    print("✓ Verifier initialized\n")

    # Test 2: Verifier disabled
    print("Test 2: Initialize verifier (disabled)")
    verifier_disabled = GraspVerifier(
        driver=driver,
        vlm_client=vlm_client,
        enabled=False
    )
    result = await verifier_disabled.verify_grasp('right', 'test object')
    print(f"✓ Disabled verifier returns: {result}\n")

    # Test 3: Build prompt
    print("Test 3: Build verification prompt")
    prompt = verifier._build_verification_prompt('blue cube')
    print(f"Prompt length: {len(prompt)} chars")
    print(f"First 100 chars: {prompt[:100]}...")
    print("✓ Prompt built\n")

    # Test 4: Parse VLM response
    print("Test 4: Parse VLM response")
    test_response = '''```json
{
    "holding_object": true,
    "confidence": 0.95,
    "reasoning": "Object clearly visible between gripper fingers"
}
```'''
    parsed = verifier._parse_vlm_response(test_response)
    print(f"Parsed: {parsed}")
    assert parsed['success'] == True
    assert parsed['confidence'] == 0.95
    print("✓ Response parsed correctly\n")

    # Test 5: Parse fallback (keyword detection)
    print("Test 5: Parse fallback response")
    fallback_response = "Yes, the gripper is holding the object successfully."
    parsed_fallback = verifier._parse_vlm_response(fallback_response)
    print(f"Parsed: {parsed_fallback}")
    assert parsed_fallback['success'] == True
    print("✓ Fallback parsing works\n")

    print("="*60)
    print("All tests passed!")
    print("="*60)
    print()
    print("Note: This test uses mock components.")
    print("To test with real robot:")
    print("  1. Start bridge server with --enable-grasp-verification")
    print("  2. Use web interface or API to test pick operations")


if __name__ == "__main__":
    asyncio.run(test_verification())
