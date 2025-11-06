# Installation Guide

[English](INSTALL.md) | [中文](INSTALL_CN.md)

## Requirements

- **Python**: 3.8 or higher
- **Claude Code**: Latest version
- **claude-agent-sdk**: Installed automatically with Claude Code

## Installation Methods

### Method 1: Quick Install (Recommended)

```bash
# Clone the repository
git clone https://github.com/yourusername/claude-ace.git
cd claude-ace

# Install to your project
python install.py --project /path/to/your/project
```

### Method 2: Install in Current Directory

```bash
cd your-claude-code-project
python /path/to/claude-ace/install.py
```

### Method 3: Manual Installation

If you prefer manual installation:

1. **Create directory structure**:
   ```bash
   mkdir -p .claude/{hooks,prompts,scripts}
   ```

2. **Copy files**:
   ```bash
   cp claude-ace/ace_core/hooks/* .claude/hooks/
   cp claude-ace/ace_core/prompts/* .claude/prompts/
   cp claude-ace/ace_core/scripts/* .claude/scripts/
   cp claude-ace/ace_core/templates/* .claude/
   ```

3. **Make executable**:
   ```bash
   chmod +x .claude/hooks/*.py
   chmod +x .claude/scripts/*.py
   ```

## Installation Options

### Force Overwrite

Overwrite existing files:
```bash
python install.py --force
```

### Skip Hooks Configuration

Install without modifying `settings.json`:
```bash
python install.py --skip-hooks
```

Then manually merge hooks into your `settings.json`:
```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python .claude/hooks/user_prompt_inject.py",
            "timeout": 10
          }
        ]
      }
    ],
    "SessionEnd": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python .claude/hooks/session_end.py",
            "timeout": 120
          }
        ]
      }
    ],
    "PreCompact": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python .claude/hooks/precompact.py",
            "timeout": 120
          }
        ]
      }
    ]
  }
}
```

## Verify Installation

```bash
# Check directory structure
ls -la .claude/

# Expected output:
# .claude/
# ├── hooks/
# │   ├── common.py
# │   ├── user_prompt_inject.py
# │   ├── precompact.py
# │   └── session_end.py
# ├── prompts/
# │   ├── reflection.txt
# │   └── playbook.txt
# ├── scripts/
# │   ├── view_playbook.py
# │   ├── cleanup_playbook.py
# │   └── analyze_diagnostics.py
# ├── settings.json
# ├── playbook.json
# └── ace_config.json
```

## Post-Installation

### 1. Enable Diagnostic Mode (Optional)

```bash
touch .claude/diagnostic_mode
```

This creates detailed logs in `.claude/diagnostic/` for debugging.

### 2. Configure ACE Settings

Edit `.claude/ace_config.json` to customize:

```json
{
  "reflection": {
    "min_atomicity_score": 0.70,
    "max_keypoints_to_inject": 15,
    "auto_cleanup_threshold": -5
  }
}
```

### 3. Start Using Claude Code

Just start a new Claude Code session! ACE will:
- Activate on first user prompt
- Learn from interactions
- Build playbook automatically

## Troubleshooting

### Issue: Hooks not triggering

**Check settings.json**:
```bash
cat .claude/settings.json
```

Ensure hooks are properly configured.

### Issue: Python not found

**Specify Python path in settings.json**:
```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "/usr/bin/python3 .claude/hooks/user_prompt_inject.py",
            "timeout": 10
          }
        ]
      }
    ]
  }
}
```

### Issue: Permission denied

**Make scripts executable**:
```bash
chmod +x .claude/hooks/*.py
chmod +x .claude/scripts/*.py
```

### Issue: claude-agent-sdk not found

The SDK is included with Claude Code. If you see this error:
1. Verify Claude Code is properly installed
2. Check if running in Claude Code environment
3. Hooks will gracefully skip reflection if SDK unavailable

## Uninstallation

To remove Claude ACE:

```bash
# Backup playbook (optional)
cp .claude/playbook.json playbook.backup.json

# Remove ACE files
rm -rf .claude/hooks
rm -rf .claude/prompts
rm -rf .claude/scripts
rm .claude/playbook.json
rm .claude/ace_config.json

# Or just disable hooks in settings.json
```

## Next Steps

- Read the [Usage Guide](USAGE.md)
- Check the [Architecture](ARCHITECTURE.md)
- View [Examples](../examples/)

---

Need help? [Open an issue](https://github.com/yourusername/claude-ace/issues)
