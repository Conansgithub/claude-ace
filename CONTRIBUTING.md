# Contributing to Claude ACE

Thank you for considering contributing to Claude ACE! This document provides guidelines for contributing to the project.

## 🤝 How to Contribute

### Reporting Bugs

1. Check if the bug has already been reported in [Issues](https://github.com/yourusername/claude-ace/issues)
2. If not, create a new issue with:
   - Clear title and description
   - Steps to reproduce
   - Expected vs actual behavior
   - System information (OS, Python version, etc.)
   - Relevant logs from `.claude/diagnostic/`

### Suggesting Enhancements

1. Check [Discussions](https://github.com/yourusername/claude-ace/discussions) for similar ideas
2. Create a new discussion or issue with:
   - Clear description of the enhancement
   - Use cases and benefits
   - Possible implementation approach

### Pull Requests

1. **Fork and Clone**
   ```bash
   git clone https://github.com/yourusername/claude-ace.git
   cd claude-ace
   ```

2. **Create a Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **Make Changes**
   - Follow existing code style
   - Add comments for complex logic
   - Update documentation if needed

4. **Test Your Changes**
   ```bash
   # Test installation
   python install.py --project ./test-project

   # Verify hooks work
   cd test-project
   python .claude/scripts/view_playbook.py
   ```

5. **Commit and Push**
   ```bash
   git add .
   git commit -m "feat: add your feature description"
   git push origin feature/your-feature-name
   ```

6. **Create Pull Request**
   - Go to GitHub and create a PR
   - Describe your changes
   - Link related issues

## 📝 Code Style

- **Python**: Follow PEP 8
- **Comments**: Use docstrings for functions
- **Naming**: Descriptive variable and function names
- **Line Length**: Max 100 characters

### Example

```python
def extract_keypoints(messages: List[Dict[str, str]],
                     playbook: Dict[str, Any],
                     diagnostic_name: str = "reflection") -> Dict[str, Any]:
    """
    Extract key points from conversation messages.

    Args:
        messages: List of conversation messages
        playbook: Current playbook dictionary
        diagnostic_name: Name for diagnostic output

    Returns:
        Dictionary with new_key_points and evaluations
    """
    # Implementation here
    pass
```

## 🧪 Testing

Before submitting a PR:

1. Test installation in a clean project
2. Verify all management scripts work
3. Check that hooks trigger correctly
4. Review diagnostic outputs for errors

## 📚 Documentation

When adding features:

- Update README.md if user-facing
- Add docstrings to new functions
- Update relevant docs/ files
- Include examples if applicable

## 🌍 Localization

We support bilingual documentation (English/Chinese):

- Update both README.md and README_CN.md
- Keep translations synchronized
- Maintain consistent formatting

## 💡 Development Tips

### Enable Diagnostic Mode
```bash
touch .claude/diagnostic_mode
```

### View Reflection Outputs
```bash
cat .claude/diagnostic/YYYYMMDD_HHMMSS_*.txt
```

### Test Prompt Changes
Edit `.claude/prompts/reflection.txt` and run a test session

## ❓ Questions?

- Open a [Discussion](https://github.com/yourusername/claude-ace/discussions)
- Join our [Discord](https://discord.gg/your-invite) (if applicable)
- Check [existing issues](https://github.com/yourusername/claude-ace/issues)

## 📜 Code of Conduct

Please be respectful and constructive in all interactions. We are building a welcoming community.

## 🎉 Recognition

Contributors will be:
- Listed in CONTRIBUTORS.md
- Mentioned in release notes
- Appreciated by the community!

---

Thank you for making Claude ACE better! 🚀
