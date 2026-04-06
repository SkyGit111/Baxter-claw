# API Reference

## Overview

The Baxter-Claw Bridge Server provides a REST API for controlling the Baxter robot through high-level action primitives.

**Base URL**: `http://localhost:8420`

**Content-Type**: `application/json`

## Authentication

Currently, no authentication is required. The bridge server is designed to run on a trusted local network.

⚠️ **Security Warning**: Do not expose the bridge server to the public internet without implementing authentication.

## Endpoints

### System Endpoints

#### GET /

Root endpoint, returns server information.

**Response**:
```json
{
  "name": "Baxter-Claw Bridge",
  "version": "0.1.0",
  "status": "running"
}
```

#### GET /health

Health check endpoint.

**Response**:
```json
{
  "healthy": true,
  "connected": true,
  "enabled": false
}
```

**Status Codes**:
- `200`: Server is healthy
- `503`: Server not initialized

---

### Robot Control Endpoints

#### POST /enable

Enable robot motors. Must be called before any motion commands.

**Request**: Empty body

**Response**:
```json
{
  "success": true,
  "message": "Robot enabled"
}
```

**Status Codes**:
- `200`: Robot enabled successfully
- `500`: Failed to enable robot

---

#### POST /disable

Disable robot motors.

**Request**: Empty body

**Response**:
```json
{
  "success": true,
  "message": "Robot disabled"
}
```

---

#### GET /status

Get current robot status.

**Query Parameters**:
- `arm` (optional): `"left"` or `"right"` (default: `"right"`)

**Response**:
```json
{
  "connected": true,
  "enabled": true,
  "arm": "right",
  "joint_angles": {
    "right_s0": 0.0,
    "right_s1": -0.55,
    "right_e0": 0.0,
    "right_e1": 0.75,
    "right_w0": 0.0,
    "right_w1": 1.26,
    "right_w2": 0.0
  },
  "endpoint_pose": [0.6, -0.3, 0.2, 0.0, 0.0, 0.0],
  "gripper_position": 50.0,
  "gripper_force": 15.0
}
```

**Fields**:
- `endpoint_pose`: `[x, y, z, roll, pitch, yaw]` in meters and radians
- `gripper_position`: 0-100 (0=closed, 100=open)
- `gripper_force`: Current grip force

---

### Primitive Endpoints

#### POST /primitives/pick

Pick up an object at the specified position.

**Request Body**:
```json
{
  "arm": "right",
  "position": [0.6, 0.2, 0.1],
  "approach_height": 0.1
}
```

**Parameters**:
- `arm` (optional): `"left"` or `"right"` (default: `"right"`)
- `position` (required): `[x, y, z]` in meters
- `approach_height` (optional): Height offset for pre-grasp pose in meters (default: `0.1`)

**Response**:
```json
{
  "success": true,
  "message": "Successfully picked object at [0.6, 0.2, 0.1]",
  "arm": "right",
  "final_position": [0.6, 0.2, 0.2]
}
```

**Execution Sequence**:
1. Move to pre-grasp pose (position + [0, 0, approach_height])
2. Open gripper
3. Descend to target position
4. Close gripper
5. Lift object

**Status Codes**:
- `200`: Pick successful
- `400`: Invalid parameters or motion failed
- `422`: Validation error (invalid position format)

**Example**:
```bash
curl -X POST http://localhost:8420/primitives/pick \
  -H "Content-Type: application/json" \
  -d '{"arm": "right", "position": [0.6, 0.2, 0.1]}'
```

---

#### POST /primitives/place

Place the held object at the specified position.

**Request Body**:
```json
{
  "arm": "right",
  "position": [0.5, -0.3, 0.15],
  "approach_height": 0.1
}
```

**Parameters**:
- `arm` (optional): `"left"` or `"right"` (default: `"right"`)
- `position` (required): `[x, y, z]` in meters
- `approach_height` (optional): Height offset for pre-place pose in meters (default: `0.1`)

**Response**:
```json
{
  "success": true,
  "message": "Successfully placed object at [0.5, -0.3, 0.15]",
  "arm": "right",
  "final_position": [0.5, -0.3, 0.25]
}
```

**Execution Sequence**:
1. Move to pre-place pose (position + [0, 0, approach_height])
2. Descend to target position
3. Open gripper
4. Retract upward

---

#### POST /primitives/move_to

Move end-effector to specified pose.

**Request Body**:
```json
{
  "arm": "right",
  "position": [0.6, 0.0, 0.3],
  "orientation": [0.0, 0.0, 1.57]
}
```

**Parameters**:
- `arm` (optional): `"left"` or `"right"` (default: `"right"`)
- `position` (required): `[x, y, z]` in meters
- `orientation` (optional): `[roll, pitch, yaw]` in radians (default: `[0, 0, 0]`)

**Response**:
```json
{
  "success": true,
  "message": "Successfully moved to [0.6, 0.0, 0.3]",
  "arm": "right",
  "final_position": [0.6, 0.0, 0.3]
}
```

---

#### POST /primitives/home

Return arm to predefined home position.

**Request Body**:
```json
{
  "arm": "right"
}
```

**Parameters**:
- `arm` (optional): `"left"` or `"right"` (default: `"right"`)

**Response**:
```json
{
  "success": true,
  "message": "Right arm returned to home position",
  "arm": "right"
}
```

**Home Positions**:
- Right arm: Safe neutral position with arm slightly raised
- Left arm: Reserved for future implementation

---

### Gripper Control

#### POST /gripper

Control gripper (open, close, or calibrate).

**Request Body**:
```json
{
  "arm": "right",
  "action": "close",
  "force": 30.0
}
```

**Parameters**:
- `arm` (optional): `"left"` or `"right"` (default: `"right"`)
- `action` (required): `"open"`, `"close"`, or `"calibrate"`
- `force` (optional): Grip force 0-100 (default: `30.0`)

**Response**:
```json
{
  "success": true,
  "message": "Gripper close executed"
}
```

**Actions**:
- `open`: Fully open gripper
- `close`: Close gripper with specified force
- `calibrate`: Calibrate gripper (required after power-on)

---

### Emergency Control

#### POST /stop

Execute emergency stop. Immediately stops all robot motion.

**Query Parameters**:
- `arm` (optional): `"left"` or `"right"` (default: `"right"`)

**Request**: Empty body

**Response**:
```json
{
  "success": true,
  "message": "Emergency stop executed"
}
```

⚠️ **Note**: After emergency stop, robot must be re-enabled before further motion.

---

### Camera (Placeholder)

#### GET /camera

Capture image from specified camera.

**Query Parameters**:
- `camera` (optional): Camera identifier (default: `"right_hand"`)

**Response**:
```json
{
  "success": false,
  "message": "Camera capture not yet implemented",
  "camera": "right_hand"
}
```

**Status**: Not yet implemented in v0.1.0

---

## Error Responses

All endpoints may return error responses in the following format:

```json
{
  "detail": "Error message describing what went wrong"
}
```

**Common Status Codes**:
- `400`: Bad request (invalid parameters, motion failed)
- `422`: Validation error (malformed request body)
- `500`: Internal server error
- `503`: Service unavailable (manager not initialized)

**Example Error**:
```json
{
  "detail": "Target pose unsafe: X position 2.0 outside limits [0.3, 0.9]"
}
```

---

## Data Models

### Position

3D position in meters relative to robot base:
```json
[x, y, z]
```

- `x`: Forward (away from robot)
- `y`: Lateral (negative = right, positive = left)
- `z`: Vertical (up)

### Orientation

Orientation in radians (roll-pitch-yaw):
```json
[roll, pitch, yaw]
```

### Pose

Combined position and orientation:
```json
[x, y, z, roll, pitch, yaw]
```

### Joint Angles

Dictionary mapping joint names to angles in radians:
```json
{
  "right_s0": 0.0,
  "right_s1": -0.55,
  "right_e0": 0.0,
  "right_e1": 0.75,
  "right_w0": 0.0,
  "right_w1": 1.26,
  "right_w2": 0.0
}
```

**Joint Names**:
- `s0`: Shoulder rotation
- `s1`: Shoulder elevation
- `e0`: Elbow rotation
- `e1`: Elbow flexion
- `w0`: Wrist rotation
- `w1`: Wrist flexion
- `w2`: Wrist roll

---

## Usage Examples

### Python

```python
import requests

BASE_URL = "http://localhost:8420"

# Enable robot
response = requests.post(f"{BASE_URL}/enable")
print(response.json())

# Pick object
response = requests.post(
    f"{BASE_URL}/primitives/pick",
    json={"arm": "right", "position": [0.6, 0.2, 0.1]}
)
print(response.json())

# Place object
response = requests.post(
    f"{BASE_URL}/primitives/place",
    json={"arm": "right", "position": [0.5, -0.3, 0.15]}
)
print(response.json())

# Return home
response = requests.post(
    f"{BASE_URL}/primitives/home",
    json={"arm": "right"}
)
print(response.json())
```

### JavaScript/TypeScript

```typescript
const BASE_URL = "http://localhost:8420";

// Enable robot
const enableResponse = await fetch(`${BASE_URL}/enable`, {
  method: "POST"
});
console.log(await enableResponse.json());

// Pick object
const pickResponse = await fetch(`${BASE_URL}/primitives/pick`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    arm: "right",
    position: [0.6, 0.2, 0.1]
  })
});
console.log(await pickResponse.json());
```

### cURL

```bash
# Enable robot
curl -X POST http://localhost:8420/enable

# Get status
curl http://localhost:8420/status?arm=right

# Pick object
curl -X POST http://localhost:8420/primitives/pick \
  -H "Content-Type: application/json" \
  -d '{"arm": "right", "position": [0.6, 0.2, 0.1]}'

# Place object
curl -X POST http://localhost:8420/primitives/place \
  -H "Content-Type: application/json" \
  -d '{"arm": "right", "position": [0.5, -0.3, 0.15]}'

# Home
curl -X POST http://localhost:8420/primitives/home \
  -H "Content-Type: application/json" \
  -d '{"arm": "right"}'

# Emergency stop
curl -X POST http://localhost:8420/stop
```

---

## Rate Limiting

Currently, no rate limiting is implemented. For production use, consider implementing rate limiting to prevent abuse.

## WebSocket Support

Not currently supported. All communication is via HTTP REST API.

## API Versioning

Current version: `v0.1.0`

API versioning will be introduced in future releases if breaking changes are necessary.

---

## See Also

- [Architecture Documentation](architecture.md)
- [Safety Guidelines](safety.md)
- [Quick Start Guide](quickstart.md)
