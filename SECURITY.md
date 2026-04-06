# Security Policy

## Reporting Security Vulnerabilities

If you discover a security vulnerability in Baxter-Claw, please report it responsibly:

1. **Do NOT** open a public GitHub issue
2. Email the maintainers directly at: [your-email@example.com]
3. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

We will respond within 48 hours and work with you to address the issue.

## Physical Safety

Baxter-Claw controls physical robots. Security vulnerabilities could lead to:
- Unexpected robot motion
- Damage to equipment
- Injury to people

**Critical Security Concerns**:
- Unauthorized access to bridge server
- Command injection via API
- Bypassing safety validators
- Malicious primitive implementations

## Software Security

### Bridge Server Security

**Authentication**: The bridge server (v0.1.0) does NOT implement authentication. It is designed to run on a trusted local network.

**Recommendations**:
- Run bridge server on localhost only (`host: "127.0.0.1"`)
- Use firewall to restrict access to port 8420
- Do not expose bridge server to public internet
- Consider adding authentication for production deployments

**Input Validation**: All API inputs are validated via Pydantic models and safety validators. However:
- Always review LLM-generated commands before execution
- Monitor bridge server logs for suspicious activity
- Implement rate limiting if needed

### OpenClaw Plugin Security

**API Keys**: OpenClaw configuration may contain API keys for LLM services.

**Best Practices**:
- Store API keys in environment variables, not config files
- Use `.gitignore` to prevent committing secrets
- Rotate API keys regularly
- Use least-privilege API keys when possible

### Configuration Security

**Sensitive Files**:
- `config/baxter.yaml` - May contain network settings
- `config/openclaw.json` - May contain API keys
- `.env` files - Environment variables

**Protection**:
```bash
# Set restrictive permissions
chmod 600 config/baxter.yaml
chmod 600 config/openclaw.json

# Never commit actual config files
# Only commit .example versions
```

## Safety Validator Bypass

The safety validator is a critical security component. Any code that bypasses safety checks is a security vulnerability.

**Prohibited**:
- Directly calling driver methods without safety validation
- Modifying safety limits without review
- Disabling safety checks in production

**If you need to modify safety limits**:
1. Document the reason
2. Test thoroughly in simulation
3. Review with team
4. Update safety documentation

## Dependency Security

**Regular Updates**:
```bash
# Check for vulnerable dependencies
pip list --outdated
npm audit

# Update dependencies
pip install --upgrade -r requirements.txt
npm update
```

**Known Vulnerabilities**:
- Monitor GitHub security advisories
- Subscribe to security mailing lists for dependencies
- Use tools like `safety` (Python) and `npm audit` (Node.js)

## Network Security

**Bridge Server**:
- Default port: 8420
- No encryption by default (HTTP, not HTTPS)
- No authentication

**For Production**:
- Use reverse proxy (nginx) with HTTPS
- Implement authentication (API keys, OAuth)
- Use VPN for remote access
- Firewall rules to restrict access

## ROS Security

Baxter SDK uses ROS, which has its own security considerations:
- ROS master must be on trusted network
- ROS topics are not encrypted
- No authentication by default

**Recommendations**:
- Use ROS on isolated network
- Do not expose ROS master to internet
- Consider ROS 2 for better security features (future work)

## Incident Response

If a security incident occurs:

1. **Immediate**:
   - Stop the bridge server
   - Disable the robot
   - Disconnect from network if needed

2. **Assessment**:
   - Determine scope of incident
   - Check logs for unauthorized access
   - Identify vulnerability

3. **Remediation**:
   - Patch vulnerability
   - Update configurations
   - Rotate credentials if compromised

4. **Reporting**:
   - Notify maintainers
   - Document incident
   - Update security policy if needed

## Security Checklist for Deployment

Before deploying Baxter-Claw:

- [ ] Bridge server runs on trusted network
- [ ] Firewall configured to restrict access
- [ ] API keys stored securely (not in code)
- [ ] Config files have restrictive permissions
- [ ] Dependencies are up to date
- [ ] Safety limits are properly configured
- [ ] Logs are monitored
- [ ] Emergency stop is accessible
- [ ] Team is trained on security procedures

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |
| < 0.1   | :x:                |

## Acknowledgments

We appreciate responsible disclosure of security vulnerabilities. Contributors who report valid security issues will be acknowledged (with permission) in release notes.

## Contact

For security concerns: [your-email@example.com]

For general questions: GitHub Issues

---

**Remember**: Security is everyone's responsibility. If you see something, say something.
