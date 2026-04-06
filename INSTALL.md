# Installation Guide

Complete installation instructions for Baxter-Claw.

## Quick Install (TL;DR)

```bash
# On Baxter control host (Linux + ROS)
git clone https://github.com/yourusername/baxter-claw.git
cd baxter-claw
pip install -e .
cp config/baxter.example.yaml config/baxter.yaml
# Edit config/baxter.yaml as needed
baxter-claw-bridge --config config/baxter.yaml
```

## Detailed Installation

See full installation guide with troubleshooting in the repository.

## System Requirements

- **OS**: Ubuntu 18.04/20.04 (for ROS)
- **Python**: 3.8+
- **ROS**: Melodic or Noetic
- **Node.js**: 18+ (for plugin)
- **Hardware**: Baxter robot (or use mock driver)

## Next Steps

After installation:
1. Read [Quick Start Guide](docs/quickstart.md)
2. Review [Safety Guidelines](docs/safety.md)
3. Test with mock driver: `python examples/test_primitives.py`
4. Deploy to real Baxter

## Support

- Documentation: [docs/](docs/)
- Issues: GitHub Issues
- ROS Help: http://answers.ros.org/
