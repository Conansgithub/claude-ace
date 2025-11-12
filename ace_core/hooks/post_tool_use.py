#!/usr/bin/env python3
"""
Claude ACE - Post Tool Use Hook
Learns from tool execution failures and patterns

Captures:
- Failed commands (git, test, build, etc.)
- Error patterns and root causes
- Successful alternatives for future reference
"""
import json
import sys
import os
from pathlib import Path
from datetime import datetime
from common import get_ace_dir, load_config


def should_learn_from_tool(tool_name: str, exit_code: int, stderr: str) -> bool:
    """
    Determine if this tool execution is worth learning from.

    Args:
        tool_name: Name of the tool that was executed
        exit_code: Tool's exit code
        stderr: Standard error output

    Returns:
        True if this execution has learning value
    """
    # Learn from all failures
    if exit_code != 0:
        return True

    # Learn from specific successful tools (for pattern recognition)
    learning_tools = ['git', 'npm', 'pytest', 'cargo', 'make', 'docker']
    if any(tool in tool_name.lower() for tool in learning_tools):
        return True

    return False


def categorize_error(tool_name: str, exit_code: int, stderr: str, stdout: str) -> dict:
    """
    Categorize the error for better learning.

    Returns:
        Dict with error category and details
    """
    error_info = {
        'category': 'unknown',
        'severity': 'medium',
        'recoverable': True,
        'keywords': []
    }

    stderr_lower = stderr.lower()
    stdout_lower = stdout.lower()
    combined = stderr_lower + stdout_lower

    # Git errors
    if 'git' in tool_name.lower():
        if 'merge conflict' in combined or 'conflict' in combined:
            error_info['category'] = 'merge_conflict'
            error_info['severity'] = 'high'
            error_info['keywords'] = ['merge', 'conflict']
        elif 'permission denied' in combined or '403' in combined:
            error_info['category'] = 'permission_error'
            error_info['severity'] = 'high'
            error_info['recoverable'] = False
        elif 'rejected' in combined and 'push' in combined:
            error_info['category'] = 'push_rejected'
            error_info['severity'] = 'medium'
        elif 'fatal' in combined:
            error_info['category'] = 'git_fatal'
            error_info['severity'] = 'high'

    # Test failures
    elif any(test in tool_name.lower() for test in ['pytest', 'jest', 'mocha', 'test']):
        if 'failed' in combined or 'error' in combined:
            error_info['category'] = 'test_failure'
            error_info['severity'] = 'high'
            # Extract test count if possible
            import re
            match = re.search(r'(\d+)\s+failed', combined)
            if match:
                error_info['failed_count'] = int(match.group(1))

    # Build/compile errors
    elif any(build in tool_name.lower() for build in ['npm', 'cargo', 'make', 'gcc', 'javac']):
        if 'error' in combined or exit_code != 0:
            error_info['category'] = 'build_error'
            error_info['severity'] = 'high'
        if 'warning' in combined:
            error_info['category'] = 'build_warning'
            error_info['severity'] = 'low'

    # Docker errors
    elif 'docker' in tool_name.lower():
        if 'not found' in combined:
            error_info['category'] = 'docker_not_found'
            error_info['severity'] = 'high'
        elif 'permission denied' in combined:
            error_info['category'] = 'docker_permission'
            error_info['severity'] = 'high'
            error_info['recoverable'] = False

    # Network errors
    if any(net in combined for net in ['connection refused', 'timeout', 'network', 'unreachable']):
        error_info['category'] = 'network_error'
        error_info['severity'] = 'medium'

    # Permission errors
    if 'permission denied' in combined or 'eacces' in combined:
        error_info['category'] = 'permission_error'
        error_info['severity'] = 'high'
        error_info['recoverable'] = False

    return error_info


def record_tool_event(tool_data: dict, error_info: dict):
    """
    Record tool execution event for later learning.

    Events are stored in .claude/tool_events/ and processed by SessionEnd hook.
    """
    events_dir = get_ace_dir() / "tool_events"
    events_dir.mkdir(parents=True, exist_ok=True)

    # Create event record
    event = {
        'timestamp': datetime.now().isoformat(),
        'tool_name': tool_data.get('toolName', 'unknown'),
        'exit_code': tool_data.get('exitCode', 0),
        'stderr': tool_data.get('stderr', '')[:1000],  # Truncate for storage
        'stdout': tool_data.get('stdout', '')[:500],
        'command': tool_data.get('command', ''),
        'error_category': error_info['category'],
        'error_severity': error_info['severity'],
        'recoverable': error_info['recoverable'],
        'session_id': tool_data.get('session_id', 'unknown')
    }

    # Save event (use timestamp as filename to avoid collisions)
    event_file = events_dir / f"event_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.json"
    with open(event_file, 'w', encoding='utf-8') as f:
        json.dump(event, f, indent=2, ensure_ascii=False)

    print(f"Recorded tool event: {error_info['category']}", file=sys.stderr)


def main():
    """
    PostToolUse hook main entry point.

    Input (stdin): JSON with tool execution details
    Output (stdout): Empty JSON (cannot modify tool result)
    """
    try:
        # Read input from stdin
        input_json = sys.stdin.read()
        if not input_json.strip():
            print(json.dumps({}), flush=True)
            sys.exit(0)

        tool_data = json.loads(input_json)

        # Extract tool information
        tool_name = tool_data.get('toolName', '')
        exit_code = tool_data.get('exitCode', 0)
        stderr = tool_data.get('stderr', '')
        stdout = tool_data.get('stdout', '')

        # Decide if we should learn from this
        if not should_learn_from_tool(tool_name, exit_code, stderr):
            print(json.dumps({}), flush=True)
            sys.exit(0)

        # Categorize the error/event
        error_info = categorize_error(tool_name, exit_code, stderr, stdout)

        # Record for later processing
        record_tool_event(tool_data, error_info)

        # PostToolUse cannot modify results, just output empty JSON
        print(json.dumps({}), flush=True)
        sys.exit(0)

    except Exception as e:
        print(f"PostToolUse hook error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        # Don't fail - just log and continue
        print(json.dumps({}), flush=True)
        sys.exit(0)


if __name__ == "__main__":
    main()
