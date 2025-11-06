# Claude ACE 🚀

**Agentic Context Engineering for Claude Code**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

[English](README.md) | [中文](README_CN.md)

---

## 🌟 What is Claude ACE?

**Claude ACE** brings self-improving capabilities to [Claude Code](https://claude.ai/code) through **Agentic Context Engineering**. It enables Claude to learn from every interaction, building a personalized knowledge base (playbook) that continuously improves responses over time.

### Key Features

✨ **Automatic Learning** - Extracts insights from conversations without manual intervention
📚 **Smart Playbook** - Builds and maintains a scored knowledge base
🔄 **Self-Improving** - Learns what works and prunes what doesn't
⚡ **One-Click Install** - Deploy to any Claude Code project in seconds
🛠️ **Management Tools** - View, analyze, and manage learned knowledge
🎯 **Atomic Insights** - Focuses on specific, actionable learnings

---

## 🎬 Quick Start

### Method 1: One-Line Installation (Recommended) ⚡

Install directly from GitHub without cloning:

```bash
# Install in current directory
curl -fsSL https://raw.githubusercontent.com/yourusername/claude-ace/main/install.sh | bash

# Or using wget
wget -qO- https://raw.githubusercontent.com/yourusername/claude-ace/main/install.sh | bash

# Install in specific directory
INSTALL_DIR=/path/to/project curl -fsSL https://raw.githubusercontent.com/yourusername/claude-ace/main/install.sh | bash

# Force overwrite existing files
FORCE=true curl -fsSL https://raw.githubusercontent.com/yourusername/claude-ace/main/install.sh | bash
```

### Method 2: Clone and Install

```bash
# Clone the repository
git clone https://github.com/yourusername/claude-ace.git
cd claude-ace

# Install into your project
python install.py --project /path/to/your/claude-project

# Or install in current directory
python install.py
```

### Method 3: Quick Install (Minimal)

Ultra-lightweight version for slow connections:

```bash
curl -fsSL https://raw.githubusercontent.com/yourusername/claude-ace/main/quick-install.sh | bash
```

### That's It!

Claude ACE is now active in your project. It will:
- **Session Start**: Inject learned knowledge into context
- **During Work**: Monitor and learn from interactions
- **Session End**: Extract insights and update playbook

---

## 📖 How It Works

### The Learning Loop

```
┌─────────────────────────────────────────────────────────┐
│  1. Session Start                                       │
│     └─> Inject playbook knowledge into context         │
├─────────────────────────────────────────────────────────┤
│  2. User Interaction                                    │
│     └─> Claude applies learned patterns               │
├─────────────────────────────────────────────────────────┤
│  3. Context Compaction (PreCompact Hook)               │
│     └─> Extract key learnings before compression      │
├─────────────────────────────────────────────────────────┤
│  4. Session End                                         │
│     └─> Comprehensive reflection and playbook update  │
└─────────────────────────────────────────────────────────┘
```

### Scoring System

- ✅ **Helpful (+1)**: Learning was successfully applied
- ⚖️ **Neutral (-1)**: Learning wasn't relevant
- ❌ **Harmful (-3)**: Learning caused issues
- 🗑️ **Auto-Cleanup**: Points below -5 are removed

---

## 🛠️ Management Tools

### View Playbook

```bash
cd your-project
python .claude/scripts/view_playbook.py
```

**Output:**
```
═══════════════════════════════════════════════════════════
📚 CLAUDE ACE PLAYBOOK VIEWER
═══════════════════════════════════════════════════════════
Total Key Points: 12

🌟 kpt_003 (Score: +5)
   Use Glob tool with '**/*.py' pattern for Python file search

✅ kpt_001 (Score: +2)
   Respond in Chinese when user greets with '你好'
...
```

### Cleanup Playbook

```bash
# Dry run (preview changes)
python .claude/scripts/cleanup_playbook.py

# Apply cleanup
python .claude/scripts/cleanup_playbook.py --apply
```

### Analyze Diagnostics

```bash
# Enable diagnostic mode first
touch .claude/diagnostic_mode

# After some sessions, analyze
python .claude/scripts/analyze_diagnostics.py
```

---

## 📊 Example Learnings

Real examples from ACE in action:

```json
{
  "text": "Use 'dotnet build <project>' instead of 'cd && dotnet build' to maintain working directory",
  "atomicity_score": 0.95,
  "score": 3
}

{
  "text": "When user mentions MCP, check for existing .claude/ configuration first",
  "atomicity_score": 0.88,
  "score": 2
}

{
  "text": "Run tests after code changes; user expects proactive testing suggestions",
  "atomicity_score": 0.92,
  "score": 4
}
```

---

## 🏗️ Architecture

### File Structure

```
your-project/
└── .claude/
    ├── hooks/
    │   ├── common.py              # Shared utilities
    │   ├── user_prompt_inject.py  # Session start hook
    │   ├── precompact.py          # Pre-compaction hook
    │   └── session_end.py         # Session end hook
    ├── prompts/
    │   ├── reflection.txt         # Learning extraction prompt
    │   └── playbook.txt           # Knowledge injection template
    ├── scripts/
    │   ├── view_playbook.py       # View knowledge base
    │   ├── cleanup_playbook.py    # Clean up playbook
    │   └── analyze_diagnostics.py # Analyze learning patterns
    ├── settings.json              # Hook configuration
    ├── playbook.json              # Knowledge base
    └── ace_config.json            # ACE settings
```

### Core Components

1. **Hooks System** - Intercepts Claude Code events
2. **Reflection Engine** - Extracts atomic insights using Claude Agent SDK
3. **Playbook Manager** - Maintains scored knowledge base
4. **Management Tools** - Utilities for playbook interaction

---

## ⚙️ Configuration

Edit `.claude/ace_config.json`:

```json
{
  "reflection": {
    "min_atomicity_score": 0.70,
    "max_keypoints_to_inject": 15,
    "auto_cleanup_threshold": -5
  },
  "scoring": {
    "helpful_delta": 1,
    "neutral_delta": -1,
    "harmful_delta": -3
  },
  "hooks": {
    "enable_user_prompt_inject": true,
    "enable_precompact": true,
    "enable_session_end": true,
    "inject_only_positive_scores": true
  }
}
```

---

## 📚 Documentation

- [Installation Guide](docs/INSTALL.md) - Detailed installation instructions
- [Usage Guide](docs/USAGE.md) - How to use and manage ACE
- [Architecture](docs/ARCHITECTURE.md) - Technical deep dive
- [中文文档](docs/README_CN.md) - Complete Chinese documentation

---

## 🤝 Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Development Setup

```bash
git clone https://github.com/yourusername/claude-ace.git
cd claude-ace

# Test installation
python install.py --project ./examples/demo_project
```

---

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- Inspired by the [Agentic Context Engineering paper](https://arxiv.org/abs/2510.04618)
- Built for [Claude Code](https://claude.ai/code) by Anthropic
- Based on insights from the [agentic-context-engine](https://github.com/kayba-ai/agentic-context-engine) project

---

## 📧 Contact & Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/claude-ace/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/claude-ace/discussions)
- **Twitter**: [@yourusername](https://twitter.com/yourusername)

---

## ⭐ Star History

If you find Claude ACE useful, please consider starring the project!

[![Star History Chart](https://api.star-history.com/svg?repos=yourusername/claude-ace&type=Date)](https://star-history.com/#yourusername/claude-ace&Date)

---

**Made with ❤️ for the Claude Code community**
