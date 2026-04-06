# Baxter-Claw Quick Start Guide

## Prerequisites

### Hardware Requirements
- Baxter research robot
- Linux workstation with ROS (Ubuntu 18.04/20.04 recommended)
- Network connection to Baxter

### Software Requirements
- Python 3.8+
- ROS Melodic or Noetic
- Baxter SDK installed and configured
- Node.js 18+ (for plugin)
- OpenClaw installed

## Installation Steps

### 1. Clone Repository

```bash
cd ~
git clone https://github.com/yourusername/baxter-claw.git
cd baxter-claw
```

### 2. Install Python Dependencies

```bash
pip install -e .
```

This installs:
- FastAPI and Uvicorn (web server)
- Pydantic (data validation)
- PyYAML (configuration)
- NumPy (math operations)

### 3. Configure Baxter Environment

```bash
# Source your Baxter workspace
cd ~/ros_ws
./baxter.sh

# Verify Baxter connection
rostopic list | grep robot

# You should see topics like:
# /robot/state
# /robot/limb/right/...
# /robot/limb/left/...
```

### 4. Configure Bridge Server

```bash
cd ~/baxter-claw
cp config/baxter.example.yaml config/baxter.yaml

# Edit config/baxter.yaml
nano config/baxter.yaml
```

For real hardware, set:
```yaml
driver:
  type: "baxter"  # Use real Baxter driver
```

For testing without hardware:
```yaml
driver:
  type: "mock"  # Use simulation
```

### 5. Test Bridge Server

```bash
# Start the bridge server
baxter-claw-bridge --config config/baxter.yaml

# You should see:
# Creating BaxterDriver (real hardware)
# or
# Creating MockDriver (simulation)
# Starting server on 0.0.0.0:8420
```

In another terminal, test the API:

```bash
# Health check
curl http://localhost:8420/health

# Enable robot
curl -X POST http://localhost:8420/enable

# Get status
curl http://localhost:8420/status?arm=right

# Test pick primitive (mock mode)
curl -X POST http://localhost:8420/primitives/pick \
  -H "Content-Type: application/json" \
  -d '{"arm": "right", "position": [0.6, 0.2, 0.1]}'
```

### 6. Install OpenClaw Plugin

```bash
cd ~/baxter-claw/plugin

# Install Node.js dependencies
npm install

# Build TypeScript
npm run build

# Copy to OpenClaw plugins directory
mkdir -p ~/.openclaw/plugins
cp -r . ~/.openclaw/plugins/baxter-claw
```

### 7. Configure OpenClaw

```bash
# Copy example config
cp config/openclaw.example.json ~/.openclaw/config.json

# Edit with your API key
nano ~/.openclaw/config.json
```

Set your API key:
```json
{
  "model": "claude-opus-4-6",
  "api_key": "your-anthropic-api-key-here",
  "plugins": ["baxter-claw"]
}
```

### 8. Start OpenClaw

```bash
openclaw
```

OpenClaw should start and load the baxter-claw plugin. You'll see:
```
Loading plugin: baxter-claw
Registered tools: robot_enable, pick, place, move_to, home, ...
OpenClaw ready at http://localhost:18789
```

## First Test

### Using Mock Driver (No Hardware)

1. **Start Bridge Server** (in terminal 1):
```bash
baxter-claw-bridge --config config/baxter.yaml
# (with driver.type: "mock")
```

2. **Start OpenClaw** (in terminal 2):
```bash
openclaw
```

3. **Open OpenClaw Web UI**:
```
http://localhost:18789
```

4. **Try Natural Language Commands**:

```
You: "Enable the robot"
Assistant: [Calls robot_enable tool] Robot enabled successfully.

You: "Pick up an object at position x=0.6, y=0.2, z=0.1"
Assistant: [Calls pick tool] Moving to pre-grasp position... 
Grasping... Lifted object successfully.

You: "Place it at x=0.5, y=-0.3, z=0.15"
Assistant: [Calls place tool] Moving to target... Placing... 
Released object.

You: "Return to home position"
Assistant: [Calls home tool] Right arm returned to home position.
```

### Using Real Baxter

1. **Ensure Baxter is powered on and connected**

2. **Source Baxter environment**:
```bash
cd ~/ros_ws
./baxter.sh
```

3. **Edit config** to use real driver:
```yaml
# config/baxter.yaml
driver:
  type: "baxter"
```

4. **Start bridge server**:
```bash
baxter-claw-bridge --config config/baxter.yaml
```

5. **Verify connection**:
```bash
curl http://localhost:8420/health
# Should return: {"healthy": true, "connected": true, "enabled": false}
```

6. **Enable robot via OpenClaw**:
```
You: "Enable the robot"
```

7. **Test simple motion**:
```
You: "Move the right arm to home position"
```

8. **Test pick and place** (adjust coordinates for your setup):
```
You: "Pick up the object at x=0.65, y=-0.2, z=0.0"
You: "Place it at x=0.5, y=-0.4, z=0.05"
```

## Running Example Scripts

### Test Primitives (Python)

```bash
cd ~/baxter-claw
python examples/test_primitives.py
```

This will:
1. Connect to robot (mock or real)
2. Enable motors
3. Test pick primitive
4. Test place primitive
5. Test move_to primitive
6. Test home primitive
7. Display results

## Troubleshooting

### Bridge Server Won't Start

**Problem**: `ImportError: No module named baxter_interface`

**Solution**: 
```bash
# Make sure ROS environment is sourced
source ~/ros_ws/baxter.sh
# Or use mock driver for testing
```

**Problem**: `Address already in use (port 8420)`

**Solution**:
```bash
# Kill existing process
lsof -ti:8420 | xargs kill -9
# Or use different port
baxter-claw-bridge --config config/baxter.yaml --port 8421
```

### OpenClaw Can't Connect to Bridge

**Problem**: Plugin tools fail with connection error

**Solution**:
```bash
# Check bridge is running
curl http://localhost:8420/health

# Check plugin config
cat ~/.openclaw/plugins/baxter-claw/openclaw.plugin.json
# Ensure "url": "http://localhost:8420"
```

### Robot Won't Move

**Problem**: Commands accepted but robot doesn't move

**Checklist**:
1. Is robot enabled? Call `robot_enable` first
2. Check robot state: `curl http://localhost:8420/status`
3. Verify ROS connection: `rostopic echo /robot/state`
4. Check for errors in bridge server logs

### Safety Errors

**Problem**: "Target outside safe workspace"

**Solution**: Adjust workspace limits in `config/baxter.yaml`:
```yaml
safety:
  workspace:
    x: [0.3, 0.9]  # Adjust based on your setup
    y: [-0.7, 0.7]
    z: [-0.2, 0.5]
```

## Next Steps

- Read [architecture.md](architecture.md) to understand system design
- See [api.md](api.md) for complete API reference
- Check [safety.md](safety.md) for safety guidelines
- Explore adding custom primitives
- Integrate vision for object detection

## Getting Help

- GitHub Issues: https://github.com/yourusername/baxter-claw/issues
- Documentation: https://github.com/yourusername/baxter-claw/docs
- Baxter SDK Docs: http://sdk.rethinkrobotics.com/
