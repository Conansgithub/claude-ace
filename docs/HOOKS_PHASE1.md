# Phase 1 Hooks - Real-time Learning and Safety

## Overview

Phase 1 adds two critical hooks that enable real-time learning from tool execution and prevent dangerous operations:

1. **PostToolUse** - Learn from tool execution results
2. **PreToolUse** - Safety checks before tool execution

These hooks complement the existing lifecycle hooks (UserPromptSubmit, PreCompact, SessionEnd) to provide continuous feedback and protection.

---

## 🔍 PostToolUse Hook

**File**: `.claude/hooks/post_tool_use.py`

**Purpose**: Captures tool execution failures and patterns for continuous learning.

### What It Does

- ✅ Monitors all tool executions (Bash, Edit, Write, etc.)
- ✅ Detects failures and categorizes errors
- ✅ Records error patterns for SessionEnd processing
- ✅ Learns from git, test, build, and docker failures

### Error Categories

| Category | Example | Severity |
|----------|---------|----------|
| `merge_conflict` | Git merge failed | High |
| `push_rejected` | Git push rejected | Medium |
| `test_failure` | Pytest failed | High |
| `build_error` | npm/cargo build failed | High |
| `network_error` | Connection timeout | Medium |
| `permission_error` | Permission denied | High |

### How It Works

1. **Tool executes** → Tool completes (success or failure)
2. **PostToolUse triggers** → Analyzes exit code and stderr
3. **Event recorded** → Saves to `.claude/tool_events/`
4. **SessionEnd processes** → Integrates into playbook learning

### Example Output

```
Recorded tool event: test_failure
```

### Storage

Events are stored in `.claude/tool_events/event_TIMESTAMP.json`:

```json
{
  "timestamp": "2025-11-12T10:30:00",
  "tool_name": "Bash",
  "exit_code": 1,
  "stderr": "FAILED tests/test_api.py::test_auth",
  "error_category": "test_failure",
  "error_severity": "high",
  "recoverable": true,
  "session_id": "abc123"
}
```

---

## 🛡️ PreToolUse Hook

**File**: `.claude/hooks/pre_tool_use.py`

**Purpose**: Prevents dangerous operations before they execute.

### What It Blocks

#### Critical (Always Block)
```bash
rm -rf /          # Delete root
rm -rf ~          # Delete home
rm -rf *          # Delete all files
sudo rm           # Privileged deletion
git push --force main   # Force push to main/master
```

#### High (Block by default)
```bash
git reset --hard HEAD~10   # Hard reset many commits
pip install git+http://    # Non-HTTPS install
eval $USER_INPUT           # Code injection risk
```

#### Medium (Warn but allow)
```bash
chmod 777 file.txt         # World-writable permissions
cat .env                   # Reading credentials
echo $API_KEY              # Echoing secrets
```

### How It Works

1. **Tool requested** → Claude wants to execute command
2. **PreToolUse triggers** → Analyzes command safety
3. **Decision made**:
   - ✅ **Safe**: Allow execution (exit 0)
   - ⚠️ **Warning**: Allow with stderr message (exit 0)
   - 🛑 **Block**: Prevent execution (exit 2)

### Example Block

```
🛑 SAFETY BLOCK: CRITICAL RISK

Attempting to recursively delete root or home directory

Command: rm -rf /var/www/*

This operation was blocked by ACE safety checks to prevent potential damage.

Suggestion:
- Review the command carefully
- Use a safer alternative if available
- Manually confirm this is intentional before retrying
```

### Safety Logs

Blocked commands are logged to `.claude/safety_logs/blocked_YYYYMMDD.jsonl`:

```json
{"timestamp": "2025-11-12T10:45:00", "tool_name": "Bash", "command": "rm -rf /", "reason": "Attempting to delete root", "severity": "critical"}
```

---

## 🔄 Integration with Existing Hooks

### Data Flow

```
┌─────────────────────────────────────────────────────────┐
│                    Claude Code Session                   │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│  UserPromptSubmit: Inject learned strategies            │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│  PreToolUse: Safety check → Block or Allow              │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼ (if allowed)
┌─────────────────────────────────────────────────────────┐
│  Tool Executes (Bash, Edit, Write, etc.)                │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│  PostToolUse: Record result → Save to tool_events/      │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼ (during context compaction)
┌─────────────────────────────────────────────────────────┐
│  PreCompact: Extract learnings + tool feedback          │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼ (at session end)
┌─────────────────────────────────────────────────────────┐
│  SessionEnd: Final reflection + process all tool events │
└─────────────────────────────────────────────────────────┘
```

### SessionEnd Integration

SessionEnd now processes tool events:

```python
# Analyzes error patterns
# - Repeated errors → Important patterns
# - Single errors → One-time failures

# Updates playbook based on:
# - Error frequency
# - Error severity
# - Successful alternatives
```

---

## 📊 Configuration

### Enable/Disable Hooks

In `.claude/settings.json`:

```json
{
  "hooks": {
    "PreToolUse": [/* ... */],      // Safety checks
    "PostToolUse": [/* ... */],     // Error learning
    "UserPromptSubmit": [/* ... */], // Knowledge injection
    "PreCompact": [/* ... */],       // Mid-session learning
    "SessionEnd": [/* ... */]        // Final reflection
  }
}
```

### Adjust Safety Rules

Edit `.claude/hooks/pre_tool_use.py`:

```python
DANGEROUS_PATTERNS = [
    {
        'pattern': r'rm\s+-rf\s+[/~]',
        'reason': 'Attempting to delete root',
        'severity': 'critical',
        'block': True  # Change to False to only warn
    },
    # Add custom rules...
]
```

---

## 🎯 Benefits

### Real-time Learning
- ❌ **Before**: Only learned at SessionEnd (too late)
- ✅ **After**: Learns continuously from every tool execution

### Safety Protection
- ❌ **Before**: Could accidentally run `rm -rf /`
- ✅ **After**: Dangerous commands blocked automatically

### Error Patterns
- ❌ **Before**: Repeated errors not detected
- ✅ **After**: Pattern recognition → Better strategies

---

## 🔍 Debugging

### View Recorded Events

```bash
# List tool events
ls -lh .claude/tool_events/

# View recent event
cat .claude/tool_events/event_20251112_103000_123456.json
```

### View Safety Logs

```bash
# Today's blocked commands
cat .claude/safety_logs/blocked_$(date +%Y%m%d).jsonl
```

### Test Hooks Manually

```bash
# Test PostToolUse
echo '{"toolName":"Bash","exitCode":1,"stderr":"error","session_id":"test"}' | \
  python .claude/hooks/post_tool_use.py

# Test PreToolUse (should block)
echo '{"toolName":"Bash","input":{"command":"rm -rf /"}}' | \
  python .claude/hooks/pre_tool_use.py
```

---

## 🚀 Next Steps

### Phase 2 (Planned)
- **Stop hook**: Decision checkpoints
- **UserPromptSubmit enhancement**: Special commands (`/ace-good`, `/ace-bad`)

### Phase 3 (Future)
- **SessionStart**: Load git status, recent issues
- **Notification**: TTS announcements
- **Collaborative learning**: Team playbooks

---

## 📝 Examples

### Example 1: Learning from Git Push Failure

```bash
# User runs: git push origin feature-branch
# PostToolUse records:
{
  "error_category": "push_rejected",
  "stderr": "! [rejected] feature-branch -> feature-branch (non-fast-forward)"
}

# SessionEnd learns:
"Before pushing, always pull and rebase to avoid rejections"
```

### Example 2: Blocking Dangerous Command

```bash
# Claude tries: rm -rf /var/log/*
# PreToolUse blocks:
🛑 SAFETY BLOCK: CRITICAL RISK
Attempting to delete protected path: /var

# Claude sees the error and suggests safer alternative:
"Use 'rm /var/log/specific.log' to delete only the target file"
```

### Example 3: Test Failure Pattern

```bash
# Session has 3 test failures
# PostToolUse records each:
- test_failure at 10:00
- test_failure at 10:15
- test_failure at 10:30

# SessionEnd detects pattern:
"Test failures repeated 3 times - check test setup and fixtures"
```

---

## 🎓 Best Practices

1. **Review safety logs periodically**
   ```bash
   cat .claude/safety_logs/blocked_*.jsonl | grep critical
   ```

2. **Don't disable safety hooks in production**
   - Keep PreToolUse enabled to prevent accidents

3. **Clean up old events**
   ```bash
   # Auto-cleaned by SessionEnd, but manual cleanup if needed
   find .claude/tool_events -name "event_*.json" -mtime +7 -delete
   ```

4. **Monitor error patterns**
   - Check `.claude/diagnostic/` for repeated errors
   - Update playbook manually if patterns emerge

5. **Customize for your workflow**
   - Add project-specific safety rules
   - Adjust error categorization for your tools

---

## 📚 Related Documentation

- [Main README](../README.md)
- [Usage Guide](./USAGE.md)
- [Phase 3 Improvements](../PHASE3_IMPROVEMENTS.md)
- [Hooks Guide](https://docs.claude.com/en/docs/claude-code/hooks-guide)

---

**Version**: 1.0.0 (Phase 1)
**Last Updated**: 2025-11-12
