# Grasp Verification Feature

## Overview

This experimental feature adds post-grasp verification using the wrist camera and VLM. After a pick action, the system captures an image from the wrist camera and asks the VLM to verify if the gripper is holding the object. If verification fails, the system automatically retries the pick operation.

## Features

- ✅ **Optional**: Can be enabled/disabled via command-line flag
- ✅ **Isolated**: Failures don't break existing functionality
- ✅ **Automatic Retry**: Retries pick operation if grasp verification fails
- ✅ **Configurable**: Adjustable retry attempts
- ✅ **Debug Mode**: Saves wrist camera images for analysis

## Architecture

```
pick_by_name()
    ↓
Execute pick primitive
    ↓
[If verification enabled]
    ↓
Capture wrist camera image
    ↓
Ask VLM: "Is gripper holding object?"
    ↓
    ├─ YES → Success
    └─ NO → Retry pick (up to max_retries)
```

## Usage

### Enable Verification

Start the bridge server with grasp verification enabled:

```bash
python start_server.py --enable-grasp-verification
```

With custom retry count:

```bash
python start_server.py --enable-grasp-verification --grasp-verify-retries 3
```

### Disable Verification (Default)

Simply start the server normally:

```bash
python start_server.py
```

## Configuration Options

| Option | Default | Description |
|--------|---------|-------------|
| `--enable-grasp-verification` | False | Enable post-grasp verification |
| `--grasp-verify-retries` | 2 | Maximum retry attempts |

## How It Works

### 1. Normal Pick Operation

When verification is **disabled** (default):

```python
result = await pick_by_name(arm='right', object_name='blue cube')
# Returns immediately after pick execution
```

### 2. Pick with Verification

When verification is **enabled**:

```python
result = await pick_by_name(arm='right', object_name='blue cube')
# After pick:
# 1. Captures wrist camera image
# 2. Asks VLM to verify grasp
# 3. If failed, retries pick (up to max_retries)
# 4. Returns final result with verification info
```

### 3. Result Format

With verification enabled, the result includes additional fields:

```python
{
    'success': True,
    'message': 'Pick successful',
    'grasp_verified': True,  # NEW: Verification result
    'verification_attempts': 1,  # NEW: Number of attempts
    'verification_details': {  # NEW: VLM response
        'success': True,
        'confidence': 0.95,
        'reasoning': 'Object clearly visible between gripper fingers'
    }
}
```

## VLM Prompt

The system asks the VLM:

```
Look at this image from a robot gripper's wrist camera.

The robot just attempted to pick up: {object_name}

Your task: Determine if the gripper is successfully holding the object.

Look for:
1. Is the object visible between the gripper fingers?
2. Are the gripper fingers closed around something?
3. Does the object appear to be securely held?

Answer in JSON format:
{
    "holding_object": true/false,
    "confidence": 0.0-1.0,
    "reasoning": "Brief explanation"
}
```

## Failure Handling

### Verification Failure

If verification fails after all retries:

```python
{
    'success': False,
    'message': 'Pick executed but grasp verification failed after 2 attempts. Reason: No object visible in gripper',
    'grasp_verified': False,
    'verification_attempts': 2
}
```

### Verification Error

If verification encounters an error (e.g., camera failure):

```python
{
    'success': True,  # Pick still succeeded
    'message': 'Pick successful',
    'grasp_verified': None,  # Verification couldn't run
    'verification_error': 'Camera capture failed'
}
```

**Important**: Verification errors don't fail the pick operation. The system assumes success and logs the error.

## Debug Mode

Debug mode is automatically enabled when verification is active. It saves wrist camera images:

```
grasp_verify_right_20260422_143052.jpg
grasp_verify_left_20260422_143105.jpg
```

These images help diagnose verification issues.

## Performance Impact

- **Additional Time**: ~2-3 seconds per pick (camera capture + VLM query)
- **Retry Time**: ~10-15 seconds per retry (open gripper + re-pick + verify)
- **Total Time**: 
  - Success on first attempt: +2-3s
  - Success on second attempt: +12-18s
  - Failure after 2 retries: +24-36s

## Limitations

1. **VLM Accuracy**: Depends on VLM's ability to recognize objects in wrist camera view
2. **Lighting**: Poor lighting may affect verification accuracy
3. **Object Size**: Very small objects may be hard to see in wrist camera
4. **Occlusion**: Gripper fingers may occlude the object

## Troubleshooting

### Verification Always Fails

**Possible causes**:
- Wrist camera not working
- Poor lighting
- VLM not configured correctly
- Object too small to see

**Solution**:
1. Check debug images: `grasp_verify_*.jpg`
2. Verify wrist camera works: `rostopic echo /cameras/{arm}_hand_camera/image`
3. Test VLM separately

### Verification Always Succeeds (False Positives)

**Possible causes**:
- VLM too lenient
- Prompt not specific enough

**Solution**:
1. Review debug images
2. Adjust VLM prompt in `grasp_verifier.py`

### Performance Too Slow

**Solution**:
- Reduce `--grasp-verify-retries` to 1
- Or disable verification for time-critical tasks

## Example Usage

### Test Script

```python
import asyncio
from bridge.arm_manager import ArmManager

async def test_verification():
    # Initialize with verification enabled
    manager = ArmManager(
        config_path='config/baxter.yaml',
        enable_grasp_verification=True,
        grasp_verify_retries=2
    )
    
    await manager.connect()
    await manager.enable()
    
    # Test pick with verification
    result = await manager.primitives.pick_by_name(
        arm='right',
        object_name='blue cube',
        use_d455=True
    )
    
    print(f"Success: {result['success']}")
    print(f"Verified: {result.get('grasp_verified')}")
    print(f"Attempts: {result.get('verification_attempts')}")

asyncio.run(test_verification())
```

### Web Interface

The web interface automatically uses verification if the server was started with `--enable-grasp-verification`.

## Future Improvements

- [ ] Configurable VLM prompt
- [ ] Confidence threshold tuning
- [ ] Support for bimanual grasps
- [ ] Verification history logging
- [ ] Real-time verification feedback in web UI

## Safety Notes

- Verification is **experimental** and may have false positives/negatives
- Always supervise the robot during operation
- Verification failures don't guarantee the object wasn't picked (may be false negative)
- Use in controlled environments first

## Disabling Verification

To completely disable verification:

1. Start server without `--enable-grasp-verification` flag
2. Or set `enable_grasp_verification=False` in code

The feature is fully isolated and won't affect normal operation when disabled.
