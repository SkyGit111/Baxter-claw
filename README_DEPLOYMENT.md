# Baxter-Claw Deployment Guide

Quick reference for deploying Baxter-Claw to your Baxter robot.

## Pre-Deployment Checklist

- [ ] Baxter robot powered on and connected to network
- [ ] ROS workspace configured (`~/ros_ws/baxter.sh`)
- [ ] Python 3.8+ installed
- [ ] OpenClaw installed
- [ ] Network connectivity verified

## Deployment Steps

### 1. On Baxter Control Host

```bash
# Clone repository
cd ~
git clone https://github.com/yourusername/baxter-claw.git
cd baxter-claw

# Install Python dependencies
pip install -e .

# Configure for real hardware
cp config/baxter.example.yaml config/baxter.yaml
nano config/baxter.yaml
# Set: driver.type = "baxter"
# Adjust safety limits if needed

# Source ROS environment
cd ~/ros_ws
./baxter.sh

# Start bridge server
cd ~/baxter-claw
baxter-claw-bridge --config config/baxter.yaml
```

### 2. Install OpenClaw Plugin

```bash
# Build plugin
cd ~/baxter-claw/plugin
npm install
npm run build

# Install to OpenClaw
mkdir -p ~/.openclaw/plugins
cp -r ~/baxter-claw/plugin ~/.openclaw/plugins/baxter-claw

# Configure OpenClaw
cp ~/baxter-claw/config/openclaw.example.json ~/.openclaw/config.json
nano ~/.openclaw/config.json
# Add your API key
```

### 3. Start OpenClaw

```bash
openclaw
# Should load baxter-claw plugin automatically
```

### 4. Test Connection

```bash
# In another terminal
curl http://localhost:8420/health
# Should return: {"healthy": true, "connected": true}

# Enable robot
curl -X POST http://localhost:8420/enable

# Test status
curl http://localhost:8420/status?arm=right
```

### 5. First Motion Test

Via OpenClaw web UI (http://localhost:18789):

```
You: "Enable the robot"
Assistant: [Calls robot_enable] Robot enabled.

You: "Move to home position"
Assistant: [Calls home] Right arm returned to home.
```

## Production Configuration

### Recommended Safety Limits

```yaml
# config/baxter.yaml
safety:
  workspace:
    x: [0.4, 0.85]  # Conservative forward reach
    y: [-0.6, 0.6]  # Lateral limits
    z: [-0.15, 0.45] # Height limits
  max_speed: 0.3    # 30% max speed for safety
```

### Systemd Service (Optional)

Create `/etc/systemd/system/baxter-claw.service`:

```ini
[Unit]
Description=Baxter-Claw Bridge Server
After=network.target

[Service]
Type=simple
User=baxter
WorkingDirectory=/home/baxter/baxter-claw
Environment="PATH=/home/baxter/ros_ws/devel/bin:/usr/bin"
ExecStartPre=/bin/bash -c 'source /home/baxter/ros_ws/baxter.sh'
ExecStart=/usr/local/bin/baxter-claw-bridge --config /home/baxter/baxter-claw/config/baxter.yaml
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Enable:
```bash
sudo systemctl enable baxter-claw
sudo systemctl start baxter-claw
```

## Monitoring

### Check Bridge Status

```bash
# Health check
curl http://localhost:8420/health

# Robot status
curl http://localhost:8420/status?arm=right

# View logs
journalctl -u baxter-claw -f
```

### Safety Monitoring

- Keep emergency stop accessible
- Monitor bridge server logs for safety warnings
- Check robot status regularly
- Test emergency stop before each session

## Troubleshooting

### Bridge won't start

```bash
# Check ROS connection
rostopic list | grep robot

# Verify Python environment
python3 -c "import baxter_interface; print('OK')"

# Check port availability
lsof -i :8420
```

### Robot won't move

1. Check robot is enabled: `curl http://localhost:8420/status`
2. Verify ROS topics: `rostopic echo /robot/state`
3. Check safety limits in config
4. Review bridge logs for errors

### OpenClaw can't connect

1. Verify bridge is running: `curl http://localhost:8420/health`
2. Check plugin installed: `ls ~/.openclaw/plugins/baxter-claw`
3. Verify OpenClaw config: `cat ~/.openclaw/config.json`

## Backup and Recovery

### Backup Configuration

```bash
# Backup configs
cp config/baxter.yaml config/baxter.yaml.backup
cp ~/.openclaw/config.json ~/.openclaw/config.json.backup
```

### Recovery

```bash
# Restore from backup
cp config/baxter.yaml.backup config/baxter.yaml

# Reset to defaults
cp config/baxter.example.yaml config/baxter.yaml
```

## Updates

```bash
# Update code
cd ~/baxter-claw
git pull

# Reinstall
pip install -e .

# Rebuild plugin
cd plugin
npm install
npm run build

# Restart service
sudo systemctl restart baxter-claw
```

## Security

- Bridge server runs on localhost by default
- Use firewall to restrict access to port 8420
- Keep API keys secure (use environment variables)
- Review SECURITY.md for details

## Support

- Documentation: `docs/`
- Issues: GitHub Issues
- Safety: `docs/safety.md`

---

**Remember**: Safety first! Always test new configurations in mock mode before deploying to real hardware.
