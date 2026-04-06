# Baxter-Claw Safety Guidelines

## Overview

Safety is paramount when working with physical robots. This document outlines safety procedures, constraints, and best practices for Baxter-Claw.

## Hardware Safety

### Before Operation

1. **Clear Workspace**
   - Remove unnecessary objects from robot workspace
   - Ensure no people are within arm's reach
   - Check for obstacles that could cause collisions

2. **Emergency Stop Access**
   - Keep Baxter's emergency stop button accessible at all times
   - Know the location of all e-stop buttons
   - Test e-stop functionality before each session

3. **Visual Inspection**
   - Check for loose cables or damaged components
   - Verify grippers are properly attached
   - Ensure robot is securely mounted

### During Operation

1. **Maintain Safe Distance**
   - Stay outside robot's workspace during autonomous operation
   - Never reach into workspace while robot is moving
   - Use the emergency stop if intervention is needed

2. **Monitor Continuously**
   - Watch robot motion at all times
   - Be ready to press emergency stop
   - Listen for unusual sounds (grinding, clicking)

3. **Gradual Testing**
   - Test new motions at low speed first
   - Verify trajectories in simulation before real execution
   - Start with small movements, gradually increase range

### After Operation

1. **Disable Robot**
   - Always disable motors when done
   - Return arms to safe home position
   - Disconnect if leaving unattended

2. **Report Issues**
   - Document any unusual behavior
   - Report collisions or unexpected motions
   - Log safety incidents for review

## Software Safety

### Built-in Safety Features

#### 1. Workspace Limits

Default safe workspace (meters, relative to robot base):

```yaml
workspace:
  x: [0.3, 0.9]    # Forward reach
  y: [-0.7, 0.7]   # Lateral reach  
  z: [-0.2, 0.5]   # Height above table
```

**Rationale**:
- `x_min = 0.3`: Prevents collision with robot torso
- `x_max = 0.9`: Limits overextension
- `y`: Symmetric lateral limits
- `z_min = -0.2`: Allows table-level operations
- `z_max = 0.5`: Prevents reaching too high

**Customization**: Adjust in `config/baxter.yaml` based on your setup, but always err on the side of caution.

#### 2. Joint Limits

Baxter joint limits (radians) are enforced by `SafetyValidator`:

| Joint | Min (rad) | Max (rad) | Min (deg) | Max (deg) |
|-------|-----------|-----------|-----------|-----------|
| s0 | -1.701 | 1.701 | -97.5° | 97.5° |
| s1 | -2.147 | 1.047 | -123° | 60° |
| e0 | -3.054 | 3.054 | -175° | 175° |
| e1 | -0.050 | 2.618 | -2.9° | 150° |
| w0 | -3.059 | 3.059 | -175° | 175° |
| w1 | -1.571 | 2.094 | -90° | 120° |
| w2 | -3.059 | 3.059 | -175° | 175° |

These limits are slightly more conservative than Baxter's hardware limits to provide a safety margin.

#### 3. Speed Limits

Default maximum speed: **0.5** (50% of maximum)

**Rationale**: Slower speeds provide:
- More reaction time for emergency stop
- Reduced impact force in case of collision
- Better motion quality and accuracy

**Override**: Can be increased in config, but not recommended above 0.7 for autonomous operation.

#### 4. Motion Validation

Every motion is validated before execution:

```python
# Example validation flow
is_safe, msg = safety.check_workspace(arm, target_pose)
if not is_safe:
    return {"success": False, "message": msg}
```

Validation checks:
- Target within workspace bounds
- Joint angles within limits
- Speed within safe range
- No NaN or infinite values

### Safety Best Practices

#### 1. Always Enable Explicitly

```python
# Good
manager.enable()
manager.primitives.pick(...)

# Bad - will fail
manager.primitives.pick(...)  # Robot not enabled
```

#### 2. Use Mock Driver for Testing

```yaml
# config/baxter.yaml
driver:
  type: "mock"  # Test logic without hardware
```

Test your code flow with mock driver before running on real hardware.

#### 3. Start with Home Position

```python
# Always start from known safe position
manager.primitives.home('right')
# Then proceed with task
manager.primitives.pick(...)
```

#### 4. Validate Coordinates

```python
# Good - explicit coordinates
position = [0.6, 0.2, 0.1]
result = primitives.pick('right', position)

# Bad - unvalidated user input
position = user_input  # Could be anything!
result = primitives.pick('right', position)
```

Always validate user-provided coordinates against expected ranges.

#### 5. Handle Errors Gracefully

```python
result = primitives.pick('right', position)
if not result['success']:
    print(f"Pick failed: {result['message']}")
    # Return to safe state
    primitives.home('right')
    return
```

#### 6. Use Approach Heights

```python
# Good - safe approach from above
primitives.pick('right', [0.6, 0.2, 0.1], approach_height=0.1)

# Risky - direct approach
primitives.pick('right', [0.6, 0.2, 0.1], approach_height=0.0)
```

Approach heights prevent collisions with objects or table surface.

## LLM-Specific Safety

### Prompt Engineering for Safety

When configuring OpenClaw, include safety guidelines in system prompt:

```json
{
  "agent": {
    "system_prompt": "You are a robotics assistant. SAFETY RULES:
    1. Always confirm potentially dangerous operations with user
    2. Never move robot near workspace boundaries without explicit permission
    3. Start all sessions by enabling robot and moving to home position
    4. If user requests motion outside safe workspace, explain limits and suggest alternative
    5. Use approach_height parameter for all pick/place operations
    6. If any operation fails, return to home position before retrying"
  }
}
```

### Dangerous Patterns to Avoid

#### 1. Rapid Repeated Motions

```
# Dangerous - could cause wear or collision
User: "Move back and forth 100 times"
```

**Mitigation**: LLM should question unusual requests and suggest safer alternatives.

#### 2. Workspace Boundary Testing

```
# Dangerous - testing limits
User: "Move as far forward as possible"
```

**Mitigation**: LLM should refuse and explain safe workspace limits.

#### 3. Unvalidated Positions

```
# Dangerous - no validation
User: "Pick at x=5, y=10, z=-2"
```

**Mitigation**: Safety validator will reject, but LLM should also recognize unreasonable values.

#### 4. Simultaneous Conflicting Commands

```
# Dangerous - dual arm collision risk
User: "Move both arms to the center"
```

**Mitigation**: Currently only right arm supported. Future dual-arm implementation must include collision checking.

## Emergency Procedures

### Emergency Stop

**Physical E-Stop**:
1. Press red emergency stop button on Baxter
2. Robot will immediately stop and disable
3. To resume: rotate e-stop to release, then re-enable robot

**Software E-Stop**:
```python
# Via API
manager.emergency_stop()

# Via OpenClaw
User: "Emergency stop!"
Assistant: [Calls emergency_stop tool]
```

### Collision Recovery

If robot collides with object:

1. **Immediate**: Press emergency stop
2. **Assess**: Check for damage to robot, gripper, or object
3. **Clear**: Remove obstacle if safe to do so
4. **Reset**: Release e-stop, re-enable robot
5. **Test**: Move to home position slowly
6. **Review**: Analyze what caused collision, update safety constraints if needed

### Unexpected Behavior

If robot moves unexpectedly:

1. **Stop**: Press emergency stop immediately
2. **Disconnect**: Disable robot and disconnect bridge server
3. **Review Logs**: Check bridge server logs for errors
4. **Verify Config**: Ensure safety limits are properly configured
5. **Test in Mock**: Reproduce issue with mock driver
6. **Report**: Document issue for debugging

## Testing Safety

### Pre-Deployment Checklist

Before deploying new code or primitives:

- [ ] Tested with mock driver
- [ ] Verified safety validator catches invalid inputs
- [ ] Tested at low speed (0.1-0.2)
- [ ] Verified emergency stop works
- [ ] Checked workspace limits are appropriate
- [ ] Reviewed motion trajectories
- [ ] Tested error handling (what happens if motion fails?)
- [ ] Documented expected behavior

### Safety Test Cases

```python
# Test 1: Workspace boundary rejection
result = primitives.pick('right', [2.0, 0.0, 0.0])  # Too far
assert result['success'] == False

# Test 2: Invalid position format
result = primitives.pick('right', [0.6, 0.2])  # Missing z
assert result['success'] == False

# Test 3: Emergency stop during motion
# Start motion, trigger e-stop, verify robot stops

# Test 4: Recovery from failed motion
result = primitives.pick('right', invalid_position)
assert result['success'] == False
# Verify robot is still responsive
result = primitives.home('right')
assert result['success'] == True
```

## Workspace Setup Recommendations

### Physical Setup

1. **Table Height**: Position table at comfortable height for Baxter's reach
2. **Lighting**: Ensure good lighting for cameras (future vision integration)
3. **Clear Space**: Minimum 2m x 2m clear area around robot
4. **Stable Surface**: Robot must be on stable, level surface
5. **Cable Management**: Secure all cables to prevent snagging

### Coordinate System

Baxter's coordinate system (right-hand rule):
- **X**: Forward (away from robot base)
- **Y**: Left (from robot's perspective)
- **Z**: Up

Origin is at robot base.

### Calibration

Before first use:
1. Verify home position is safe and accessible
2. Test workspace boundaries with slow motions
3. Calibrate grippers (`gripper_control(arm, "calibrate")`)
4. Measure and record actual workspace dimensions

## Compliance and Liability

### User Responsibility

Users of Baxter-Claw are responsible for:
- Ensuring safe operation environment
- Following all safety guidelines
- Proper training on Baxter robot
- Compliance with local regulations
- Supervision during autonomous operation

### Disclaimer

Baxter-Claw is research software provided "as-is" without warranty. Users assume all risks associated with robot operation. Always follow Rethink Robotics' official Baxter safety guidelines.

### Incident Reporting

Report safety incidents to:
- Your institution's safety officer
- Baxter-Claw GitHub issues (for software-related incidents)
- Rethink Robotics support (for hardware issues)

## Additional Resources

- [Baxter Safety Documentation](http://sdk.rethinkrobotics.com/wiki/Safety)
- [ROS Industrial Safety Guidelines](http://wiki.ros.org/Industrial/Safety)
- [ISO 10218 Robot Safety Standards](https://www.iso.org/standard/51330.html)

## Summary

**Key Safety Principles**:
1. ✅ Always maintain emergency stop access
2. ✅ Test in simulation before real execution
3. ✅ Start slow, gradually increase speed
4. ✅ Monitor continuously during operation
5. ✅ Validate all inputs and motions
6. ✅ Handle errors gracefully
7. ✅ Document and learn from incidents

**Remember**: No task is worth risking injury or equipment damage. When in doubt, stop and reassess.
