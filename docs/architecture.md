# Baxter-Claw Architecture

## Overview

Baxter-Claw is a natural language control system for the Baxter dual-arm research robot. It bridges the gap between high-level LLM reasoning (via OpenClaw) and low-level robot control (via Baxter SDK).

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         User Layer                          │
│                   (Natural Language Input)                  │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                      OpenClaw Platform                      │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              LLM Agent (Claude/GPT/Qwen)             │  │
│  │  • Natural language understanding                    │  │
│  │  • Task planning and reasoning                       │  │
│  │  • Tool selection and invocation                     │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────┘
                             │ HTTP (Tool Calls)
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                   Baxter-Claw Plugin                        │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              TypeScript Plugin Layer                 │  │
│  │  • Tool definitions (pick, place, move_to, home)     │  │
│  │  • Parameter validation                              │  │
│  │  • Bridge client (HTTP communication)                │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────┘
                             │ REST API (Port 8420)
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                    Bridge Server (FastAPI)                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │                   ArmManager                         │  │
│  │  • Robot lifecycle management                        │  │
│  │  • State tracking (connected, enabled)               │  │
│  │  • Component coordination                            │  │
│  └──────────────────────────────────────────────────────┘  │
│                             │                               │
│  ┌──────────────┬───────────┴───────────┬──────────────┐  │
│  │              │                       │              │  │
│  ▼              ▼                       ▼              ▼  │
│ ┌────────┐  ┌─────────┐           ┌────────┐  ┌────────┐ │
│ │Primitives│ │ Safety  │           │ Driver │  │ Models │ │
│ │          │ │Validator│           │        │  │        │ │
│ └────────┘  └─────────┘           └────────┘  └────────┘ │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                      Driver Layer                           │
│  ┌──────────────────────┐      ┌──────────────────────┐    │
│  │   BaxterDriver       │      │    MockDriver        │    │
│  │  (Real Hardware)     │      │   (Simulation)       │    │
│  └──────────────────────┘      └──────────────────────┘    │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                   Baxter SDK (baxter_interface)             │
│                        ROS Topics/Services                  │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                    Baxter Physical Robot                    │
│                  Left Arm | Right Arm | Grippers            │
└─────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. OpenClaw Platform (External)

**Role**: LLM agent orchestration and natural language understanding

**Responsibilities**:
- Parse user natural language input
- Reason about task requirements
- Select appropriate tools to invoke
- Handle multi-step task planning
- Provide conversational feedback to user

**Technology**: Model-agnostic (supports Claude, GPT, Qwen, etc.)

### 2. Baxter-Claw Plugin (TypeScript)

**Role**: Bridge between OpenClaw and Bridge Server

**Components**:
- `index.ts`: Plugin entry point, tool registration
- `bridge-client.ts`: HTTP client for Bridge API
- `openclaw.plugin.json`: Tool definitions and metadata

**Tools Provided**:
- `robot_enable`: Enable robot motors
- `robot_status`: Query robot state
- `pick`: High-level pick primitive
- `place`: High-level place primitive
- `move_to`: Move to Cartesian pose
- `home`: Return to home position
- `gripper_control`: Open/close gripper
- `emergency_stop`: Emergency stop

### 3. Bridge Server (Python FastAPI)

**Role**: Core control logic and robot abstraction

**Components**:

#### ArmManager
- Robot lifecycle management (connect, enable, disable)
- State tracking
- Coordinates primitives, safety, and driver

#### Primitives Layer
High-level semantic actions:
- `pick(arm, position, approach_height)`: Grasp object
- `place(arm, position, approach_height)`: Release object
- `move_to(arm, position, orientation)`: Move to pose
- `home(arm)`: Return to safe position

Each primitive is a sequence of lower-level operations with built-in safety checks.

#### Safety Validator
- Joint limit checking (per Baxter specs)
- Workspace boundary validation
- Speed limit enforcement
- Motion validation before execution

#### Driver Interface
Abstract base class defining robot control API:
- Connection management
- Joint/Cartesian motion
- Gripper control
- State queries

### 4. Driver Layer

#### BaxterDriver (Real Hardware)
- Uses `baxter_interface` Python SDK
- Communicates via ROS topics/services
- Implements IK for Cartesian motions
- Handles gripper control
- Camera interface (placeholder)

#### MockDriver (Simulation)
- In-memory state simulation
- No hardware required
- Useful for development and testing
- Mimics timing and behavior

**Driver Selection**: Configured via YAML (`driver.type: "baxter"` or `"mock"`)

### 5. Baxter SDK Layer

**Technology**: ROS-based Python SDK (`baxter_interface`)

**Key APIs Used**:
- `RobotEnable`: Enable/disable robot
- `Limb`: Arm control (joint/Cartesian motion)
- `Gripper`: Gripper control
- `CameraController`: Camera access (future)

## Data Flow Examples

### Example 1: Simple Pick Operation

```
User: "Pick up the object at x=0.6, y=0.2, z=0.1"
  │
  ▼
OpenClaw LLM:
  - Understands intent: pick operation
  - Extracts parameters: position=[0.6, 0.2, 0.1]
  - Calls tool: pick(arm="right", position=[0.6, 0.2, 0.1])
  │
  ▼
Plugin (TypeScript):
  - Validates parameters
  - HTTP POST /primitives/pick
  │
  ▼
Bridge Server:
  - Receives request
  - Calls primitives.pick()
  │
  ▼
Primitives Layer:
  1. Safety check: workspace validation
  2. Move to pre-grasp (position + [0, 0, 0.1])
  3. Open gripper
  4. Descend to target
  5. Close gripper
  6. Lift object
  │
  ▼
Driver (BaxterDriver):
  - move_to_pose() → IK solve → move_to_joint_positions()
  - gripper_command() → baxter_interface.Gripper
  │
  ▼
Baxter SDK:
  - Publishes joint commands to ROS topics
  - Monitors motion completion
  │
  ▼
Physical Robot:
  - Executes motion
  - Returns status
  │
  ▼
Response flows back up the stack to user
```

### Example 2: Status Query

```
User: "What's the current position of the right arm?"
  │
  ▼
OpenClaw: Calls robot_status(arm="right")
  │
  ▼
Plugin: HTTP GET /status?arm=right
  │
  ▼
Bridge: manager.get_status('right')
  │
  ▼
Driver: 
  - get_joint_angles()
  - get_endpoint_pose()
  - get_gripper_state()
  │
  ▼
Baxter SDK: Query ROS topics
  │
  ▼
Response: {
  connected: true,
  enabled: true,
  joint_angles: {...},
  endpoint_pose: [x, y, z, r, p, y],
  gripper_position: 50.0,
  gripper_force: 15.0
}
```

## Design Principles

### 1. Layered Abstraction
Each layer has a clear responsibility and interface. Higher layers don't need to know implementation details of lower layers.

### 2. Safety First
Multiple safety checks at different levels:
- Primitives validate workspace before motion
- Safety validator checks all parameters
- Driver enforces hardware limits

### 3. Extensibility
- Abstract driver interface allows swapping hardware
- Primitive layer can be extended with new actions
- Plugin can add new tools without changing bridge

### 4. Testability
- Mock driver enables testing without hardware
- Each component can be unit tested independently
- Integration tests use mock driver

### 5. Separation of Concerns
- LLM reasoning (OpenClaw) separate from robot control (Bridge)
- High-level semantics (primitives) separate from low-level control (driver)
- Safety logic isolated in dedicated validator

## Future Extensions

### Planned Features

1. **Vision Integration**
   - Camera capture implementation
   - VLM-based object localization
   - Visual servoing

2. **Dual-Arm Coordination**
   - Bimanual primitives (bimanual_pick, handover)
   - Synchronized motion control
   - Collision avoidance between arms

3. **Mid-Level Primitives**
   - Approach, retract, grasp (as standalone)
   - Trajectory primitives (linear, circular)
   - Force-controlled motions

4. **Skill Mode**
   - Code generation (like ClawArm)
   - Direct baxter_interface script execution
   - Custom motion sequences

5. **Advanced Planning**
   - MoveIt integration for path planning
   - Collision detection
   - Trajectory optimization

### Extension Points

**Adding New Primitives**:
1. Add method to `BaxterPrimitives` class
2. Add endpoint to `server.py`
3. Add tool definition to `openclaw.plugin.json`
4. Implement tool handler in `index.ts`

**Supporting New Hardware**:
1. Implement `ArmDriver` interface
2. Update config to support new driver type
3. No changes needed to primitives or plugin

**Adding Vision**:
1. Implement `capture_image()` in BaxterDriver
2. Add VLM client to bridge
3. Create vision-aware primitives (e.g., `pick_object_by_name`)

## Configuration

### Bridge Configuration (`config/baxter.yaml`)
```yaml
driver:
  type: "baxter"  # or "mock"

safety:
  workspace:
    x: [0.3, 0.9]
    y: [-0.7, 0.7]
    z: [-0.2, 0.5]
  max_speed: 0.5

primitives:
  approach_height: 0.1
  grasp_force: 30.0
```

### OpenClaw Configuration (`config/openclaw.example.json`)
```json
{
  "model": "claude-opus-4-6",
  "plugins": ["baxter-claw"],
  "agent": {
    "system_prompt": "You are a robotics assistant..."
  }
}
```

## Deployment

### Development (Windows + Mock)
```bash
# On Windows machine
cd baxter-claw
pip install -e .
baxter-claw-bridge --config config/baxter.example.yaml
# (driver.type should be "mock")
```

### Production (Linux + Real Baxter)
```bash
# On Baxter control host (Linux + ROS)
source ~/ros_ws/baxter.sh
cd baxter-claw
pip install -e .
# Edit config/baxter.yaml: driver.type = "baxter"
baxter-claw-bridge --config config/baxter.yaml
```

### Plugin Installation
```bash
cd plugin
npm install
npm run build
cp -r . ~/.openclaw/plugins/baxter-claw
```

## API Reference

See [api.md](api.md) for detailed REST API documentation.
