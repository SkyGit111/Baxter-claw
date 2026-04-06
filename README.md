# Baxter-Claw

Natural language control for Baxter dual-arm robot via OpenClaw LLM agent platform.

[简体中文](README_CN.md) | English

[![Tests](https://github.com/yourusername/baxter-claw/workflows/Tests/badge.svg)](https://github.com/yourusername/baxter-claw/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

## Overview

Baxter-Claw enables intuitive natural language interaction with the Baxter research robot through high-level action primitives. Built on top of [OpenClaw](https://openclaw.ai/), it provides a bridge between LLM reasoning and physical robot control.

**Key Features:**
- 🤖 High-level action primitives: `pick`, `place`, `move_to`, `home`
- 🔌 Plugin-based integration with OpenClaw
- 🛡️ Built-in safety validation
- 🎯 Single-arm control (right arm) with dual-arm interface reserved
- 📷 Camera interface for future vision integration
- 🧪 Mock driver for testing without hardware

## Quick Start

```bash
# Install
git clone https://github.com/yourusername/baxter-claw.git
cd baxter-claw
pip install -e .

# Configure (edit config/baxter.yaml)
cp config/baxter.example.yaml config/baxter.yaml

# Start bridge server
baxter-claw-bridge --config config/baxter.yaml

# Install plugin
cd plugin && npm install && npm run build
cp -r . ~/.openclaw/plugins/baxter-claw

# Start OpenClaw and use natural language!
```

See [INSTALL.md](INSTALL.md) for detailed installation instructions.

## Usage Example

```
User: "Enable the robot"
Assistant: [Calls robot_enable tool] Robot enabled successfully.

User: "Pick up the object at position x=0.6, y=0.2, z=0.1"
Assistant: [Calls pick tool] Moving to pre-grasp position... 
Grasping... Lifted object successfully.

User: "Place it at x=0.5, y=-0.3, z=0.15"
Assistant: [Calls place tool] Moving to target... Placing... 
Released object.

User: "Return to home position"
Assistant: [Calls home tool] Right arm returned to home position.
```

## Architecture

```
User (Natural Language)
      ↓
OpenClaw LLM Agent
      ↓ (HTTP Tool Calls)
Bridge Server (FastAPI)
      ↓
BaxterDriver (baxter_interface SDK)
      ↓ (ROS Topics/Services)
Baxter Robot
```

## Action Primitives

### pick(arm, position, approach_height)
Grasp an object at the specified position.

### place(arm, position, approach_height)
Place the held object at the specified position.

### move_to(arm, position, orientation)
Move end-effector to specified pose.

### home(arm)
Return arm to predefined home position.

## Documentation

- 📖 [Installation Guide](INSTALL.md)
- 🚀 [Quick Start](docs/quickstart.md)
- 🏗️ [Architecture](docs/architecture.md)
- 📡 [API Reference](docs/api.md)
- 🛡️ [Safety Guidelines](docs/safety.md)

## Project Structure

```
baxter-claw/
├── bridge/              # Python Bridge Server
│   ├── drivers/        # Robot drivers (Baxter, Mock)
│   ├── primitives.py   # High-level action primitives
│   ├── safety.py       # Safety validation
│   └── server.py       # FastAPI server
├── plugin/             # OpenClaw TypeScript plugin
├── config/             # Configuration files
├── docs/               # Documentation
├── examples/           # Example scripts
└── tests/              # Unit tests
```

## Development

### Testing without Hardware

```bash
# Use mock driver
# Edit config/baxter.yaml: driver.type = "mock"
baxter-claw-bridge --config config/baxter.yaml

# Run tests
pytest tests/ -v

# Test primitives
python examples/test_primitives.py
```

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=bridge --cov-report=html

# Specific test file
pytest tests/test_primitives.py -v
```

## Roadmap

- [x] High-level primitives (pick, place, move_to, home)
- [x] Single-arm control (right arm)
- [x] Mock driver for testing
- [ ] Vision integration (VLM-based object localization)
- [ ] Dual-arm coordination primitives
- [ ] Mid-level motion primitives
- [ ] Skill mode (code generation)
- [ ] Trajectory planning and optimization

## Safety

⚠️ **Important Safety Notes:**
- Always test in mock mode first
- Keep emergency stop accessible
- Verify workspace limits before deployment
- Monitor robot during autonomous operation
- See [docs/safety.md](docs/safety.md) for detailed guidelines

## Requirements

- Python 3.8+
- Ubuntu 18.04/20.04 with ROS Melodic/Noetic
- Baxter SDK installed and configured
- Node.js 18+ (for plugin)
- OpenClaw installed

## Contributing

Contributions welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) first.

## License

MIT License - see [LICENSE](LICENSE) for details.

## Acknowledgments

- Inspired by [ClawArm](https://github.com/agilexrobotics/clawarm)
- Built on [OpenClaw](https://openclaw.ai/) agent platform
- Uses [Baxter SDK](http://sdk.rethinkrobotics.com/)

## Citation

If you use Baxter-Claw in your research, please cite:

```bibtex
@software{baxter_claw_2026,
  title = {Baxter-Claw: Natural Language Control for Baxter Robot},
  author = {Your Name},
  year = {2026},
  url = {https://github.com/yourusername/baxter-claw}
}
```

## Contact

- GitHub Issues: [Report bugs or request features](https://github.com/yourusername/baxter-claw/issues)
- Documentation: [Full docs](https://github.com/yourusername/baxter-claw/docs)

---

**Built with ❤️ for the robotics research community**
