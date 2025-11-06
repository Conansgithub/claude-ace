# Claude ACE 🚀

**为 Claude Code 提供自主学习能力的代理上下文工程**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

[English](README.md) | [中文](README_CN.md)

---

## 🌟 什么是 Claude ACE？

**Claude ACE** 通过**代理上下文工程（Agentic Context Engineering）**为 [Claude Code](https://claude.ai/code) 带来自我改进能力。它使 Claude 能够从每次交互中学习，构建一个个性化的知识库（playbook），随着时间推移不断改进响应质量。

### 核心特性

✨ **自动学习** - 无需手动干预，从对话中自动提取洞察
📚 **智能知识库** - 构建和维护带评分的知识库
🔄 **自我改进** - 学习有效的方法，淘汰无效的知识
⚡ **一键安装** - 几秒钟内部署到任何 Claude Code 项目
🛠️ **管理工具** - 查看、分析和管理学到的知识
🎯 **原子化洞察** - 专注于具体、可操作的学习点

---

## 🎬 快速开始

### 方法 1: 一键安装（推荐）⚡

无需克隆，直接从 GitHub 安装：

```bash
# 在当前目录安装
curl -fsSL https://raw.githubusercontent.com/yourusername/claude-ace/main/install.sh | bash

# 或使用 wget
wget -qO- https://raw.githubusercontent.com/yourusername/claude-ace/main/install.sh | bash

# 安装到指定目录
INSTALL_DIR=/path/to/project curl -fsSL https://raw.githubusercontent.com/yourusername/claude-ace/main/install.sh | bash

# 强制覆盖已有文件
FORCE=true curl -fsSL https://raw.githubusercontent.com/yourusername/claude-ace/main/install.sh | bash
```

### 方法 2: 克隆后安装

```bash
# 克隆仓库
git clone https://github.com/yourusername/claude-ace.git
cd claude-ace

# 安装到你的项目
python install.py --project /path/to/your/claude-project

# 或在当前目录安装
python install.py
```

### 方法 3: 快速安装（精简版）

适合网络较慢的情况：

```bash
curl -fsSL https://raw.githubusercontent.com/yourusername/claude-ace/main/quick-install.sh | bash
```

### 就这么简单！

Claude ACE 现在已在你的项目中激活。它将：
- **会话开始**：将学到的知识注入上下文
- **工作期间**：监控并从交互中学习
- **会话结束**：提取洞察并更新知识库

---

## 📖 工作原理

### 学习循环

```
┌─────────────────────────────────────────────────────────┐
│  1. 会话开始                                            │
│     └─> 将 playbook 知识注入上下文                     │
├─────────────────────────────────────────────────────────┤
│  2. 用户交互                                            │
│     └─> Claude 应用学到的模式                          │
├─────────────────────────────────────────────────────────┤
│  3. 上下文压缩（PreCompact Hook）                      │
│     └─> 在压缩前提取关键学习点                         │
├─────────────────────────────────────────────────────────┤
│  4. 会话结束                                            │
│     └─> 全面反思并更新 playbook                        │
└─────────────────────────────────────────────────────────┘
```

### 评分系统

- ✅ **有帮助 (+1)**：学习点被成功应用
- ⚖️ **中性 (-1)**：学习点不相关
- ❌ **有害 (-3)**：学习点导致问题
- 🗑️ **自动清理**：得分低于 -5 的会被移除

---

## 🛠️ 管理工具

### 查看 Playbook

```bash
cd your-project
python .claude/scripts/view_playbook.py
```

**输出示例：**
```
═══════════════════════════════════════════════════════════
📚 CLAUDE ACE PLAYBOOK VIEWER
═══════════════════════════════════════════════════════════
总计关键点: 12

🌟 kpt_003 (得分: +5)
   使用 Glob 工具和 '**/*.py' 模式搜索 Python 文件

✅ kpt_001 (得分: +2)
   当用户用'你好'打招呼时，用中文回复
...
```

### 清理 Playbook

```bash
# 预览模式（不实际修改）
python .claude/scripts/cleanup_playbook.py

# 应用清理
python .claude/scripts/cleanup_playbook.py --apply
```

### 分析诊断日志

```bash
# 首先启用诊断模式
touch .claude/diagnostic_mode

# 经过一些会话后，分析
python .claude/scripts/analyze_diagnostics.py
```

---

## 📊 学习示例

ACE 实际运行中的真实案例：

```json
{
  "text": "使用 'dotnet build <项目>' 而不是 'cd && dotnet build' 以保持工作目录",
  "atomicity_score": 0.95,
  "score": 3
}

{
  "text": "当用户提到 MCP 时，首先检查现有的 .claude/ 配置",
  "atomicity_score": 0.88,
  "score": 2
}

{
  "text": "代码更改后运行测试；用户期待主动的测试建议",
  "atomicity_score": 0.92,
  "score": 4
}
```

---

## 🏗️ 架构

### 文件结构

```
your-project/
└── .claude/
    ├── hooks/
    │   ├── common.py              # 共享工具函数
    │   ├── user_prompt_inject.py  # 会话开始钩子
    │   ├── precompact.py          # 压缩前钩子
    │   └── session_end.py         # 会话结束钩子
    ├── prompts/
    │   ├── reflection.txt         # 学习提取提示词
    │   └── playbook.txt           # 知识注入模板
    ├── scripts/
    │   ├── view_playbook.py       # 查看知识库
    │   ├── cleanup_playbook.py    # 清理 playbook
    │   └── analyze_diagnostics.py # 分析学习模式
    ├── settings.json              # 钩子配置
    ├── playbook.json              # 知识库
    └── ace_config.json            # ACE 设置
```

### 核心组件

1. **Hooks 系统** - 拦截 Claude Code 事件
2. **反思引擎** - 使用 Claude Agent SDK 提取原子化洞察
3. **Playbook 管理器** - 维护带评分的知识库
4. **管理工具** - 用于 playbook 交互的实用工具

---

## ⚙️ 配置

编辑 `.claude/ace_config.json`：

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

## 📚 文档

- [安装指南](docs/INSTALL_CN.md) - 详细的安装说明
- [使用指南](docs/USAGE_CN.md) - 如何使用和管理 ACE
- [架构文档](docs/ARCHITECTURE_CN.md) - 技术深入探讨
- [English Docs](docs/README.md) - 完整英文文档

---

## 🤝 贡献

欢迎贡献！请查看 [CONTRIBUTING.md](CONTRIBUTING.md) 了解贡献指南。

### 开发环境设置

```bash
git clone https://github.com/yourusername/claude-ace.git
cd claude-ace

# 测试安装
python install.py --project ./examples/demo_project
```

---

## 📜 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件。

---

## 🙏 致谢

- 灵感来自 [Agentic Context Engineering 论文](https://arxiv.org/abs/2510.04618)
- 为 Anthropic 的 [Claude Code](https://claude.ai/code) 构建
- 基于 [agentic-context-engine](https://github.com/kayba-ai/agentic-context-engine) 项目的洞察

---

## 📧 联系与支持

- **问题反馈**: [GitHub Issues](https://github.com/yourusername/claude-ace/issues)
- **讨论**: [GitHub Discussions](https://github.com/yourusername/claude-ace/discussions)
- **Twitter**: [@yourusername](https://twitter.com/yourusername)

---

## ⭐ Star 历史

如果你觉得 Claude ACE 有用，请考虑给项目加星！

[![Star History Chart](https://api.star-history.com/svg?repos=yourusername/claude-ace&type=Date)](https://star-history.com/#yourusername/claude-ace&Date)

---

**用 ❤️ 为 Claude Code 社区制作**
