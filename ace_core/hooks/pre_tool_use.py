#!/usr/bin/env python3
"""
Claude ACE - Pre Tool Use Hook
Safety checks before tool execution

Prevents:
- Destructive file operations
- Dangerous system commands
- Accidental credential exposure
- Unsafe git operations
"""
import json
import sys
import os
import re
from pathlib import Path
from common import get_ace_dir, load_config


# Dangerous patterns that should be blocked
DANGEROUS_PATTERNS = [
    # Destructive file operations
    {
        'pattern': r'rm\s+-rf\s+[/~]',
        'reason': 'Attempting to recursively delete root or home directory',
        'severity': 'critical',
        'block': True
    },
    {
        'pattern': r'rm\s+-rf\s+\*',
        'reason': 'Attempting to delete all files recursively',
        'severity': 'critical',
        'block': True
    },
    {
        'pattern': r'rm\s+-rf\s+\.(?:\s|$)',
        'reason': 'Attempting to recursively delete current directory',
        'severity': 'critical',
        'block': True
    },
    # System-level operations
    {
        'pattern': r'sudo\s+rm',
        'reason': 'Using sudo with rm command - potential system damage',
        'severity': 'critical',
        'block': True
    },
    {
        'pattern': r'chmod\s+777',
        'reason': 'Setting world-writable permissions - security risk',
        'severity': 'high',
        'block': False  # Warn but allow
    },
    # Git operations
    {
        'pattern': r'git\s+push.*--force.*\s+(main|master)',
        'reason': 'Force pushing to main/master branch - dangerous',
        'severity': 'high',
        'block': True
    },
    {
        'pattern': r'git\s+reset.*--hard.*HEAD~[5-9]|HEAD~[1-9]\d+',
        'reason': 'Hard reset more than 5 commits - potential data loss',
        'severity': 'high',
        'block': False
    },
    # Credential exposure
    {
        'pattern': r'cat\s+.*\.(env|key|pem|crt)',
        'reason': 'Reading sensitive files - potential credential exposure',
        'severity': 'medium',
        'block': False
    },
    {
        'pattern': r'echo\s+.*password|token|key|secret',
        'reason': 'Echoing potential credentials',
        'severity': 'medium',
        'block': False
    },
]

# Critical directories that should not be deleted
PROTECTED_PATHS = [
    '/', '/home', '/usr', '/etc', '/var', '/bin', '/sbin',
    '/lib', '/lib64', '/boot', '/dev', '/proc', '/sys'
]


def check_tool_safety(tool_data: dict) -> dict:
    """
    Check if tool execution is safe.

    Returns:
        Dict with 'safe', 'reason', and 'severity'
    """
    tool_name = tool_data.get('toolName', '')
    command = tool_data.get('input', {}).get('command', '')

    # Special handling for different tools
    if tool_name == 'Bash':
        return check_bash_safety(command)
    elif tool_name == 'Write':
        return check_write_safety(tool_data.get('input', {}))
    elif tool_name == 'Edit':
        return check_edit_safety(tool_data.get('input', {}))

    # Default: allow
    return {'safe': True, 'reason': '', 'severity': 'none'}


def check_bash_safety(command: str) -> dict:
    """
    Check Bash command safety.
    """
    if not command:
        return {'safe': True, 'reason': '', 'severity': 'none'}

    # Check against dangerous patterns
    for pattern_def in DANGEROUS_PATTERNS:
        if re.search(pattern_def['pattern'], command, re.IGNORECASE):
            return {
                'safe': not pattern_def['block'],
                'reason': pattern_def['reason'],
                'severity': pattern_def['severity'],
                'pattern': pattern_def['pattern']
            }

    # Check for deletion of protected paths
    if 'rm' in command:
        for protected in PROTECTED_PATHS:
            if protected in command:
                return {
                    'safe': False,
                    'reason': f'Attempting to delete protected path: {protected}',
                    'severity': 'critical'
                }

    # Check for pip/npm install from untrusted sources
    if re.search(r'pip\s+install.*git\+http://', command):
        return {
            'safe': False,
            'reason': 'Installing from non-HTTPS git URL - security risk',
            'severity': 'high'
        }

    # Check for eval/exec of user input
    if re.search(r'eval\s+\$|exec\s+\$', command):
        return {
            'safe': False,
            'reason': 'Using eval/exec with variables - code injection risk',
            'severity': 'high'
        }

    return {'safe': True, 'reason': '', 'severity': 'none'}


def check_write_safety(write_input: dict) -> dict:
    """
    Check Write tool safety.
    """
    file_path = write_input.get('file_path', '')
    content = write_input.get('content', '')

    # Check for writing to system files
    system_paths = ['/etc/', '/usr/', '/bin/', '/sbin/', '/boot/']
    for sys_path in system_paths:
        if file_path.startswith(sys_path):
            return {
                'safe': False,
                'reason': f'Attempting to write to system directory: {sys_path}',
                'severity': 'critical'
            }

    # Check for potential credential exposure
    if any(pattern in content.lower() for pattern in ['password =', 'api_key =', 'secret =', 'token =']):
        return {
            'safe': True,  # Allow but warn
            'reason': 'File contains potential credentials - ensure this is intentional',
            'severity': 'medium'
        }

    return {'safe': True, 'reason': '', 'severity': 'none'}


def check_edit_safety(edit_input: dict) -> dict:
    """
    Check Edit tool safety.
    """
    file_path = edit_input.get('file_path', '')

    # Check for editing system files
    system_paths = ['/etc/', '/usr/', '/bin/', '/sbin/']
    for sys_path in system_paths:
        if file_path.startswith(sys_path):
            return {
                'safe': False,
                'reason': f'Attempting to edit system file: {file_path}',
                'severity': 'critical'
            }

    return {'safe': True, 'reason': '', 'severity': 'none'}


def log_blocked_command(tool_data: dict, safety_result: dict):
    """
    Log blocked command for analysis and future improvements.
    """
    logs_dir = get_ace_dir() / "safety_logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    from datetime import datetime
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'tool_name': tool_data.get('toolName', 'unknown'),
        'command': tool_data.get('input', {}).get('command', ''),
        'reason': safety_result['reason'],
        'severity': safety_result['severity']
    }

    # Append to daily log file
    log_file = logs_dir / f"blocked_{datetime.now().strftime('%Y%m%d')}.jsonl"
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')


def main():
    """
    PreToolUse hook main entry point.

    Input (stdin): JSON with tool information
    Output (stdout):
        - Empty JSON {} if safe (allow)
        - JSON with error if blocked (exit code 2)
    """
    try:
        # Read input from stdin
        input_json = sys.stdin.read()
        if not input_json.strip():
            print(json.dumps({}), flush=True)
            sys.exit(0)

        tool_data = json.loads(input_json)

        # Check safety
        safety_result = check_tool_safety(tool_data)

        # If safe, allow execution
        if safety_result['safe']:
            # If there's a warning (safe but with reason), log to stderr
            if safety_result['reason']:
                print(f"⚠️  Safety Warning: {safety_result['reason']}", file=sys.stderr)

            print(json.dumps({}), flush=True)
            sys.exit(0)

        # BLOCK: Not safe
        log_blocked_command(tool_data, safety_result)

        # Output error message to stderr (will be shown to Claude)
        error_msg = f"""
🛑 SAFETY BLOCK: {safety_result['severity'].upper()} RISK

{safety_result['reason']}

Command: {tool_data.get('input', {}).get('command', 'N/A')}

This operation was blocked by ACE safety checks to prevent potential damage.

Suggestion:
- Review the command carefully
- Use a safer alternative if available
- Manually confirm this is intentional before retrying
"""
        print(error_msg.strip(), file=sys.stderr)

        # Exit with code 2 to block the tool execution
        sys.exit(2)

    except Exception as e:
        print(f"PreToolUse hook error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        # On error, allow execution (fail open for safety)
        print(json.dumps({}), flush=True)
        sys.exit(0)


if __name__ == "__main__":
    main()
