# Usage Guide

[English](USAGE.md) | [中文](USAGE_CN.md)

## Daily Usage

Once installed, Claude ACE works automatically. No manual intervention needed!

### The Learning Cycle

```
User starts session
    ↓
ACE injects playbook knowledge
    ↓
User interacts with Claude
    ↓
Claude applies learned patterns
    ↓
Context compaction triggered (if needed)
    ↓
ACE extracts learnings
    ↓
Session ends
    ↓
ACE performs final reflection
    ↓
Playbook updated
```

## Management Tools

### 1. View Playbook

**See what Claude has learned:**

```bash
python .claude/scripts/view_playbook.py
```

**Output:**
```
═══════════════════════════════════════════════════════════
📚 CLAUDE ACE PLAYBOOK VIEWER
═══════════════════════════════════════════════════════════
Total Key Points: 8

📊 Statistics:
   🌟 Positive Score: 5
   ⚖️  Neutral Score: 2
   ⚠️  Negative Score: 1

📋 Key Points:

🌟 kpt_005 (Score: +4)
   Use Task tool with subagent_type=Explore for codebase questions
   💎 Atomicity: 92%
   📈 Recent: helpful, helpful, neutral

✅ kpt_002 (Score: +2)
   Respond in Chinese when user greets with '你好'
   💎 Atomicity: 95%
...
```

### 2. Cleanup Playbook

**Remove duplicates and low-scoring entries:**

```bash
# Preview what will be removed (dry run)
python .claude/scripts/cleanup_playbook.py

# Apply cleanup
python .claude/scripts/cleanup_playbook.py --apply

# Custom threshold
python .claude/scripts/cleanup_playbook.py --apply --threshold -3
```

**Output:**
```
═══════════════════════════════════════════════════════════
🧹 CLAUDE ACE PLAYBOOK CLEANUP
═══════════════════════════════════════════════════════════
Original: 15 key points
Score Threshold: -5

📉 Low Score Removal (≤-5):
   ❌ [kpt_012] Score: -6
      This approach caused errors in previous sessions...

🔄 Duplicate Removal (≥85% similar):
   ❌ [kpt_008] Score: +1
      Very similar to existing kpt_003

📊 Summary:
   Original:         15
   Removed (low):    1
   Removed (dup):    1
   Final:            13
   Total Removed:    2
   Reduction:        13.3%

✅ Changes saved!
```

### 3. Analyze Diagnostics

**Understand learning patterns:**

First, enable diagnostic mode:
```bash
touch .claude/diagnostic_mode
```

After some sessions:
```bash
python .claude/scripts/analyze_diagnostics.py
```

**Output:**
```
═══════════════════════════════════════════════════════════
🔍 CLAUDE ACE DIAGNOSTIC ANALYSIS
═══════════════════════════════════════════════════════════
Total Files: 24

📋 By Hook Type:
   session_end_reflection          8 files
   precompact_reflection           12 files
   user_prompt_inject              4 files

📅 By Date:
   2025-01-15    6 files
   2025-01-14    10 files
   2025-01-13    8 files

🧠 Learning Statistics:
   Total New Key Points:    18
   Total Evaluations:       45
   Sessions w/ Learning:    6
   Avg Points per Session:  3.0

📈 Recent Activity (last 5 sessions):
   2025-01-15 14:32:10  session_end_reflection     3456 bytes
   2025-01-15 14:28:45  precompact_reflection      2341 bytes
   ...
```

## Configuration

### ACE Settings

Edit `.claude/ace_config.json`:

```json
{
  "reflection": {
    "min_atomicity_score": 0.70,      // Minimum quality for new points
    "max_keypoints_to_inject": 15,    // Max points injected per session
    "auto_cleanup_threshold": -5      // Auto-remove below this score
  },
  "scoring": {
    "helpful_delta": 1,     // +1 for helpful
    "neutral_delta": -1,    // -1 for neutral
    "harmful_delta": -3     // -3 for harmful
  },
  "hooks": {
    "enable_user_prompt_inject": true,
    "enable_precompact": true,
    "enable_session_end": true,
    "inject_only_positive_scores": true  // Only inject points with score ≥ 0
  }
}
```

### Customizing Prompts

**Reflection Prompt:**
Edit `.claude/prompts/reflection.txt` to customize how learnings are extracted.

**Playbook Injection:**
Edit `.claude/prompts/playbook.txt` to customize how knowledge is presented to Claude.

## Advanced Usage

### Manual Playbook Editing

Edit `.claude/playbook.json` directly:

```json
{
  "version": "1.0",
  "last_updated": "2025-01-15T14:30:00",
  "key_points": [
    {
      "name": "kpt_001",
      "text": "Your custom learning point",
      "score": 0,
      "atomicity_score": 0.95
    }
  ]
}
```

### Exporting Playbook

```bash
# Backup playbook
cp .claude/playbook.json playbook_backup_$(date +%Y%m%d).json

# View as pretty JSON
cat .claude/playbook.json | python -m json.tool
```

### Importing Learnings

```python
import json

# Load existing playbook
with open('.claude/playbook.json') as f:
    playbook = json.load(f)

# Add custom learning
playbook['key_points'].append({
    "name": "kpt_999",
    "text": "Your imported learning",
    "score": 0
})

# Save
with open('.claude/playbook.json', 'w') as f:
    json.dump(playbook, f, indent=2, ensure_ascii=False)
```

### Resetting Playbook

```bash
# Backup first
cp .claude/playbook.json playbook_old.json

# Reset to empty
cat > .claude/playbook.json << 'EOF'
{
  "version": "1.0",
  "last_updated": null,
  "key_points": []
}
EOF
```

## Best Practices

### 1. Review Playbook Regularly

```bash
# Weekly check
python .claude/scripts/view_playbook.py
```

Look for:
- Low-scoring points to investigate
- Outdated learnings that should be removed
- Surprising patterns

### 2. Clean Up Periodically

```bash
# Monthly cleanup
python .claude/scripts/cleanup_playbook.py --apply
```

### 3. Monitor Diagnostics

Keep diagnostic mode enabled during initial learning:
```bash
touch .claude/diagnostic_mode
```

Disable later for performance:
```bash
rm .claude/diagnostic_mode
```

### 4. Customize Thresholds

Adjust based on your workflow:

**Aggressive Learning** (keep more points):
```json
{
  "reflection": {
    "auto_cleanup_threshold": -8
  }
}
```

**Conservative Learning** (keep only best points):
```json
{
  "reflection": {
    "min_atomicity_score": 0.85,
    "auto_cleanup_threshold": -3,
    "inject_only_positive_scores": true
  }
}
```

## Troubleshooting

### Playbook Growing Too Large

```bash
# Aggressive cleanup
python .claude/scripts/cleanup_playbook.py --apply --threshold -2

# Or manually edit playbook.json
```

### Learning Quality Issues

1. Check diagnostic outputs:
   ```bash
   cat .claude/diagnostic/latest_*.txt
   ```

2. Adjust atomicity threshold:
   ```json
   {
     "reflection": {
       "min_atomicity_score": 0.80
     }
   }
   ```

3. Review reflection prompt:
   - Edit `.claude/prompts/reflection.txt`
   - Add more examples
   - Adjust scoring criteria

### Hooks Not Working

1. Check hook configuration:
   ```bash
   cat .claude/settings.json
   ```

2. Test hook manually:
   ```bash
   echo '{"session_id": "test"}' | python .claude/hooks/user_prompt_inject.py
   ```

3. Check stderr logs in Claude Code

## Examples

See [examples/](../examples/) directory for:
- Example projects with ACE installed
- Sample playbooks
- Custom configurations

## Next Steps

- Explore [Architecture](ARCHITECTURE.md)
- Read [Contributing Guide](../CONTRIBUTING.md)
- Join [Discussions](https://github.com/yourusername/claude-ace/discussions)

---

Questions? [Open an issue](https://github.com/yourusername/claude-ace/issues)
