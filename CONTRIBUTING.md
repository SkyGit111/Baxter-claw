# Contributing to Baxter-Claw

Thank you for your interest in contributing to Baxter-Claw! This document provides guidelines for contributing to the project.

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/yourusername/baxter-claw.git`
3. Create a branch: `git checkout -b feature/your-feature-name`
4. Make your changes
5. Test thoroughly
6. Submit a pull request

## Development Setup

### Prerequisites
- Python 3.8+
- Node.js 18+
- Git

### Installation

```bash
# Clone repository
git clone https://github.com/yourusername/baxter-claw.git
cd baxter-claw

# Install Python dependencies
pip install -e ".[dev]"

# Install Node.js dependencies (for plugin)
cd plugin
npm install
cd ..
```

### Running Tests

```bash
# Run Python tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=bridge --cov-report=html

# Run specific test file
pytest tests/test_primitives.py -v
```

### Code Style

**Python**:
- Follow PEP 8
- Use Black for formatting: `black bridge/ tests/`
- Use Ruff for linting: `ruff check bridge/ tests/`
- Type hints encouraged but not required

**TypeScript**:
- Follow standard TypeScript conventions
- Use Prettier for formatting
- Run `npm run build` to check for errors

## Project Structure

```
baxter-claw/
├── bridge/              # Python bridge server
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

## Types of Contributions

### Bug Reports

When reporting bugs, please include:
- Baxter-Claw version
- Python version
- Operating system
- Steps to reproduce
- Expected vs actual behavior
- Relevant logs or error messages

### Feature Requests

For feature requests, please describe:
- Use case and motivation
- Proposed solution or API
- Alternative approaches considered
- Potential impact on existing functionality

### Code Contributions

#### Adding New Primitives

1. **Implement in `bridge/primitives.py`**:
```python
def new_primitive(self, arm: str, param1: float) -> Dict:
    """Description of what this primitive does."""
    try:
        # Implementation
        return {"success": True, "message": "..."}
    except Exception as e:
        return {"success": False, "message": f"Failed: {e}"}
```

2. **Add API endpoint in `bridge/server.py`**:
```python
@app.post("/primitives/new_primitive")
async def new_primitive(req: NewPrimitiveRequest) -> PrimitiveResponse:
    result = manager.primitives.new_primitive(req.arm, req.param1)
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['message'])
    return PrimitiveResponse(**result)
```

3. **Add Pydantic model in `bridge/models.py`**:
```python
class NewPrimitiveRequest(BaseModel):
    arm: Literal["left", "right"] = "right"
    param1: float = Field(..., description="Parameter description")
```

4. **Add plugin tool in `plugin/openclaw.plugin.json`**:
```json
{
  "name": "new_primitive",
  "description": "Description for LLM",
  "parameters": {
    "type": "object",
    "properties": {
      "arm": {"type": "string", "enum": ["left", "right"]},
      "param1": {"type": "number"}
    },
    "required": ["param1"]
  }
}
```

5. **Add tool handler in `plugin/index.ts`**:
```typescript
new_primitive: async (params: any) => {
  const { arm = 'right', param1 } = params;
  const result = await bridgeClient.newPrimitive(arm, param1);
  return { success: true, message: result.message };
}
```

6. **Add tests in `tests/test_primitives.py`**:
```python
def test_new_primitive_success(primitives):
    result = primitives.new_primitive('right', 1.0)
    assert result['success'] is True
```

#### Adding New Drivers

To support a different robot:

1. **Implement `ArmDriver` interface in `bridge/drivers/`**:
```python
from .base import ArmDriver

class NewRobotDriver(ArmDriver):
    def connect(self) -> bool:
        # Implementation
        pass
    
    # Implement all abstract methods
```

2. **Update `arm_manager.py` to support new driver**:
```python
def _create_driver(self) -> ArmDriver:
    driver_type = self.config.get('driver', {}).get('type', 'mock')
    
    if driver_type == 'new_robot':
        return NewRobotDriver()
    # ...
```

3. **Add configuration example**

4. **Add tests**

## Testing Guidelines

### Test Coverage

- Aim for >80% code coverage
- All new primitives must have tests
- Test both success and failure cases
- Use mock driver for unit tests

### Test Structure

```python
def test_feature_success(fixture):
    """Test successful operation."""
    result = function_under_test(valid_input)
    assert result['success'] is True
    assert expected_condition

def test_feature_failure(fixture):
    """Test failure handling."""
    result = function_under_test(invalid_input)
    assert result['success'] is False
    assert 'error message' in result['message']
```

### Safety Testing

All motion-related code must include safety tests:
- Workspace boundary violations
- Joint limit violations
- Invalid input handling
- Emergency stop functionality

## Documentation

### Code Documentation

- Use docstrings for all public functions/classes
- Include parameter descriptions and return types
- Provide usage examples for complex functions

```python
def pick(self, arm: str, position: List[float], approach_height: float = 0.1) -> Dict:
    """Pick up an object at the specified position.

    Args:
        arm: 'left' or 'right'
        position: Target position [x, y, z] in meters
        approach_height: Height offset for pre-grasp pose (meters)

    Returns:
        Dict with 'success' (bool) and 'message' (str)

    Example:
        >>> result = primitives.pick('right', [0.6, 0.2, 0.1])
        >>> print(result['message'])
        'Successfully picked object at [0.6, 0.2, 0.1]'
    """
```

### User Documentation

When adding features, update relevant docs:
- `README.md`: High-level overview
- `docs/quickstart.md`: Setup and basic usage
- `docs/architecture.md`: System design
- `docs/api.md`: API reference (if adding endpoints)

## Pull Request Process

1. **Before submitting**:
   - Run all tests: `pytest tests/`
   - Check code style: `black bridge/ tests/` and `ruff check bridge/`
   - Update documentation
   - Add entry to CHANGELOG.md

2. **PR Description**:
   - Clear title describing the change
   - Motivation and context
   - List of changes
   - Testing performed
   - Screenshots/videos if applicable

3. **Review Process**:
   - Maintainers will review within 1 week
   - Address feedback and update PR
   - Once approved, maintainer will merge

## Code Review Checklist

Reviewers will check:
- [ ] Code follows project style
- [ ] Tests pass and coverage is adequate
- [ ] Documentation is updated
- [ ] No breaking changes (or properly documented)
- [ ] Safety considerations addressed
- [ ] Performance impact considered
- [ ] Error handling is robust

## Release Process

Maintainers handle releases:
1. Update version in `pyproject.toml` and `plugin/package.json`
2. Update CHANGELOG.md
3. Create git tag: `git tag v0.2.0`
4. Push tag: `git push origin v0.2.0`
5. Create GitHub release with notes

## Community

- **GitHub Issues**: Bug reports and feature requests
- **Discussions**: Questions and general discussion
- **Pull Requests**: Code contributions

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

## Questions?

If you have questions about contributing, please open a GitHub Discussion or reach out to the maintainers.

Thank you for contributing to Baxter-Claw! 🤖
