# Changelog

All notable changes to Baxter-Claw will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned
- Vision integration (VLM-based object localization)
- Dual-arm coordination primitives
- Mid-level motion primitives
- Skill mode (code generation)
- MoveIt integration for path planning

## [0.1.0] - 2026-04-01

### Added
- Initial release of Baxter-Claw
- High-level action primitives: `pick`, `place`, `move_to`, `home`
- FastAPI bridge server for robot control
- BaxterDriver for real hardware control via baxter_interface SDK
- MockDriver for testing without hardware
- Safety validation (workspace limits, joint limits, speed limits)
- OpenClaw TypeScript plugin with 8 tools
- Comprehensive documentation (README, quickstart, architecture, safety)
- Unit tests for drivers, primitives, safety, and API
- Example scripts for testing primitives
- Configuration system (YAML for bridge, JSON for OpenClaw)

### Features
- **Primitives**: Semantic action primitives for intuitive robot control
- **Safety**: Multi-layer safety validation before motion execution
- **Extensibility**: Abstract driver interface for supporting different robots
- **Testing**: Mock driver enables development without hardware
- **Documentation**: Complete setup guides and API reference

### Supported Platforms
- Python 3.8+
- Ubuntu 18.04/20.04 with ROS Melodic/Noetic
- Baxter research robot
- OpenClaw agent platform

### Known Limitations
- Single-arm control only (right arm, left arm interface reserved)
- No vision integration yet (camera interface placeholder)
- No dual-arm coordination
- IK solution in BaxterDriver is simplified (production use should consider MoveIt)
- Camera capture not implemented

### Dependencies
- fastapi >= 0.104.0
- uvicorn >= 0.24.0
- pydantic >= 2.0.0
- pyyaml >= 6.0
- numpy >= 1.24.0
- baxter_interface (via ROS workspace)

[Unreleased]: https://github.com/yourusername/baxter-claw/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/yourusername/baxter-claw/releases/tag/v0.1.0
