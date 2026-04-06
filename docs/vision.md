# Vision Features Documentation

## Overview

Baxter-Claw now includes vision capabilities powered by Vision-Language Models (VLMs). This allows the robot to:
- Locate objects by name using natural language
- Identify all objects in a scene
- Get descriptions of the environment
- Pick objects without knowing exact coordinates

## Architecture

```
User: "Pick up the red cup"
    ↓
OpenClaw LLM
    ↓
pick_by_name tool
    ↓
Bridge Server
    ↓
1. Capture image from camera
2. Send to VLM (Claude/GPT-4V)
3. VLM locates object
4. Execute pick primitive
    ↓
Baxter Robot
```

## Configuration

### Enable Vision Features

Edit `config/baxter.yaml`:

```yaml
vlm:
  enabled: true
  provider: "claude"  # or "openai"
  api_key: "${ANTHROPIC_API_KEY}"  # or set directly
```

### Set API Key

**Option 1: Environment Variable (Recommended)**
```bash
export ANTHROPIC_API_KEY="your-api-key-here"
# or
export OPENAI_API_KEY="your-api-key-here"
```

**Option 2: Configuration File**
```yaml
vlm:
  enabled: true
  provider: "claude"
  api_key: "sk-ant-..."  # Not recommended for production
```

## Available Vision Tools

### 1. pick_by_name

Pick up an object by name using vision.

**Usage:**
```
User: "Pick up the red cup"
User: "Grab the blue box"
User: "Pick up my phone"
```

**Parameters:**
- `object_name` (required): Name of object to pick
- `arm` (optional): Which arm to use (default: "right")
- `camera` (optional): Which camera to use (default: "right_hand")

**Example API Call:**
```bash
curl -X POST http://localhost:8420/vision/pick_by_name \
  -H "Content-Type: application/json" \
  -d '{
    "arm": "right",
    "object_name": "red cup",
    "camera": "right_hand"
  }'
```

**Response:**
```json
{
  "success": true,
  "message": "Successfully picked object",
  "object_name": "red cup",
  "position": [0.65, 0.2, 0.1],
  "confidence": 85.5,
  "vlm_response": {
    "found": true,
    "description": "Red ceramic cup located on the table",
    "bounding_box": [320, 240, 450, 380]
  }
}
```

### 2. locate_object

Locate an object without moving the robot.

**Usage:**
```
User: "Where is the red cup?"
User: "Can you see the blue box?"
User: "Locate my phone"
```

**Parameters:**
- `object_name` (required): Name of object to locate
- `camera` (optional): Which camera to use

**Example:**
```bash
curl -X POST http://localhost:8420/vision/locate_object \
  -H "Content-Type: application/json" \
  -d '{"object_name": "red cup"}'
```

**Response:**
```json
{
  "success": true,
  "message": "Object found",
  "object_name": "red cup",
  "position": [0.65, 0.2, 0.1],
  "confidence": 85.5,
  "description": "Red ceramic cup on the table",
  "bounding_box": [320, 240, 450, 380]
}
```

### 3. describe_scene

Get a description of what the robot sees.

**Usage:**
```
User: "What do you see?"
User: "Describe the scene"
User: "What's on the table?"
```

**Example:**
```bash
curl -X POST http://localhost:8420/vision/describe_scene \
  -H "Content-Type: application/json" \
  -d '{"camera": "right_hand"}'
```

**Response:**
```json
{
  "success": true,
  "message": "Scene described successfully",
  "description": "I can see a table with several objects: a red ceramic cup in the center-left area, a blue rectangular box on the right side, and a smartphone near the edge. The workspace appears clear with good lighting. The red cup appears to be the most accessible object for grasping."
}
```

### 4. identify_objects

Identify all objects in the scene.

**Usage:**
```
User: "What objects can you see?"
User: "List all objects on the table"
User: "Identify everything in view"
```

**Example:**
```bash
curl -X POST http://localhost:8420/vision/identify_objects \
  -H "Content-Type: application/json" \
  -d '{"camera": "right_hand"}'
```

**Response:**
```json
{
  "success": true,
  "message": "Identified 3 objects",
  "objects": [
    {
      "name": "red cup",
      "color": "red",
      "size": "medium",
      "location": "center-left",
      "graspable": true
    },
    {
      "name": "blue box",
      "color": "blue",
      "size": "large",
      "location": "right side",
      "graspable": true
    },
    {
      "name": "smartphone",
      "color": "black",
      "size": "small",
      "location": "near edge",
      "graspable": true
    }
  ]
}
```

## Camera Options

Baxter has three cameras:
- `right_hand`: Camera on right gripper (default for right arm operations)
- `left_hand`: Camera on left gripper
- `head`: Camera on head (wider view)

**Choosing the right camera:**
- Use hand cameras for close-up object manipulation
- Use head camera for scene overview
- Match camera to the arm you're using (right_hand for right arm)

## Usage Examples

### Example 1: Vision-Guided Pick and Place

```
User: "What objects do you see?"
Assistant: [Calls identify_objects] I can see a red cup, blue box, and phone.

User: "Pick up the red cup"
Assistant: [Calls pick_by_name] Locating red cup... Found at position [0.65, 0.2, 0.1] with 85% confidence. Picking up... Success!

User: "Place it at x=0.5, y=-0.3, z=0.15"
Assistant: [Calls place] Placing object... Done!
```

### Example 2: Scene Understanding

```
User: "Describe what you see"
Assistant: [Calls describe_scene] I can see a table with several objects: a red cup in the center, a blue box on the right, and a phone near the edge. The workspace is clear and well-lit.

User: "Where is the phone?"
Assistant: [Calls locate_object] The phone is located at position [0.7, 0.35, 0.05], near the edge of the table.
```

### Example 3: Natural Language Manipulation

```
User: "Grab my phone and move it to the center"
Assistant: [Calls pick_by_name for "phone"] Locating phone... Picking up... [Calls move_to with center position] Moving to center... Done!
```

## VLM Providers

### Claude (Anthropic)

**Model:** `claude-3-5-sonnet-20241022`

**Pros:**
- Excellent vision understanding
- Good at spatial reasoning
- Detailed descriptions

**Setup:**
```yaml
vlm:
  enabled: true
  provider: "claude"
  api_key: "${ANTHROPIC_API_KEY}"
```

### GPT-4V (OpenAI)

**Model:** `gpt-4-vision-preview`

**Pros:**
- Fast response times
- Good object recognition
- Wide availability

**Setup:**
```yaml
vlm:
  enabled: true
  provider: "openai"
  api_key: "${OPENAI_API_KEY}"
```

## Limitations

### Current Limitations

1. **3D Position Estimation**: VLM estimates 3D positions from 2D images. Accuracy depends on:
   - Camera angle
   - Object size and distance
   - Workspace calibration

2. **Confidence Threshold**: Operations with <50% confidence are rejected by default

3. **Object Ambiguity**: Similar objects may be confused (e.g., "red cup" when there are multiple red cups)

4. **Lighting Conditions**: Poor lighting affects recognition accuracy

### Best Practices

1. **Use Specific Names**: "red ceramic cup" is better than "cup"
2. **Check Confidence**: Review confidence scores before critical operations
3. **Verify with locate_object**: Use locate_object to verify position before pick
4. **Good Lighting**: Ensure workspace is well-lit
5. **Clear Workspace**: Minimize clutter for better recognition

## Troubleshooting

### VLM Not Working

**Problem:** "VLM client not configured"

**Solution:**
```yaml
# Check config/baxter.yaml
vlm:
  enabled: true  # Must be true
  provider: "claude"
  api_key: "${ANTHROPIC_API_KEY}"
```

```bash
# Set environment variable
export ANTHROPIC_API_KEY="your-key"
```

### Low Confidence

**Problem:** "Low confidence (30%) in object location"

**Solutions:**
- Improve lighting
- Use more specific object names
- Move camera closer to object
- Clear workspace of similar objects

### Object Not Found

**Problem:** "Could not locate object in image"

**Solutions:**
- Verify object is in camera view
- Use describe_scene to see what's visible
- Try different camera angle
- Check if object name is too generic

### Camera Capture Failed

**Problem:** "Failed to capture image"

**Solutions:**
```bash
# Check ROS topics
rostopic list | grep camera

# Test camera manually
rostopic echo /cameras/right_hand_camera/image --noarr

# Verify cv_bridge is installed
pip install cv-bridge
```

## API Reference

See [api.md](api.md) for complete API documentation of vision endpoints.

## Performance

**Typical Response Times:**
- Camera capture: 0.5-1s
- VLM inference: 2-5s
- Total pick_by_name: 8-15s

**Cost Considerations:**
- Claude API: ~$0.01-0.03 per image
- OpenAI API: ~$0.01-0.02 per image
- Consider caching for repeated queries

## Future Enhancements

Planned improvements:
- [ ] Depth estimation from stereo cameras
- [ ] Object tracking across frames
- [ ] Grasp pose estimation
- [ ] Scene segmentation
- [ ] Custom object training

---

**Next Steps:**
- Try the vision examples above
- Experiment with different object names
- Integrate vision into your workflows
- See [examples/vision_demo.py](../examples/vision_demo.py) for code examples
