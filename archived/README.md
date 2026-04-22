# Archived Files

This directory contains historical documents, debug scripts, and test reports that are no longer actively used but kept for reference.

## Directory Structure

```
archived/
├── docs/           # Historical documentation and analysis reports
├── scripts/        # Debug and calibration scripts
└── test_reports/   # Old test reports
```

## Contents

### docs/
Historical documentation including:
- Bug fix reports and analysis
- Architecture improvement proposals
- Calibration and deployment logs
- Vision system analysis
- Project summaries from different stages

These documents provide context about the project's evolution but are superseded by current documentation in the main directory.

### scripts/
Debug and calibration scripts including:
- Manual calibration tools
- Coordinate system verification
- Localization debugging
- Old test scripts

These scripts were used during development and debugging but are no longer needed for normal operation.

### test_reports/
Test reports from specific dates, kept for historical reference.

## Current Documentation

For up-to-date documentation, refer to:
- `README.md` - Main project documentation
- `QUICKSTART.md` - Quick start guide
- `ARCHITECTURE_SWITCH.md` - Architecture switching guide
- `docs/` - Current API and architecture documentation
- `openclaw_plugin/skills.md` - Skills definition

## When to Archive

Files should be archived when:
1. They document bugs that have been fixed
2. They describe temporary workarounds no longer needed
3. They are superseded by newer documentation
4. They are debug scripts no longer used in normal workflow
5. They are test reports from specific debugging sessions

## Restoration

If you need to restore any archived file:
```bash
git mv archived/path/to/file.md ./
```
